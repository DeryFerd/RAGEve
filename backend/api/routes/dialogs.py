from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.dependencies import get_current_user
from backend.api.routes._limiter import limiter
from backend.models_peewee import User
from backend.schemas.dialogs import (
    DialogCreate,
    DialogListResponse,
    DialogResponse,
    DialogUpdate,
)
from backend.services.database import run_db_operation
from backend.services.dialog_store import get_dialog_store
from backend.services.tenant_user_store import get_tenant_user_store

router = APIRouter(prefix="/dialogs", tags=["dialogs"])


async def _ensure_tenant_access(user: User, tenant_id: str) -> None:
    """Allow access for admins, direct owner-style tenant IDs, or explicit membership."""
    if user.is_admin or tenant_id == user.id:
        return

    tenant_store = get_tenant_user_store()
    role = await run_db_operation(
        tenant_store.get_user_role_in_tenant, user.id, tenant_id
    )
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this tenant",
        )


@router.post("/", response_model=DialogResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_dialog(
    request: Request,
    payload: DialogCreate,
    user: User = Depends(get_current_user),
) -> DialogResponse:
    """Create a new dialog (agent)."""
    await _ensure_tenant_access(user, payload.tenant_id)

    store = get_dialog_store()
    dialog = await run_db_operation(
        store.create_dialog,
        tenant_id=payload.tenant_id,
        name=payload.name,
        llm_id=payload.llm_id,
        created_by=user.id,
        description=payload.description,
        language=payload.language,
        llm_setting=payload.llm_setting,
        prompt_type=payload.prompt_type,
        prompt_config=payload.prompt_config,
        meta_data_filter=payload.meta_data_filter,
        similarity_threshold=payload.similarity_threshold,
        vector_similarity_weight=payload.vector_similarity_weight,
        top_n=payload.top_n,
        top_k=payload.top_k,
        do_refer=payload.do_refer,
        rerank_id=payload.rerank_id,
        kb_ids=payload.kb_ids,
        status=payload.status,
    )
    # dialog is a peewee model; convert to dict then to response
    dialog_dict = dialog.to_dict()
    return DialogResponse(**dialog_dict)


@router.get("/", response_model=DialogListResponse)
@limiter.limit("120/minute")
async def list_dialogs(
    request: Request,
    tenant_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
) -> DialogListResponse:
    """List dialogs, optionally filtered by tenant."""
    if tenant_id:
        await _ensure_tenant_access(user, tenant_id)

    store = get_dialog_store()
    dialogs, total = await run_db_operation(
        store.list_dialogs, tenant_id=tenant_id, limit=limit, offset=offset
    )

    if not user.is_admin:
        tenant_store = get_tenant_user_store()
        tenant_objs = await run_db_operation(tenant_store.get_tenants_for_user, user.id)
        allowed_tenants = {user.id, *(t.id for t in tenant_objs)}
        dialogs = [d for d in dialogs if d.get("tenant_id") in allowed_tenants]
        total = len(dialogs)

    return DialogListResponse(
        dialogs=[DialogResponse(**d) for d in dialogs],
        total=total,
    )


@router.get("/{dialog_id}", response_model=DialogResponse)
@limiter.limit("120/minute")
async def get_dialog(
    request: Request,
    dialog_id: str,
    user: User = Depends(get_current_user),
) -> DialogResponse:
    """Get a dialog by ID."""
    store = get_dialog_store()
    dialog = await run_db_operation(store.get_dialog, dialog_id)
    if not dialog:
        raise HTTPException(status_code=404, detail=f"Dialog '{dialog_id}' not found")
    await _ensure_tenant_access(user, dialog.tenant_id)
    dialog_dict = dialog.to_dict()
    return DialogResponse(**dialog_dict)


@router.put("/{dialog_id}", response_model=DialogResponse)
@limiter.limit("60/minute")
async def update_dialog(
    request: Request,
    dialog_id: str,
    payload: DialogUpdate,
    user: User = Depends(get_current_user),
) -> DialogResponse:
    """Update a dialog."""
    store = get_dialog_store()
    existing = await run_db_operation(store.get_dialog, dialog_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Dialog '{dialog_id}' not found")
    await _ensure_tenant_access(user, existing.tenant_id)

    updates = payload.dict(exclude_unset=True)
    dialog = await run_db_operation(store.update_dialog, dialog_id, **updates)
    if not dialog:
        raise HTTPException(status_code=404, detail=f"Dialog '{dialog_id}' not found")
    dialog_dict = dialog.to_dict()
    return DialogResponse(**dialog_dict)


@router.delete("/{dialog_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_dialog(
    request: Request,
    dialog_id: str,
    user: User = Depends(get_current_user),
) -> None:
    """Delete a dialog."""
    store = get_dialog_store()
    existing = await run_db_operation(store.get_dialog, dialog_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Dialog '{dialog_id}' not found")
    await _ensure_tenant_access(user, existing.tenant_id)

    deleted = await run_db_operation(store.delete_dialog, dialog_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Dialog '{dialog_id}' not found")
