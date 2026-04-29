"""
Knowledgebase API routes.

Endpoints for managing knowledgebases, documents, files, and ingestion tasks.
"""

from __future__ import annotations

import logging
import time as _time
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

from backend.api.routes._limiter import limiter
from backend.config import settings
from backend.schemas.knowledgebases import (
    DocumentResponse,
    FileUploadResponse,
    KnowledgebaseCreate,
    KnowledgebaseListResponse,
    KnowledgebaseResponse,
    KnowledgebaseUpdate,
    TaskResponse,
)
from backend.services.database import run_db_operation
from backend.services.ingestion_factory import get_ingestion_service
from backend.services.knowledge_base_store import get_knowledge_base_store
from rag.storage.qdrant_store import QdrantStore

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledgebases", tags=["knowledgebases"])


@router.post(
    "/", response_model=KnowledgebaseResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("60/minute")
async def create_knowledgebase(
    request: Request, payload: KnowledgebaseCreate
) -> KnowledgebaseResponse:
    """Create a new knowledge base."""
    store = get_knowledge_base_store()
    kb = await run_db_operation(
        store.create_knowledgebase,
        tenant_id=payload.tenant_id,
        name=payload.name,
        created_by=payload.created_by,
        description=payload.description,
        avatar=payload.avatar,
        parser_ids=payload.parser_ids,
        language=payload.language,
        pagerank=payload.pagerank,
        pipeline_id=payload.pipeline_id,
    )
    kb_dict = kb.to_dict()
    return KnowledgebaseResponse(**kb_dict)


@router.get("/", response_model=KnowledgebaseListResponse)
@limiter.limit("120/minute")
async def list_knowledgebases(
    request: Request,
    tenant_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> KnowledgebaseListResponse:
    """List knowledge bases, optionally filtered by tenant."""
    store = get_knowledge_base_store()
    kbs, total = await run_db_operation(
        store.list_knowledgebases, tenant_id=tenant_id, limit=limit, offset=offset
    )
    return KnowledgebaseListResponse(
        knowledgebases=[KnowledgebaseResponse(**kb) for kb in kbs],
        total=total,
    )


@router.get("/{kb_id}", response_model=KnowledgebaseResponse)
@limiter.limit("120/minute")
async def get_knowledgebase(request: Request, kb_id: str) -> KnowledgebaseResponse:
    """Get a knowledge base by ID."""
    store = get_knowledge_base_store()
    kb = await run_db_operation(store.get_knowledgebase, kb_id)
    if not kb:
        raise HTTPException(
            status_code=404, detail=f"Knowledge base '{kb_id}' not found"
        )
    kb_dict = kb.to_dict()
    return KnowledgebaseResponse(**kb_dict)


@router.put("/{kb_id}", response_model=KnowledgebaseResponse)
@limiter.limit("60/minute")
async def update_knowledgebase(
    request: Request, kb_id: str, payload: KnowledgebaseUpdate
) -> KnowledgebaseResponse:
    """Update a knowledge base."""
    store = get_knowledge_base_store()
    updates = payload.dict(exclude_unset=True)
    kb = await run_db_operation(store.update_knowledgebase, kb_id, **updates)
    if not kb:
        raise HTTPException(
            status_code=404, detail=f"Knowledge base '{kb_id}' not found"
        )
    kb_dict = kb.to_dict()
    return KnowledgebaseResponse(**kb_dict)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_knowledgebase(request: Request, kb_id: str) -> None:
    """Delete a knowledge base and all its documents, files, and tasks."""
    store = get_knowledge_base_store()
    # First, delete Qdrant collection if it exists
    try:
        qdrant: QdrantStore = get_ingestion_service().qdrant
        await qdrant.delete_collection(kb_id)
    except Exception as e:
        _log.warning("Failed to delete Qdrant collection %s: %s", kb_id, e)

    # Delete knowledgebase and cascade
    deleted = await run_db_operation(store.delete_knowledgebase, kb_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Knowledge base '{kb_id}' not found"
        )


@router.post("/{kb_id}/upload", response_model=FileUploadResponse)
@limiter.limit("60/minute")
async def upload_files(
    request: Request,
    kb_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    parser_id: str = Query(default="pdf", description="Parser to use for these files"),
    chunk_size: int | None = Query(default=None, ge=100, le=10000),
    chunk_overlap: int | None = Query(default=None, ge=0, le=1000),
) -> list[FileUploadResponse]:
    """Upload files to a knowledge base.

    This creates File, Document, and Task records, then kicks off background ingestion.
    Ingestion progress can be tracked via the task_id.
    """
    # Validate knowledgebase exists
    store = get_knowledge_base_store()
    kb = await run_db_operation(store.get_knowledgebase, kb_id)
    if not kb:
        raise HTTPException(
            status_code=404, detail=f"Knowledge base '{kb_id}' not found"
        )

    # Determine created_by - for now use kb.created_by or a placeholder
    created_by = kb.created_by

    upload_root: Path = settings.upload_root / kb_id
    upload_root.mkdir(parents=True, exist_ok=True)

    results: list[FileUploadResponse] = []

    for upload in files:
        # Read file bytes
        file_bytes = await upload.read()
        file_size = len(file_bytes)
        # Validate file size
        if file_size > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{upload.filename}' exceeds maximum size of {settings.max_upload_bytes} bytes",
            )
        file_name = upload.filename or "untitled"
        file_ext = Path(file_name).suffix.lower()
        # Basic type from extension
        file_type = file_ext.lstrip(".") if file_ext else "unknown"

        # Save to disk
        dest_path = upload_root / file_name
        dest_path.write_bytes(file_bytes)

        # Create File record
        file_rec = await run_db_operation(
            store.create_file,
            name=file_name,
            size=file_size,
            file_type=file_type,
            created_by=created_by,
            source_type="upload",
        )

        # Create Document record
        doc_rec = await run_db_operation(
            store.create_document,
            kb_id=kb_id,
            name=file_name,
            parser_id=parser_id,
            created_by=created_by,
            doc_type=file_type,
        )

        # Link file to document
        await run_db_operation(store.link_file_to_document, file_rec.id, doc_rec.id)

        # Create Task for ingestion
        task_rec = await run_db_operation(
            store.create_task,
            doc_id=doc_rec.id,
            task_type="ingestion",
            from_page=0,
            to_page=100000000,
        )

        # Kick off background ingestion
        # We'll run the ingestion in a separate asyncio task, updating Task and Document as we go.
        background_tasks.add_task(
            run_ingestion_background,
            task_id=task_rec.id,
            doc_id=doc_rec.id,
            kb_id=kb_id,
            file_path=dest_path,
            parser_id=parser_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        results.append(
            FileUploadResponse(
                filename=file_name,
                file_id=file_rec.id,
                doc_id=doc_rec.id,
                task_id=task_rec.id,
                size=file_size,
                file_type=file_type,
                status="queued",
            )
        )

    return results


async def run_ingestion_background(
    task_id: str,
    doc_id: str,
    kb_id: str,
    file_path: Path,
    parser_id: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
):
    """Background task to run ingestion and update Task/Document records."""
    store = get_knowledge_base_store()
    ingestion = get_ingestion_service()

    # Mark task as started
    await run_db_operation(store.start_task, task_id)
    t0 = _time.monotonic()

    try:
        # Update document progress: starting
        await run_db_operation(
            store.update_document_progress,
            doc_id,
            progress=5.0,
            progress_msg="Starting ingestion",
        )

        # Run ingestion
        result = await ingestion.ingest_file(
            file_path=file_path,
            dataset_id=kb_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # force_profile could be passed if needed
        )

        elapsed = _time.monotonic() - t0

        # Update document as complete
        await run_db_operation(
            store.complete_document,
            doc_id,
            duration=elapsed,
            doc_metadata={
                "chunks": result.get("chunks", 0),
                "quality_report": result.get("quality_report", {}),
                "extraction": result.get("extraction", {}),
            },
        )

        # Update task to complete
        await run_db_operation(store.complete_task, task_id, duration=elapsed)
        _log.info("Ingestion completed for doc %s (task %s)", doc_id, task_id)

    except Exception as e:
        _log.exception("Ingestion failed for doc %s (task %s)", doc_id, task_id)
        # Update task and document with failure
        await run_db_operation(
            store.update_task_progress,
            task_id,
            progress=-1.0,  # negative indicates error
            msg=f"Error: {str(e)}",
        )
        # Also update document progress
        await run_db_operation(
            store.update_document_progress,
            doc_id,
            progress=-1.0,
            progress_msg=f"Ingestion failed: {str(e)}",
        )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
@limiter.limit("120/minute")
async def get_document(request: Request, doc_id: str) -> DocumentResponse:
    """Get document details by ID."""
    store = get_knowledge_base_store()
    doc = await run_db_operation(store.get_document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    doc_dict = doc.to_dict()
    return DocumentResponse(**doc_dict)


@router.get("/documents", response_model=List[DocumentResponse])
@limiter.limit("120/minute")
async def list_documents(
    request: Request,
    kb_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[DocumentResponse]:
    """List documents, optionally filtered by knowledge base."""
    store = get_knowledge_base_store()
    docs, _ = await run_db_operation(
        store.list_documents, kb_id=kb_id, limit=limit, offset=offset
    )
    return [DocumentResponse(**d) for d in docs]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
@limiter.limit("120/minute")
async def get_task(request: Request, task_id: str) -> TaskResponse:
    """Get task details by ID."""
    store = get_knowledge_base_store()
    task = await run_db_operation(store.get_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    task_dict = task.to_dict()
    return TaskResponse(**task_dict)


@router.get("/documents/{doc_id}/tasks", response_model=List[TaskResponse])
@limiter.limit("120/minute")
async def list_document_tasks(request: Request, doc_id: str) -> list[TaskResponse]:
    """List all tasks for a document."""
    store = get_knowledge_base_store()
    tasks = await run_db_operation(store.get_document_tasks, doc_id)
    return [TaskResponse(**t.to_dict()) for t in tasks]


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def create_document_for_kb(
    request: Request,
    kb_id: str,
    payload: dict,
) -> DocumentResponse:
    """Create a new document within a knowledge base."""
    store = get_knowledge_base_store()
    # Validate KB exists
    kb = await run_db_operation(store.get_knowledgebase, kb_id)
    if not kb:
        raise HTTPException(
            status_code=404, detail=f"Knowledge base '{kb_id}' not found"
        )
    name = payload.get("name")
    parser_id = payload.get("parser_id")
    created_by = payload.get("created_by")
    if not all([name, parser_id, created_by]):
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: name, parser_id, created_by",
        )
    doc = await run_db_operation(
        store.create_document,
        kb_id=kb_id,
        name=name,
        parser_id=parser_id,
        created_by=created_by,
    )
    doc_dict = doc.to_dict()
    return DocumentResponse(**doc_dict)


@router.post("/documents/{doc_id}/upload", response_model=FileUploadResponse)
@limiter.limit("60/minute")
async def upload_file_to_document(
    request: Request,
    doc_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> FileUploadResponse:
    """Upload a file and attach it to an existing document."""
    store = get_knowledge_base_store()
    # Get document
    doc = await run_db_operation(store.get_document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    kb_id = doc.kb_id
    # Read file
    file_bytes = await file.read()
    file_size = len(file_bytes)
    file_name = file.filename or "untitled"
    file_ext = Path(file_name).suffix.lower()
    file_type = file_ext.lstrip(".") if file_ext else "unknown"
    # Save to disk
    upload_root: Path = settings.upload_root / kb_id
    upload_root.mkdir(parents=True, exist_ok=True)
    dest_path = upload_root / file_name
    dest_path.write_bytes(file_bytes)
    # Create File record
    file_rec = await run_db_operation(
        store.create_file,
        name=file_name,
        size=file_size,
        file_type=file_type,
        created_by=doc.created_by,
        source_type="upload",
    )
    # Link file to document
    await run_db_operation(store.link_file_to_document, file_rec.id, doc_id)
    # Create Task for ingestion
    task_rec = await run_db_operation(
        store.create_task,
        doc_id=doc_id,
        task_type="ingestion",
        from_page=0,
        to_page=100000000,
    )
    # Kick off background ingestion
    background_tasks.add_task(
        run_ingestion_background,
        task_id=task_rec.id,
        doc_id=doc_id,
        kb_id=kb_id,
        file_path=dest_path,
        parser_id=doc.parser_id,
        chunk_size=None,
        chunk_overlap=None,
    )
    return FileUploadResponse(
        filename=file_name,
        file_id=file_rec.id,
        doc_id=doc_id,
        task_id=task_rec.id,
        size=file_size,
        file_type=file_type,
        status="queued",
    )


@router.get("/{kb_id}/documents", response_model=list[DocumentResponse])
@limiter.limit("120/minute")
async def list_documents_for_kb(
    request: Request,
    kb_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[DocumentResponse]:
    """List documents for a specific knowledge base."""
    store = get_knowledge_base_store()
    docs, _ = await run_db_operation(
        store.list_documents, kb_id=kb_id, limit=limit, offset=offset
    )
    return [DocumentResponse(**d) for d in docs]
