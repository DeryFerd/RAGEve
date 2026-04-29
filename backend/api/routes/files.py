from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from backend.api.routes._limiter import limiter
from backend.schemas.files import ProcessedFileResponse, UploadSummaryResponse
from backend.services.file_processor import SUPPORTED_EXTENSIONS, FileProcessorService

router = APIRouter(prefix="/files", tags=["files"])
processor = FileProcessorService()


@router.post("/{dataset_id}/upload", response_model=UploadSummaryResponse)
@limiter.limit("60/minute")
async def upload_files_only(
    request: Request, dataset_id: str, files: list[UploadFile] = File(...)
) -> UploadSummaryResponse:
    """
    Upload files WITHOUT embedding — saves to disk and runs deepdoc analysis only.
    Use /datasets/{dataset_id}/upload to upload AND ingest into the vector store.
    """
    results: list[ProcessedFileResponse] = []

    for upload in files:
        if upload.filename is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file missing filename",
            )
        ext = Path(upload.filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported extension '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
            )

        try:
            saved_file = await processor.save_upload(
                dataset_id=dataset_id, upload=upload
            )
            payload = processor.process_file(
                dataset_id=dataset_id, file_path=saved_file
            )
            results.append(ProcessedFileResponse(**payload))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc

    return UploadSummaryResponse(dataset_id=dataset_id, files=results)
