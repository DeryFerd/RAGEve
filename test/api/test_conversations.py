from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.api.base import APITestBase

from backend.services.database import run_db_operation
from backend.services.dialog_store import get_dialog_store


class TestConversationsAPI(APITestBase):
    """Tests for conversation CRUD operations via API."""

    dialog_id: str | None = None
    conversation_id: str | None = None

    @classmethod
    def setup_class(cls):
        super().setup_class()
        # Create a dialog to attach conversations to
        store = get_dialog_store()
        dialog = asyncio.run(
            run_db_operation(
                store.create_dialog,
                tenant_id=cls.test_tenant_id,
                name="Conversation Test Dialog",
                llm_id="llama3.2:latest",
                created_by=cls.test_user_id,
                kb_ids=[],
            )
        )
        cls.dialog_id = dialog.id

    def test_create_conversation(self):
        """Test POST /conversations creates a new conversation."""
        payload = {
            "dialog_id": self.dialog_id,
            "name": "Test Conversation",
            "user_id": self.test_user_id,
            "messages": [],
            "reference": [],
        }
        response = self.client.post("/conversations/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        assert data["id"] is not None
        assert data["dialog_id"] == self.dialog_id
        assert data["name"] == "Test Conversation"
        self.__class__.conversation_id = data["id"]

    def test_list_conversations(self):
        """Test GET /conversations returns list filtered by dialog."""
        response = self.client.get(
            "/conversations/", params={"dialog_id": self.dialog_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert data["total"] >= 1
        found = any(c["id"] == self.conversation_id for c in data["conversations"])
        assert found, "Created conversation not found in list"

    def test_get_conversation(self):
        """Test GET /conversations/{id} returns the conversation."""
        response = self.client.get(f"/conversations/{self.conversation_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.conversation_id
        assert data["dialog_id"] == self.dialog_id

    def test_append_message(self):
        """Test POST /conversations/{id}/messages appends a message."""
        message = {
            "role": "user",
            "content": "Hello, this is a test message.",
        }
        response = self.client.post(
            f"/conversations/{self.conversation_id}/messages", json=message
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello, this is a test message."

        # Verify message appears in conversation
        get_resp = self.client.get(f"/conversations/{self.conversation_id}")
        assert get_resp.status_code == 200
        conv_data = get_resp.json()
        msgs = conv_data["message"]
        assert len(msgs) >= 1
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "Hello, this is a test message."

    def test_update_conversation(self):
        """Test PUT /conversations/{id} updates the conversation."""
        update_data = {
            "name": "Updated Conversation Name",
        }
        response = self.client.put(
            f"/conversations/{self.conversation_id}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Conversation Name"

    def test_delete_conversation(self):
        """Test DELETE /conversations/{id} deletes the conversation."""
        # Create a new conversation to delete
        payload = {
            "dialog_id": self.dialog_id,
            "name": "To Delete",
            "messages": [],
        }
        create_resp = self.client.post("/conversations/", json=payload)
        assert create_resp.status_code == 201
        conv_id = create_resp.json()["id"]

        response = self.client.delete(f"/conversations/{conv_id}")
        assert response.status_code == 204

        get_resp = self.client.get(f"/conversations/{conv_id}")
        assert get_resp.status_code == 404
