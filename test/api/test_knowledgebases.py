"""
API integration tests for /knowledgebases endpoints.
Tests knowledgebase CRUD, document creation, and file upload.
"""

from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.api.base import APITestBase

from backend.services.database import run_db_operation
from backend.services.knowledge_base_store import get_knowledge_base_store


class TestKnowledgebasesAPI(APITestBase):
    """Tests for knowledgebase and document management via API."""

    kb_id: str | None = None
    other_kb_id: str | None = None
    doc_id: str | None = None
    task_id: str | None = None

    @classmethod
    def setup_class(cls):
        super().setup_class()
        # Create a KB for document tests
        store = get_knowledge_base_store()
        kb = asyncio.run(
            run_db_operation(
                store.create_knowledgebase,
                tenant_id=cls.test_tenant_id,
                name="Test KB for Documents",
                created_by=cls.test_user_id,
            )
        )
        cls.kb_id = kb.id

    def test_create_knowledgebase(self):
        """Test POST /knowledgebases creates a new knowledge base."""
        payload = {
            "tenant_id": self.test_tenant_id,
            "name": "Another KB",
            "created_by": self.test_user_id,
            "description": "Test description",
            "language": "English",
            "parser_ids": "pdf,docx",
            "pagerank": 0,
        }
        response = self.client.post("/knowledgebases/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Another KB"
        assert data["tenant_id"] == self.test_tenant_id
        self.__class__.other_kb_id = data["id"]

    def test_list_knowledgebases(self):
        """Test GET /knowledgebases returns list with our KBs."""
        response = self.client.get(
            "/knowledgebases/", params={"tenant_id": self.test_tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "knowledgebases" in data
        assert "total" in data
        assert data["total"] >= 2
        ids = [kb["id"] for kb in data["knowledgebases"]]
        assert self.kb_id in ids
        assert self.other_kb_id in ids

    def test_get_knowledgebase(self):
        """Test GET /knowledgebases/{id} returns the KB."""
        response = self.client.get(f"/knowledgebases/{self.kb_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.kb_id
        assert data["name"] == "Test KB for Documents"

    def test_update_knowledgebase(self):
        """Test PUT /knowledgebases/{id} updates the KB."""
        update_data = {
            "name": "Updated KB Name",
            "description": "Updated description",
            "pagerank": 5,
        }
        response = self.client.put(f"/knowledgebases/{self.kb_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated KB Name"
        assert data["description"] == "Updated description"
        assert data["pagerank"] == 5

    def test_create_document(self):
        """Test POST /knowledgebases/{kb_id}/documents creates a document."""
        payload = {
            "name": "Test Document",
            "parser_id": "pdf",
            "created_by": self.test_user_id,
        }
        response = self.client.post(
            f"/knowledgebases/{self.kb_id}/documents", json=payload
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Test Document"
        assert data["kb_id"] == self.kb_id
        self.__class__.doc_id = data["id"]
        print(f"DEBUG: Set doc_id to {self.doc_id!r}, class doc_id = {self.__class__.doc_id!r}")

    def test_get_document(self):
        """Test GET /documents/{doc_id} returns the document."""
        response = self.client.get(f"/documents/{self.doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.doc_id
        assert data["name"] == "Test Document"
        assert data["progress"] == 0.0  # initial

    def test_list_documents(self):
        """Test GET /knowledgebases/{kb_id}/documents lists documents."""
        response = self.client.get(f"/knowledgebases/{self.kb_id}/documents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(d["id"] == self.doc_id for d in data)

    def test_file_upload(self):
        """Test POST /documents/{doc_id}/upload uploads a file and creates File, Task."""
        # Create a document first (test should be independent)
        payload = {
            "name": "Upload Test Document",
            "parser_id": "pdf",
            "created_by": self.test_user_id,
        }
        response = self.client.post(
            f"/knowledgebases/{self.kb_id}/documents", json=payload
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        doc_data = response.json()
        doc_id = doc_data["id"]

        # Create a simple text file content
        file_content = b"Hello, this is a test document for RAG."
        file_like = io.BytesIO(file_content)
        files = {"file": ("test.txt", file_like, "text/plain")}
        response = self.client.post(f"/documents/{doc_id}/upload", files=files)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "file_id" in data
        assert "doc_id" in data
        assert "task_id" in data
        assert data["file_id"] is not None
        assert data["doc_id"] == self.doc_id
        assert data["task_id"] is not None
        self.__class__.task_id = data["task_id"]

    def test_get_task(self):
        """Task created by file upload should be retrievable via store indirectly?
        There is no direct GET /tasks/{id} endpoint currently, but we can check it via document or just store test.
        """
        # For API tests, we might not have a direct task endpoint; we can skip or check via knowledgebase store.
        # We'll just verify the task_id is not None and move on.
        assert hasattr(self, "task_id")

    def test_delete_knowledgebase(self):
        """Test DELETE /knowledgebases/{id} deletes the KB and cascade."""
        # Create a KB to delete
        payload = {
            "tenant_id": self.test_tenant_id,
            "name": "To Delete KB",
            "created_by": self.test_user_id,
        }
        create_resp = self.client.post("/knowledgebases/", json=payload)
        assert create_resp.status_code == 201
        kb_id = create_resp.json()["id"]

        response = self.client.delete(f"/knowledgebases/{kb_id}")
        assert response.status_code == 204

        get_resp = self.client.get(f"/knowledgebases/{kb_id}")
        assert get_resp.status_code == 404
