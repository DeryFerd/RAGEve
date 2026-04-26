"""
Unit tests for rag.storage.agent_store.AgentStore.

Run: uv run python test/test_agent_store.py
"""

import json
import sys
import tempfile
from pathlib import Path

# Ensure project root is in path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from rag.storage.agent_store import AgentStore, AgentConfig


def test_agent_store():
    # Use a temporary directory for registry
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"
        # Ensure file does not exist; AgentStore will create it
        store = AgentStore(registry_path=registry_path)

        # Create config
        config = AgentConfig(
            system_prompt="You are a helpful assistant.",
            dataset_id="test-collection",
            embedding_model="nomic-embed-text",
            chat_model="llama3.2",
            temperature=0.7,
            top_k=5,
        )

        # Create agents for user1 and user2
        agent1 = store.create(owner_id="user-1", name="Agent 1", description="First agent", config=config)
        agent2 = store.create(owner_id="user-2", name="Agent 2", description="Second agent", config=config)

        # List by owner
        agents_user1 = store.list_by_owner(owner_id="user-1")
        assert len(agents_user1) == 1 and agents_user1[0].agent_id == agent1.agent_id
        agents_user2 = store.list_by_owner(owner_id="user-2")
        assert len(agents_user2) == 1 and agents_user2[0].agent_id == agent2.agent_id

        # List all
        all_agents = store.list()
        assert len(all_agents) == 2

        # Get with ownership
        agent = store.get(agent1.agent_id, user_id="user-1")
        assert agent is not None and agent.agent_id == agent1.agent_id
        # Get with wrong user should return None
        agent = store.get(agent1.agent_id, user_id="user-2")
        assert agent is None
        # Get as admin (is_admin=True) should allow
        agent = store.get(agent1.agent_id, user_id=None, is_admin=True)
        assert agent is not None

        # Update
        updated = store.update(
            agent1.agent_id,
            user_id="user-1",
            is_admin=False,
            updates={"name": "Updated Agent 1", "config": {"temperature": 0.5}}
        )
        assert updated is not None
        assert updated.name == "Updated Agent 1"
        assert updated.config.temperature == 0.5
        # Update by non-owner fails
        bad_update = store.update(
            agent2.agent_id,
            user_id="user-1",
            is_admin=False,
            updates={"name": "Hacked"}
        )
        assert bad_update is None

        # Delete
        deleted = store.delete(agent1.agent_id, user_id="user-1", is_admin=False)
        assert deleted is True
        assert store.get(agent1.agent_id) is None
        # Delete by non-owner fails
        deleted = store.delete(agent2.agent_id, user_id="user-1", is_admin=False)
        assert deleted is False

        # Backward compatibility: agent without owner_id defaults to "system"
        legacy_agent = {
            "agent_id": "legacy-agent",
            "name": "Legacy",
            "description": "Old agent",
            "config": {
                "system_prompt": "test",
                "dataset_id": "test",
                "embedding_model": "test",
                "chat_model": "test",
                "temperature": 0.7,
                "top_k": 5,
                "extra": {},
            },
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            # No owner_id
        }
        # Write directly to registry in correct format (dict keyed by agent_id)
        with open(registry_path, "w") as f:
            json.dump({"legacy-agent": legacy_agent}, f)
        # Reload store
        store2 = AgentStore(registry_path=registry_path)
        legacy = store2.get("legacy-agent")
        assert legacy is not None
        assert legacy.owner_id == "system"

    print("All AgentStore tests passed.")


if __name__ == "__main__":
    test_agent_store()
