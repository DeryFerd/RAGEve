from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from rag.llm.context_builder import build_context


def test_build_context_includes_huggingface_column_metadata():
    chunk = SimpleNamespace(
        chunk_text="Question: What is RAG?\nAnswer: Retrieval augmented generation.",
        metadata={
            "dataset_id": "owner/dataset",
            "split": "train",
            "quality_score": 0.876,
            "profile": "technical",
            "source_file": "train.parquet",
            "text_columns_used": ["question", "answer"],
            "chunk_index": 2,
            "total_chunks_in_row": 4,
        },
    )

    context = build_context([chunk])

    assert "Columns: question, answer" in context
    assert "Chunk: 3/4" in context
