from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from fastapi.testclient import TestClient

from backend.api.dependencies import get_current_user
from backend.main import app
from test.api.base import APITestBase


def _agent(agent_id: str, owner_id: str):
    config = SimpleNamespace(
        system_prompt="You are helpful.",
        dataset_id="dataset",
        embedding_model="nomic-embed-text:latest",
        chat_model="llama3.2:latest",
        temperature=0.7,
        top_k=5,
    )
    return SimpleNamespace(
        agent_id=agent_id,
        owner_id=owner_id,
        name=f"Agent {agent_id}",
        description="",
        config=config,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


class _FakeAgentStore:
    def __init__(self, current_user_id: str):
        self.current_user_id = current_user_id

    def list(self, owner_id: str | None = None):
        agents = [
            _agent("owned-agent", self.current_user_id),
            _agent("other-agent", "other-user"),
        ]
        if owner_id is None:
            return agents
        return [agent for agent in agents if agent.owner_id == owner_id]


class TestAgentAuth(APITestBase):
    """Tests for agent registry authentication and ownership."""

    def test_create_agent_requires_authentication(self):
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides.pop(get_current_user, None)
        try:
            client = TestClient(app)
            response = client.post(
                "/agents/",
                json={
                    "name": "Private Agent",
                    "config": {
                        "dataset_id": "dataset",
                        "embedding_model": "nomic-embed-text:latest",
                        "chat_model": "llama3.2:latest",
                    },
                },
            )
        finally:
            app.dependency_overrides = original_overrides

        assert response.status_code == 401

    def test_list_agents_filters_to_current_user(self, monkeypatch):
        monkeypatch.setattr(
            "backend.api.routes.agents.get_agent_store",
            lambda: _FakeAgentStore(self.test_user_id),
        )

        response = self.client.get("/agents/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["agents"][0]["agent_id"] == "owned-agent"
