"""
HuggingFace ingest routes + background worker.

Routes:
  POST /{dataset_id}/ingest — submit a dataset for ingestion into Qdrant
  GET /ingest/{ingest_id}/status — poll ingest progress
  POST /ingest/{ingest_id}/cancel — cancel an in-progress ingest
"""
from __future__ import annotations

import asyncio
import logging
import time as _time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import settings
from backend.api.routes import hf_status

_log = logging.getLogger("app")

router = APIRouter(tags=["huggingface-ingest"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class HuggingFaceIngestRequest(BaseModel):
    split: str = "train"
    text_columns: list[str] = Field(
        default_factory=list,
        description=(
            "List of column names to combine for semantic embedding. "
            "Columns are formatted as 'Key: Value' lines and concatenated. "
            "Example: ['title', 'content']"
        ),
    )
    metadata_columns: list[str] = Field(default_factory=list)
    row_limit: int | None = Field(default=None, description="Cap rows for testing; leave unset for full ingestion")
    batch_size: int = Field(default=32, ge=1, le=256)
    chunk_overlap: int = Field(default=180, ge=0, le=500)
    max_tokens_per_chunk: int = Field(default=500, ge=50, le=2000)
    force: bool = Field(
        default=False,
        description="Force re-ingestion even if the dataset is already in Qdrant.",
    )


class HuggingFaceIngestResponse(BaseModel):
    ingest_id: str
    dataset_id: str
    collection: str
    rows_processed: int
    chunks_embedded: int
    avg_quality_score: float
    profiles_used: dict[str, int]
    text_columns_used: list[str] = Field(default_factory=list)
    message: str


class HFIngestSubmitResponse(BaseModel):
    ingest_id: str
    dataset_id: str
    message: str


class HFIngestStatusResponse(BaseModel):
    ingest_id: str
    dataset_id: str
    status: str  # queued | running | completed | failed | cancelled
    message: str = ""
    progress: int = Field(default=0, ge=0, le=100)
    error: str | None = None
    result: HuggingFaceIngestResponse | None = None
    completed_at: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Background ingest worker ──────────────────────────────────────────────────


async def _run_hf_background_ingest(
    ingest_id: str,
    dataset_id: str,
    qdrant_safe_id: str,
    started_at: str,
    payload_kwargs: dict[str, Any],
) -> None:
    """Background worker: run HF dataset through quality scoring → chunking → embedding → Qdrant upsert."""
    from rag.ingestion.hf_ingestion import ingest_hf_dataset as _run_hf_ingest
    from backend.services.database import run_db_operation
    from backend.services.ingestion_factory import get_embedder, get_qdrant_store, get_sparse_embedder
    from backend.services.knowledge_base_store import get_knowledge_base_store

    _log.info("HF ingest worker started: ingest_id=%s dataset_id=%s", ingest_id, dataset_id)

    hf_root = settings.data_root / "hf"
    local_path = hf_root / hf_status._normalize_dataset_dirname(dataset_id)

    # Get or create knowledgebase, document, task records
    store = get_knowledge_base_store()
    kb = await run_db_operation(store.get_knowledgebase, qdrant_safe_id)
    if not kb:
        kb = await run_db_operation(
            store.create_knowledgebase,
            tenant_id="system",  # HF datasets are system-wide
            name=dataset_id,
            created_by="system",
            description=f"HuggingFace dataset: {dataset_id}",
            parser_ids="default",
            kb_id=qdrant_safe_id,
        )

    doc = await run_db_operation(store.get_document, qdrant_safe_id)
    if not doc:
        doc = await run_db_operation(
            store.create_document,
            kb_id=kb.id,
            name=dataset_id,
            parser_id="default",
            created_by="system",
            doc_id=qdrant_safe_id,
        )

    task = await run_db_operation(
        store.create_task,
        doc_id=doc.id,
        task_type="hf_ingestion",
        priority=0,
    )

    # Bridge: forward progress from ingest pipeline to Task record and ingest status registry
    async def _bridge(event: dict) -> None:
        st = event.get("stage", "running")
        pct = event.get("progress", 0)
        msg = event.get("message", "")
        # Update ingest status registry for HTTP polling
        await hf_status._set_hf_ingest_status(
            ingest_id,
            progress=min(pct, 99),
            message=f"[{st}] {msg}" if msg else st,
        )
        # Also update Task progress
        await run_db_operation(
            store.update_task_progress,
            task.id,
            progress=pct,
            msg=msg,
        )
        await run_db_operation(
            store.update_document_progress,
            doc.id,
            progress=pct,
            progress_msg=msg,
        )

    await hf_status._set_hf_ingest_status(
        ingest_id,
        status="running",
        message="Loading dataset…",
        progress=2,
        started_at=started_at,
    )

    # Mark task as started
    await run_db_operation(store.start_task, task.id)

    qdrant_store = get_qdrant_store()
    embedder = get_embedder()
    sparse_embedder = get_sparse_embedder()

    try:
        t0_ingest = _time.monotonic()
        result = await _run_hf_ingest(
            local_path=local_path,
            dataset_id=qdrant_safe_id,
            qdrant_store=qdrant_store,
            embedder=embedder,
            split=payload_kwargs.get("split", "train"),
            text_columns=payload_kwargs.get("text_columns"),
            metadata_columns=payload_kwargs.get("metadata_columns"),
            batch_size=payload_kwargs.get("batch_size", 32),
            chunk_overlap=payload_kwargs.get("chunk_overlap", 180),
            max_tokens_per_chunk=payload_kwargs.get("max_tokens_per_chunk", 500),
            row_limit=payload_kwargs.get("row_limit"),
            sparse_embedder=sparse_embedder,
            progress_callback=_bridge,
        )
        elapsed = _time.monotonic() - t0_ingest

        # Mark complete
        await hf_status._set_hf_ingest_status(
            ingest_id,
            status="completed",
            progress=100,
            message="Ingestion complete",
            completed_at=hf_status._utc_now_iso(),
            result={
                "ingest_id": ingest_id,
                "dataset_id": dataset_id,
                "collection": qdrant_safe_id,
                "rows_processed": result.get("rows_processed", 0),
                "chunks_embedded": result.get("chunks_embedded", 0),
                "avg_quality_score": result.get("avg_quality_score", 0.0),
                "profiles_used": result.get("profiles_used", {}),
                "text_columns_used": result.get("text_columns_used", []),
                "message": result.get("message", "Done"),
            },
        )
        # Complete task and document
        duration = elapsed
        await run_db_operation(store.complete_task, task.id, duration)
        await run_db_operation(store.complete_document, doc.id, duration)
        _log.info("HF ingest completed: ingest_id=%s chunks=%d", ingest_id, result.get("chunks_embedded", 0))

    except asyncio.CancelledError:
        await hf_status._set_hf_ingest_status(
            ingest_id,
            status="cancelled",
            progress=0,
            message="Cancelled by user",
            completed_at=hf_status._utc_now_iso(),
        )
        # Also update task/document as failed/cancelled
        await run_db_operation(
            store.update_task_progress,
            task.id,
            progress=-1.0,
            msg="Cancelled by user",
        )
        raise

    except Exception as exc:
        _log.error("HF ingest failed: ingest_id=%s error=%s", ingest_id, exc)
        await hf_status._set_hf_ingest_status(
            ingest_id,
            status="failed",
            progress=0,
            error=str(exc),
            message=f"Failed: {exc}",
            completed_at=hf_status._utc_now_iso(),
        )
        # Update task/document as failed
        await run_db_operation(
            store.update_task_progress,
            task.id,
            progress=-1.0,
            msg=f"Failed: {exc}",
        )
        await run_db_operation(
            store.update_document_progress,
            doc.id,
            progress=-1.0,
            progress_msg=f"Failed: {exc}",
        )


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post(
    "/{dataset_id:path}/ingest",
    response_model=HFIngestSubmitResponse,
    summary="Ingest a registered HuggingFace dataset into Qdrant",
)
async def submit_hf_ingest(
    dataset_id: str,
    payload: HuggingFaceIngestRequest,
    background_tasks: BackgroundTasks,
) -> HFIngestSubmitResponse:
    """
    Submit a HuggingFace dataset for ingestion into Qdrant.

    Runs in the background. Poll GET /datasets/hf/ingest/{ingest_id}/status
    for progress. Use POST /datasets/hf/ingest/{ingest_id}/cancel to abort.
    """
    from backend.services.ingestion_factory import get_qdrant_store

    hf_root = settings.data_root / "hf"
    local_path = hf_root / hf_status._normalize_dataset_dirname(dataset_id)

    if not local_path.exists():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Dataset not found at {local_path}. Download it first using POST /datasets/hf/download.",
        )

    qdrant_safe_id = dataset_id.replace("/", "_")
    qdrant_store = get_qdrant_store()

    if qdrant_store.collection_has_points(qdrant_safe_id) and not payload.force:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Dataset '{dataset_id}' is already ingested. "
            "Set force=True to re-ingest.",
        )

    ingest_id = f"hf-{uuid.uuid4().hex[:12]}"
    started_at = _utc_now_iso()

    await hf_status._set_hf_ingest_status(
        ingest_id,
        status="queued",
        dataset_id=dataset_id,
        message="Ingest queued — waiting for a worker",
        progress=0,
        started_at=started_at,
        result=None,
        completed_at=None,
    )

    # Serialise payload to dict so the daemon thread can reconstruct it
    payload_kwargs = {
        "split": payload.split,
        "text_columns": payload.text_columns,
        "metadata_columns": payload.metadata_columns,
        "batch_size": payload.batch_size,
        "chunk_overlap": payload.chunk_overlap,
        "max_tokens_per_chunk": payload.max_tokens_per_chunk,
        "row_limit": payload.row_limit,
    }

    background_tasks.add_task(
        _run_hf_background_ingest,
        ingest_id,
        dataset_id,
        qdrant_safe_id,
        started_at,
        payload_kwargs,
    )

    _log.info(
        "HF ingest submitted: ingest_id=%s dataset_id=%s qdrant_id=%s",
        ingest_id, dataset_id, qdrant_safe_id,
    )

    return HFIngestSubmitResponse(
        ingest_id=ingest_id,
        dataset_id=dataset_id,
        message=f"Ingest submitted — poll GET /datasets/hf/ingest/{ingest_id}/status for progress.",
    )


@router.get(
    "/ingest/{ingest_id}/status",
    response_model=HFIngestStatusResponse,
    summary="Poll status of a background HF ingest",
)
async def get_hf_ingest_status(ingest_id: str) -> HFIngestStatusResponse:
    """Return current status of a background HF ingest task."""
    entry = hf_status._hf_ingest_registry.get(ingest_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Ingest task not found: '{ingest_id}'")

    result_obj = entry.get("result")
    if result_obj:
        result = HuggingFaceIngestResponse(**result_obj)
    else:
        result = None

    return HFIngestStatusResponse(
        ingest_id=entry.get("ingest_id", ingest_id),
        dataset_id=entry.get("dataset_id", ""),
        status=entry.get("status", "unknown"),
        message=entry.get("message", ""),
        progress=entry.get("progress", 0),
        error=entry.get("error"),
        result=result,
        completed_at=entry.get("completed_at"),
    )


@router.post("/ingest/{ingest_id}/cancel")
async def cancel_hf_ingest(ingest_id: str) -> dict:
    """Cancel a running or queued ingest task."""
    entry = hf_status._hf_ingest_registry.get(ingest_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Ingest task not found: '{ingest_id}'")

    s = entry.get("status", "unknown")
    if s in ("completed", "failed", "cancelled"):
        return {"status": s, "message": f"Already {s}"}

    # await the status write so the 200 response is only sent after persistence completes
    await hf_status._set_hf_ingest_status(
        ingest_id,
        status="cancelled",
        message="Cancellation requested",
        completed_at=_utc_now_iso(),
    )

    return {"status": "cancelled", "message": "Cancellation requested"}
