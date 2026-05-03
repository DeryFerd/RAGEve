from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from fastapi.testclient import TestClient

from backend.api.dependencies import get_current_user
from backend.main import app
from test.api.base import APITestBase


class TestDatasetMutationAuth(APITestBase):
    """Tests for authentication on dataset mutation endpoints."""

    def test_delete_dataset_requires_authentication(self):
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides.pop(get_current_user, None)
        try:
            client = TestClient(app)
            response = client.delete("/datasets/private-dataset")
        finally:
            app.dependency_overrides = original_overrides

        assert response.status_code == 401

    def test_upload_dataset_requires_authentication(self):
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides.pop(get_current_user, None)
        try:
            client = TestClient(app)
            response = client.post(
                "/datasets/private-dataset/upload",
                files={"files": ("sample.txt", b"hello", "text/plain")},
            )
        finally:
            app.dependency_overrides = original_overrides

        assert response.status_code == 401
