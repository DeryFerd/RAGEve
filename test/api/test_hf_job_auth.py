from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from fastapi.testclient import TestClient

from backend.api.dependencies import get_current_user
from backend.main import app
from test.api.base import APITestBase


class TestHuggingFaceJobAuth(APITestBase):
    """Tests for authentication on HuggingFace job mutation endpoints."""

    def test_hf_download_requires_authentication(self):
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides.pop(get_current_user, None)
        try:
            client = TestClient(app)
            response = client.post(
                "/datasets/hf/download",
                json={"dataset_id": "owner/dataset"},
            )
        finally:
            app.dependency_overrides = original_overrides

        assert response.status_code == 401

    def test_hf_ingest_requires_authentication(self):
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides.pop(get_current_user, None)
        try:
            client = TestClient(app)
            response = client.post(
                "/datasets/hf/owner/dataset/ingest",
                json={"split": "train"},
            )
        finally:
            app.dependency_overrides = original_overrides

        assert response.status_code == 401
