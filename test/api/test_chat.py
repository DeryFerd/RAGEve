from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.api.base import APITestBase

from backend.services.database import run_db_operation
from backend.services.dialog_store import get_dialog_store
from backend.services.knowledge_base_store import get_knowledge_base_store


class TestChatAPI(APITestBase):
    """Tests for chat endpoints."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        # Create a knowledgebase (empty) and a dialog pointing to it
        kb_store = get_knowledge_base_store()
        kb = asyncio.run(
            run_db_operation(
                kb_store.create_knowledgebase,
                tenant_id=cls.test_tenant_id,
                name="Chat Test KB",
                created_by=cls.test_user_id,
            )
        )
        cls.kb_id = kb.id

        dialog_store = get_dialog_store()
        dialog = asyncio.run(
            run_db_operation(
                dialog_store.create_dialog,
                tenant_id=cls.test_tenant_id,
                name="Chat Test Dialog",
                llm_id="llama3.2:latest",  # may not matter if no data
                created_by=cls.test_user_id,
                kb_ids=[cls.kb_id],
            )
        )
        cls.dialog_id = dialog.id

    def test_chat_non_streaming(self):
        """Test POST /chat/{dialog_id} returns a ChatResponse."""
        payload = {
            "question": "Hello, this is a test question.",
            "temperature": 0.7,
            "top_k": 5,
            "stream": False,
            "use_reranker": False,
            "use_hybrid": False,
        }
        response = self.client.post(f"/chat/{self.dialog_id}", json=payload)
        # The response should be 200 even if no data in KB, as long as pipeline runs
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        # The answer may be empty or a default message
        # sources should be a list
        assert isinstance(data["sources"], list)

    def test_chat_streaming(self):
        """Test POST /chat/{dialog_id}/stream returns SSE stream."""
        payload = {
            "question": "Test streaming question.",
            "temperature": 0.7,
            "top_k": 5,
            "stream": True,
            "use_reranker": False,
            "use_hybrid": False,
        }
        response = self.client.post(f"/chat/{self.dialog_id}/stream", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        assert "text/event-stream" in response.headers["content-type"]
        # Read a few chunks from the stream
        lines = []
        for line in response.iter_lines():
            lines.append(line)
            if len(lines) >= 5:
                break
        # There should be at least some data lines (starting with "data: ")
        assert any(line.startswith("data:") for line in lines)
