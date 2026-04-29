from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from backend.api.routes._limiter import limiter
from backend.schemas.dialogs import (
    DialogCreate,
    DialogListResponse,
    DialogResponse,
    DialogUpdate,
)
from backend.services.database import run_db_operation
from backend.services.dialog_store import get_dialog_store

router = APIRouter(prefix="/dialogs", tags=["dialogs"])


@router.post("/", response_model=DialogResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_dialog(request: Request, payload: DialogCreate) -> DialogResponse:
    """Create a new dialog (agent)."""
    store = get_dialog_store()
    dialog = await run_db_operation(
        store.create_dialog,
        tenant_id=payload.tenant_id,
        name=payload.name,
        llm_id=payload.llm_id,
        created_by=payload.tenant_id,  # TODO: use authenticated user
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
) -> DialogListResponse:
    """List dialogs, optionally filtered by tenant."""
    store = get_dialog_store()
    dialogs, total = await run_db_operation(
        store.list_dialogs, tenant_id=tenant_id, limit=limit, offset=offset
    )
    return DialogListResponse(
        dialogs=[DialogResponse(**d) for d in dialogs],
        total=total,
    )


@router.get("/{dialog_id}", response_model=DialogResponse)
@limiter.limit("120/minute")
async def get_dialog(request: Request, dialog_id: str) -> DialogResponse:
    """Get a dialog by ID."""
    store = get_dialog_store()
    dialog = await run_db_operation(store.get_dialog, dialog_id)
    if not dialog:
        raise HTTPException(status_code=404, detail=f"Dialog '{dialog_id}' not found")
    dialog_dict = dialog.to_dict()
    return DialogResponse(**dialog_dict)


@router.put("/{dialog_id}", response_model=DialogResponse)
@limiter.limit("60/minute")
async def update_dialog(
    request: Request, dialog_id: str, payload: DialogUpdate
) -> DialogResponse:
    """Update a dialog."""
    store = get_dialog_store()
    updates = payload.dict(exclude_unset=True)
    dialog = await run_db_operation(store.update_dialog, dialog_id, **updates)
    if not dialog:
        raise HTTPException(status_code=404, detail=f"Dialog '{dialog_id}' not found")
    dialog_dict = dialog.to_dict()
    return DialogResponse(**dialog_dict)


@router.delete("/{dialog_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_dialog(request: Request, dialog_id: str) -> None:
    """Delete a dialog."""
    store = get_dialog_store()
    deleted = await run_db_operation(store.delete_dialog, dialog_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Dialog '{dialog_id}' not found")
