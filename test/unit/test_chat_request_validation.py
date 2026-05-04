from __future__ import annotations

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from backend.schemas.chat import ChatRequest


def test_reranker_requires_model_when_enabled():
    with pytest.raises(ValueError, match="reranker_model"):
        ChatRequest(question="What is RAG?", use_reranker=True)


def test_reranker_rejects_unknown_model_when_enabled():
    with pytest.raises(ValueError, match="Unknown reranker_model"):
        ChatRequest(
            question="What is RAG?",
            use_reranker=True,
            reranker_model="not-a-real-reranker",
        )


def test_reranker_accepts_registered_model_when_enabled():
    request = ChatRequest(
        question="What is RAG?",
        use_reranker=True,
        reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
    )

    assert request.reranker_model == "cross-encoder/ms-marco-MiniLM-L-6-v2"
