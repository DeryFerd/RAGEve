"""
RAG evaluation framework models.

Tables:
- EvaluationDataset: Ground truth dataset for evaluation
- EvaluationCase: Individual test case (question + reference answer)
- EvaluationRun: An evaluation execution run
- EvaluationResult: Result for a single test case
"""

from __future__ import annotations

import uuid
from typing import Optional

import peewee

from .base import BaseModel, JSONTextField


class EvaluationDataset(BaseModel):
    """Ground truth dataset for RAG evaluation."""

    id = peewee.CharField(max_length=32, primary_key=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=255, null=False, index=True)
    description = peewee.TextField(null=True)
    kb_ids = JSONTextField(null=False, default=[])
    created_by = peewee.CharField(max_length=32, null=False, index=True)
    status = peewee.IntegerField(null=False, default=1)

    class Meta:
        table_name = "evaluation_datasets"

    @classmethod
    def create_dataset(
        cls,
        tenant_id: str,
        name: str,
        created_by: str,
        description: Optional[str] = None,
        kb_ids: Optional[list[str]] = None,
        status: int = 1,
    ) -> "EvaluationDataset":
        """Create a new evaluation dataset."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            tenant_id=tenant_id,
            name=name,
            description=description,
            kb_ids=kb_ids or [],
            created_by=created_by,
            status=status,
        )


class EvaluationCase(BaseModel):
    """Individual test case within an evaluation dataset."""

    id = peewee.CharField(max_length=32, primary_key=True)
    dataset_id = peewee.CharField(max_length=32, null=False, index=True)
    question = peewee.TextField(null=False)
    reference_answer = peewee.TextField(null=True)
    relevant_doc_ids = JSONTextField(null=True, default=[])
    relevant_chunk_ids = JSONTextField(null=True, default=[])
    metadata = JSONTextField(null=True, default={})

    class Meta:
        table_name = "evaluation_cases"

    @classmethod
    def create_case(
        cls,
        dataset_id: str,
        question: str,
        reference_answer: Optional[str] = None,
        relevant_doc_ids: Optional[list[str]] = None,
        relevant_chunk_ids: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> "EvaluationCase":
        """Create a new evaluation case."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            dataset_id=dataset_id,
            question=question,
            reference_answer=reference_answer,
            relevant_doc_ids=relevant_doc_ids or [],
            relevant_chunk_ids=relevant_chunk_ids or [],
            metadata=metadata or {},
        )


class EvaluationRun(BaseModel):
    """Evaluation execution run."""

    id = peewee.CharField(max_length=32, primary_key=True)
    dataset_id = peewee.CharField(max_length=32, null=False, index=True)
    dialog_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=255, null=False)
    config_snapshot = JSONTextField(null=False)
    metrics_summary = JSONTextField(null=True)
    status = peewee.CharField(max_length=32, null=False, default="PENDING")
    created_by = peewee.CharField(max_length=32, null=False, index=True)
    create_time = peewee.BigIntegerField(null=False, index=True)
    complete_time = peewee.BigIntegerField(null=True)

    class Meta:
        table_name = "evaluation_runs"

    @classmethod
    def create_run(
        cls,
        dataset_id: str,
        dialog_id: str,
        name: str,
        created_by: str,
        config_snapshot: dict,
        status: str = "PENDING",
        create_time: Optional[int] = None,
    ) -> "EvaluationRun":
        """Create a new evaluation run."""
        if create_time is None:
            import time

            create_time = int(time.time())
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            dataset_id=dataset_id,
            dialog_id=dialog_id,
            name=name,
            config_snapshot=config_snapshot,
            metrics_summary={},
            status=status,
            created_by=created_by,
            create_time=create_time,
            complete_time=None,
        )

    def finish(self, metrics_summary: dict, complete_time: Optional[int] = None):
        """Mark evaluation run as completed."""
        self.metrics_summary = metrics_summary
        if complete_time is None:
            import time

            complete_time = int(time.time())
        self.complete_time = complete_time
        self.status = "COMPLETED"
        self.save()


class EvaluationResult(BaseModel):
    """Result for a single test case in an evaluation run."""

    id = peewee.CharField(max_length=32, primary_key=True)
    run_id = peewee.CharField(max_length=32, null=False, index=True)
    case_id = peewee.CharField(max_length=32, null=False, index=True)
    generated_answer = peewee.TextField(null=False)
    retrieved_chunks = JSONTextField(null=False, default=[])
    metrics = JSONTextField(null=False, default={})
    execution_time = peewee.FloatField(null=False)
    token_usage = JSONTextField(null=True)
    create_time = peewee.BigIntegerField(null=False)

    class Meta:
        table_name = "evaluation_results"

    @classmethod
    def create_result(
        cls,
        run_id: str,
        case_id: str,
        generated_answer: str,
        retrieved_chunks: list,
        metrics: dict,
        execution_time: float,
        token_usage: Optional[dict] = None,
        create_time: Optional[int] = None,
    ) -> "EvaluationResult":
        """Create an evaluation result for a test case."""
        if create_time is None:
            import time

            create_time = int(time.time())
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            run_id=run_id,
            case_id=case_id,
            generated_answer=generated_answer,
            retrieved_chunks=retrieved_chunks,
            metrics=metrics,
            execution_time=execution_time,
            token_usage=token_usage,
            create_time=create_time,
        )
