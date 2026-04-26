from __future__ import annotations

import sys
from pathlib import Path
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.api.base import APITestBase


class TestDialogsAPI(APITestBase):
    """Tests for dialog (agent) CRUD operations via API."""

    def test_create_dialog(self):
        """Test POST /dialogs creates a new dialog."""
        payload = {
            "tenant_id": self.test_tenant_id,
            "name": "Test Dialog",
            "description": "A test dialog",
            "llm_id": "llama3.2:latest",
            "llm_setting": {
                "temperature": 0.5,
                "max_tokens": 256,
            },
            "prompt_type": "simple",
            "prompt_config": {
                "system": "You are a helpful assistant.",
                "prologue": "Hello!",
            },
            "kb_ids": [],
            "status": "1",
        }
        response = self.client.post("/dialogs/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Test Dialog"
        assert data["tenant_id"] == self.test_tenant_id
        assert data["llm_id"] == "llama3.2:latest"
        # Store for later tests
        self.dialog_id = data["id"]

    def test_list_dialogs(self):
        """Test GET /dialogs returns list with our dialog."""
        response = self.client.get("/dialogs/", params={"tenant_id": self.test_tenant_id})
        assert response.status_code == 200
        data = response.json()
        assert "dialogs" in data
        assert "total" in data
        assert data["total"] >= 1
        # Find our dialog
        found = any(d["id"] == self.dialog_id for d in data["dialogs"])
        assert found, "Created dialog not found in list"

    def test_get_dialog(self):
        """Test GET /dialogs/{id} returns the dialog."""
        response = self.client.get(f"/dialogs/{self.dialog_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.dialog_id
        assert data["name"] == "Test Dialog"

    def test_update_dialog(self):
        """Test PUT /dialogs/{id} updates the dialog."""
        update_data = {
            "name": "Updated Dialog Name",
            "description": "Updated description",
            "top_k": 2048,
        }
        response = self.client.put(f"/dialogs/{self.dialog_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Dialog Name"
        assert data["description"] == "Updated description"
        assert data["top_k"] == 2048

    def test_delete_dialog(self):
        """Test DELETE /dialogs/{id} deletes the dialog."""
        # Create a new dialog to delete
        payload = {
            "tenant_id": self.test_tenant_id,
            "name": "To Delete",
            "llm_id": "llama3.2:latest",
            "kb_ids": [],
        }
        create_resp = self.client.post("/dialogs/", json=payload)
        assert create_resp.status_code == 201
        dialog_id = create_resp.json()["id"]

        # Delete
        response = self.client.delete(f"/dialogs/{dialog_id}")
        assert response.status_code == 204

        # Verify gone
        get_resp = self.client.get(f"/dialogs/{dialog_id}")
        assert get_resp.status_code == 404
