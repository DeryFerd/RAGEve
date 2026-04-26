"""
RAG evaluation store.

Manages evaluation datasets, test cases, runs, and results.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from backend.models_peewee import (
    EvaluationDataset,
    EvaluationCase,
    EvaluationRun,
    EvaluationResult,
    get_database,
)

_log = logging.getLogger(__name__)


class EvaluationStore:
    """CRUD operations for evaluation framework."""

    # ==================== Evaluation Datasets ====================

    def create_dataset(
        self,
        tenant_id: str,
        name: str,
        created_by: str,
        description: str | None = None,
        kb_ids: list[str] | None = None,
        status: int = 1,
    ) -> EvaluationDataset:
        """Create a new evaluation dataset."""
        with get_database().connection_context():
            ds = EvaluationDataset.create_dataset(
                tenant_id=tenant_id,
                name=name,
                created_by=created_by,
                description=description,
                kb_ids=kb_ids or [],
                status=status,
            )
            _log.info("Created evaluation dataset %s (tenant %s)", ds.id, tenant_id)
            return ds

    def get_dataset(self, dataset_id: str) -> EvaluationDataset | None:
        """Get a dataset by ID."""
        with get_database().connection_context():
            try:
                return EvaluationDataset.get(EvaluationDataset.id == dataset_id)
            except EvaluationDataset.DoesNotExist:
                return None

    def list_datasets(
        self,
        tenant_id: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List evaluation datasets."""
        with get_database().connection_context():
            query = EvaluationDataset.select()
            if tenant_id:
                query = query.where(EvaluationDataset.tenant_id == tenant_id)
            if created_by:
                query = query.where(EvaluationDataset.created_by == created_by)

            total = query.count()
            results = query.order_by(EvaluationDataset.create_time.desc()).limit(limit).offset(offset)
            return [ds.to_dict() for ds in results], total

    # ==================== Evaluation Cases ====================

    def add_case(
        self,
        dataset_id: str,
        question: str,
        reference_answer: str | None = None,
        relevant_doc_ids: list[str] | None = None,
        relevant_chunk_ids: list[str] | None = None,
        metadata: dict | None = None,
    ) -> EvaluationCase:
        """Add a test case to a dataset."""
        with get_database().connection_context():
            case = EvaluationCase.create_case(
                dataset_id=dataset_id,
                question=question,
                reference_answer=reference_answer,
                relevant_doc_ids=relevant_doc_ids,
                relevant_chunk_ids=relevant_chunk_ids,
                metadata=metadata or {},
            )
            _log.debug("Added evaluation case %s to dataset %s", case.id, dataset_id)
            return case

    def get_cases(self, dataset_id: str, limit: int = 1000) -> list[EvaluationCase]:
        """Get all test cases for a dataset."""
        with get_database().connection_context():
            query = (
                EvaluationCase.select()
                .where(EvaluationCase.dataset_id == dataset_id)
                .order_by(EvaluationCase.id)
                .limit(limit)
            )
            return list(query)

    # ==================== Evaluation Runs ====================

    def create_run(
        self,
        dataset_id: str,
        dialog_id: str,
        name: str,
        created_by: str,
        config_snapshot: dict,
        status: str = "PENDING",
    ) -> EvaluationRun:
        """Create a new evaluation run."""
        with get_database().connection_context():
            run = EvaluationRun.create_run(
                dataset_id=dataset_id,
                dialog_id=dialog_id,
                name=name,
                created_by=created_by,
                config_snapshot=config_snapshot,
                status=status,
            )
            _log.info("Created evaluation run %s (dataset %s)", run.id, dataset_id)
            return run

    def get_run(self, run_id: str) -> EvaluationRun | None:
        """Get an evaluation run by ID."""
        with get_database().connection_context():
            try:
                return EvaluationRun.get(EvaluationRun.id == run_id)
            except EvaluationRun.DoesNotExist:
                return None

    def list_runs(
        self,
        dataset_id: str | None = None,
        dialog_id: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List evaluation runs with filters."""
        with get_database().connection_context():
            query = EvaluationRun.select()
            if dataset_id:
                query = query.where(EvaluationRun.dataset_id == dataset_id)
            if dialog_id:
                query = query.where(EvaluationRun.dialog_id == dialog_id)
            if created_by:
                query = query.where(EvaluationRun.created_by == created_by)

            total = query.count()
            results = query.order_by(EvaluationRun.create_time.desc()).limit(limit).offset(offset)
            return [r.to_dict() for r in results], total

    def finish_run(
        self,
        run_id: str,
        metrics_summary: dict,
        complete_time: int | None = None,
    ) -> EvaluationRun | None:
        """Mark an evaluation run as completed."""
        with get_database().connection_context():
            try:
                run = EvaluationRun.get(EvaluationRun.id == run_id)
                run.finish(metrics_summary=metrics_summary, complete_time=complete_time)
                _log.info("Completed evaluation run %s", run_id)
                return run
            except EvaluationRun.DoesNotExist:
                return None

    # ==================== Evaluation Results ====================

    def record_result(
        self,
        run_id: str,
        case_id: str,
        generated_answer: str,
        retrieved_chunks: list,
        metrics: dict,
        execution_time: float,
        token_usage: dict | None = None,
        create_time: int | None = None,
    ) -> EvaluationResult:
        """Record a result for a single test case."""
        with get_database().connection_context():
            result = EvaluationResult.create_result(
                run_id=run_id,
                case_id=case_id,
                generated_answer=generated_answer,
                retrieved_chunks=retrieved_chunks,
                metrics=metrics,
                execution_time=execution_time,
                token_usage=token_usage,
                create_time=create_time,
            )
            return result

    def get_results(
        self,
        run_id: str,
        limit: int = 1000,
    ) -> list[dict]:
        """Get all results for an evaluation run."""
        with get_database().connection_context():
            query = (
                EvaluationResult.select()
                .where(EvaluationResult.run_id == run_id)
                .order_by(EvaluationResult.create_time)
                .limit(limit)
            )
            return [r.to_dict() for r in query]

    def get_result_stats(self, run_id: str) -> dict:
        """Compute aggregate statistics for a run."""
        results = self.get_results(run_id)
        if not results:
            return {}

        # Simple aggregations over metrics
        metric_names = set()
        for r in results:
            metric_names.update(r.get("metrics", {}).keys())

        stats = {}
        for metric in metric_names:
            values = [r["metrics"].get(metric) for r in results if metric in r["metrics"]]
            if values:
                stats[metric] = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                }
        return stats


# Singleton
_evaluation_store: EvaluationStore | None = None


def get_evaluation_store() -> EvaluationStore:
    global _evaluation_store
    if _evaluation_store is None:
        _evaluation_store = EvaluationStore()
    return _evaluation_store
