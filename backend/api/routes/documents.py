"""
Documents API routes (top-level).

Endpoints:
  - GET /documents/{doc_id}       — Get document details
  - POST /documents/{doc_id}/upload — Upload file for a document
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile

from backend.api.dependencies import get_current_user
from backend.api.routes._limiter import limiter
from backend.models_peewee import User
from backend.schemas.knowledgebases import DocumentResponse, FileUploadResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{doc_id}", response_model=DocumentResponse)
@limiter.limit("120/minute")
async def get_document(
    request: Request,
    doc_id: str,
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Backward-compatible alias for secure document lookup."""
    from backend.api.routes.knowledgebases import get_document as get_document_secure

    return await get_document_secure(request=request, doc_id=doc_id, user=user)


@router.post("/{doc_id}/upload", response_model=FileUploadResponse)
@limiter.limit("60/minute")
async def upload_file_to_document(
    request: Request,
    doc_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> FileUploadResponse:
    """Backward-compatible alias for secure upload flow."""
    from backend.api.routes.knowledgebases import (
        upload_file_to_document as upload_file_to_document_secure,
    )

    return await upload_file_to_document_secure(
        request=request,
        doc_id=doc_id,
        background_tasks=background_tasks,
        file=file,
        user=user,
    )
