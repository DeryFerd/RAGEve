"""
API integration tests for ingestion flow (file upload → task completion).
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

import pytest
from test.api.base import APITestBase

from backend.services.database import run_db_operation
from backend.services.knowledge_base_store import get_knowledge_base_store

# Skip integration tests by default; set RUN_INTEGRATION_TESTS=1 to enable
RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS") == "1"


@pytest.mark.skipif(
    not RUN_INTEGRATION_TESTS,
    reason="Integration test requires Qdrant and Ollama with models (set RUN_INTEGRATION_TESTS=1 to run)",
)
class TestIngestionAPI(APITestBase):
    """Tests for file ingestion pipeline via API."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        # Create a knowledgebase
        store = get_knowledge_base_store()
        kb = asyncio.run(
            run_db_operation(
                store.create_knowledgebase,
                tenant_id=cls.test_tenant_id,
                name="Ingestion Test KB",
                created_by=cls.test_user_id,
            )
        )
        cls.kb_id = kb.id
        # Create a document to attach the file to
        doc = asyncio.run(
            run_db_operation(
                store.create_document,
                kb_id=cls.kb_id,
                name="test_document.txt",
                parser_id="txt",
                created_by=cls.test_user_id,
            )
        )
        cls.doc_id = doc.id

    def test_file_upload_triggers_ingestion(self):
        """Test uploading a file creates a File record and a Task, and ingestion completes."""
        file_content = b"This is a test document for RAG ingestion pipeline."
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        response = self.client.post(f"/documents/{self.doc_id}/upload", files=files)
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert "file_id" in data
        assert "doc_id" in data
        assert "task_id" in data
        task_id = data["task_id"]
        self.task_id = task_id

        # Poll the task status until complete (wait up to 120 seconds)
        store = get_knowledge_base_store()
        timeout = 120
        start = time.time()
        completed = False
        while time.time() - start < timeout:
            task = asyncio.run(run_db_operation(store.get_task, task_id))
            if task:
                if task.progress >= 100.0:
                    completed = True
                    break
                elif task.progress < 0:
                    assert False, f"Ingestion task failed: {task.progress_msg}"
            time.sleep(2)
        assert completed, "Ingestion task did not complete within timeout"

        # Verify document progress is 100%
        doc = asyncio.run(run_db_operation(store.get_document, self.doc_id))
        assert doc.progress == 100.0
