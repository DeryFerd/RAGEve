"""
Full end-to-end integration test for RAG workflow.

Tests: create KB → upload file → wait for ingestion → create dialog → chat query.
Requires Qdrant and Ollama services running.
"""

from __future__ import annotations

import asyncio
import io
import sys
import time
from pathlib import Path
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.api.base import APITestBase
from backend.services.knowledge_base_store import get_knowledge_base_store
from backend.services.dialog_store import get_dialog_store
from backend.services.database import run_db_operation


class TestRAGIntegration(APITestBase):
    """End-to-end RAG integration tests."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        # Use real model names that exist in the local Ollama instance
        cls.embed_model = "nomic-embed-text:latest"
        cls.chat_model = "llama3.2:latest"

        # Update the test tenant to use the correct embedding model
        from backend.models_peewee import Tenant
        Tenant.update(embd_id=cls.embed_model).where(Tenant.id == cls.test_tenant_id).execute()

        # Create a knowledgebase for integration tests
        kb = cls.create_knowledgebase(cls, name="Integration KB")
        cls.kb_id = kb.id

        # Create a dialog that uses the correct chat model and points to the KB
        dialog_store = get_dialog_store()
        dialog = asyncio.run(run_db_operation(
            dialog_store.create_dialog,
            tenant_id=cls.test_tenant_id,
            name="Integration Dialog",
            llm_id=cls.chat_model,
            created_by=cls.test_user_id,
            kb_ids=[cls.kb_id],
            top_k=5,
        ))
        cls.dialog_id = dialog.id

    def test_upload_ingest_chat_flow(self):
        """Test complete flow: upload file → ingest → chat query."""
        # Step 1: Create document and upload file
        store = get_knowledge_base_store()
        doc = asyncio.run(run_db_operation(
            store.create_document,
            kb_id=self.kb_id,
            name="integration_test.txt",
            parser_id="txt",
            created_by=self.test_user_id,
        ))
        doc_id = doc.id

        file_content = b"The Bazzi RAG platform is a local-first system for retrieval-augmented generation. It uses Ollama for embeddings and chat, and Qdrant for vector storage."
        files = {"file": ("integration_test.txt", io.BytesIO(file_content), "text/plain")}
        upload_resp = self.client.post(f"/documents/{doc_id}/upload", files=files)
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        task_id = upload_resp.json()["task_id"]

        # Step 2: Wait for ingestion to complete
        timeout = 180
        start = time.time()
        completed = False
        while time.time() - start < timeout:
            task = asyncio.run(run_db_operation(store.get_task, task_id))
            if task:
                if task.progress >= 100.0:
                    completed = True
                    break
                elif task.progress < 0:
                    assert False, f"Ingestion failed: {task.progress_msg}"
            time.sleep(3)
        assert completed, "Ingestion timed out"

        # Verify document marked complete
        doc = asyncio.run(run_db_operation(store.get_document, doc_id))
        assert doc.progress == 100.0

        # Step 3: Send chat query
        payload = {
            "question": "What is the Bazzi RAG platform?",
            "temperature": 0.7,
            "top_k": 5,
            "stream": False,
            "use_hybrid": False,
        }
        chat_resp = self.client.post(f"/chat/{self.dialog_id}", json=payload)
        assert chat_resp.status_code == 200, f"Chat failed: {chat_resp.text}"
        data = chat_resp.json()
        assert "answer" in data
        assert "sources" in data
        answer = data["answer"].lower()
        # The answer should mention key phrases from the uploaded content
        assert "bazzi" in answer or "local" in answer or "rag" in answer or "ollama" in answer
        # Sources should include the uploaded file
        sources = data["sources"]
        assert any("integration_test.txt" in s.get("source", "") for s in sources), "Uploaded file not found in sources"

    def test_streaming_chat(self):
        """Test streaming chat returns SSE events."""
        payload = {
            "question": "Tell me about the platform.",
            "stream": True,
        }
        resp = self.client.post(f"/chat/{self.dialog_id}/stream", json=payload)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        # Collect a few lines
        lines = []
        for line in resp.iter_lines():
            lines.append(line)
            if len(lines) >= 5:
                break
        # At least one data line should be present
        assert any(line.startswith(b"data:") for line in lines), "No SSE data received"
