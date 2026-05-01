"""
Documents API routes (top-level).

Endpoints:
  - GET /documents/{doc_id}       — Get document details
  - POST /documents/{doc_id}/upload — Upload file for a document
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Request,
    UploadFile,
)

from backend.api.routes._limiter import limiter
from backend.config_loader import settings
from backend.schemas.knowledgebases import DocumentResponse, FileUploadResponse
from backend.services.database import run_db_operation
from backend.services.knowledge_base_store import get_knowledge_base_store

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{doc_id}", response_model=DocumentResponse)
@limiter.limit("120/minute")
async def get_document(request: Request, doc_id: str) -> DocumentResponse:
    """Get document details by ID."""
    store = get_knowledge_base_store()
    doc = await run_db_operation(store.get_document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    doc_dict = doc.to_dict()
    return DocumentResponse(**doc_dict)


@router.post("/{doc_id}/upload", response_model=FileUploadResponse)
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
    # Note: we need to import run_ingestion_background from knowledgebases, but to avoid circular import,
    # we can define the same background function here or import from a shared module.
    # For simplicity, we'll directly call get_ingestion_service().ingest, but that might be heavy.
    # However, the original knowledgebases module defines run_ingestion_background.
    # We'll import it from there to reuse.
    try:
        from backend.api.routes.knowledgebases import run_ingestion_background

        background_tasks.add_task(
            run_ingestion_background,
            task_id=task_rec.id,
            doc_id=doc_id,
            kb_id=kb_id,
            minio_key=None,  # File already on disk, no MinIO download needed
            parser_id=doc.parser_id,
            chunk_size=None,
            chunk_overlap=None,
            temp_file_path=str(dest_path),  # Pass the file path on disk
        )
    except ImportError:
        # Fallback: do not run ingestion in background; just return queued status.
        pass

    return FileUploadResponse(
        filename=file_name,
        file_id=file_rec.id,
        doc_id=doc_id,
        task_id=task_rec.id,
        size=file_size,
        file_type=file_type,
        status="queued",
    )
