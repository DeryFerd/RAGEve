"""
Base class for API integration tests.

Sets up a test SQLite database, creates test fixtures (tenant, user),
overrides auth dependency, and provides a TestClient.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

import asyncio
import os
import uuid

import peewee
from fastapi.testclient import TestClient
from playhouse.shortcuts import model_to_dict

import backend.models_peewee as mp
from backend.api.dependencies import get_current_user
from backend.main import app
from backend.models_peewee import (
    LLM,
    MCP,
    API4Conversation,
    APIToken,
    CanvasTemplate,
    Connector,
    Connector2Kb,
    Conversation,
    Dialog,
    Document,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
    File,
    File2Document,
    Knowledgebase,
    LLMFactories,
    PipelineOperationLog,
    Search,
    SyncLogs,
    SystemSettings,
    Task,
    Tenant,
    TenantLLM,
    User,
    UserCanvas,
    UserTenant,
)
from backend.services.auth import hash_password
from backend.services.conversation_store import get_conversation_store
from backend.services.database import run_db_operation
from backend.services.dialog_store import get_dialog_store
from backend.services.knowledge_base_store import get_knowledge_base_store
from backend.services.tenant_user_store import get_tenant_user_store

# Test database file
_test_db_path = "./test_api.db"
_test_db: peewee.SqliteDatabase = None


def setup_test_db():
    """Initialize the test database and bind all models."""
    global _test_db
    _test_db = peewee.SqliteDatabase(_test_db_path)

    models = [
        User,
        Tenant,
        UserTenant,
        Knowledgebase,
        Document,
        File,
        File2Document,
        Task,
        Dialog,
        Conversation,
        LLMFactories,
        LLM,
        TenantLLM,
        Connector,
        Connector2Kb,
        SyncLogs,
        UserCanvas,
        CanvasTemplate,
        EvaluationDataset,
        EvaluationCase,
        EvaluationRun,
        EvaluationResult,
        SystemSettings,
        APIToken,
        API4Conversation,
        MCP,
        Search,
        PipelineOperationLog,
    ]

    for model in models:
        model._meta.database = _test_db

    _test_db.create_tables(models, safe=True)

    # Override global database singleton
    mp._database = _test_db

    # Reset store singletons so they pick up the new database
    import backend.services.tenant_user_store as tus

    tus._tenant_user_store = None
    import backend.services.dialog_store as ds

    ds._dialog_store = None
    import backend.services.knowledge_base_store as kbs

    kbs._knowledge_base_store = None
    import backend.services.conversation_store as cs

    cs._conversation_store = None
    import backend.services.llm_store as ls

    ls._llm_store = None
    import backend.services.connector_store as cons

    cons._connector_store = None
    import backend.services.canvas_store as cas

    cas._canvas_store = None
    import backend.services.evaluation_store as es

    es._evaluation_store = None
    import backend.services.system_store as ss

    ss._system_store = None

    print("✅ Test database initialized (SQLite file)")


def teardown_test_db():
    """Drop tables and remove test database file."""
    global _test_db
    if _test_db:
        _test_db.close()
        _test_db = None
    try:
        os.remove(_test_db_path)
    except Exception:
        pass
    print("✅ Test database cleaned")


class APITestBase:
    """Base class for all API tests."""

    @classmethod
    def setup_class(cls):
        """Set up test environment once per test class."""
        setup_test_db()
        # Create test tenant and user synchronously for simplicity
        cls.test_tenant_id = str(uuid.uuid4()).replace("-", "")[:32]
        cls.test_user_id = str(uuid.uuid4()).replace("-", "")[:32]

        # Create tenant directly using model
        Tenant.create(
            id=cls.test_tenant_id,
            name="Test Tenant",
            llm_id="llama3.2:latest",
            embd_id="nomic-embed-text:latest",
            parser_ids="pdf,docx,txt,md,html",
        )

        # Create user using model's create_user method
        User.create_user(
            email="test@example.com",
            password=hash_password("testpass"),
            username="testuser",
        )
        # Get the created user ID (assumes email unique)
        user = User.get(User.email == "test@example.com")
        cls.test_user_id = user.id

        # Link user to tenant
        UserTenant.create(
            user_id=cls.test_user_id,
            tenant_id=cls.test_tenant_id,
            role="owner",
            invited_by=cls.test_user_id,
        )

        # Override get_current_user dependency to return our test user
        async def override_get_current_user():
            user_store = get_tenant_user_store()
            user = await run_db_operation(user_store.get_user, cls.test_user_id)
            if not user:
                raise Exception("Test user not found")
            return user

        app.dependency_overrides[get_current_user] = override_get_current_user

        # Create TestClient
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        """Clean up after all tests in the class."""
        app.dependency_overrides = {}
        teardown_test_db()

    def create_dialog(
        self, name="Test Dialog", llm_id="llama3.2:latest", kb_ids=None, **kwargs
    ):
        """Helper to create a dialog for tests."""
        if kb_ids is None:
            kb_ids = []
        store = get_dialog_store()
        dialog = asyncio.run(
            run_db_operation(
                store.create_dialog,
                tenant_id=self.test_tenant_id,
                name=name,
                llm_id=llm_id,
                created_by=self.test_user_id,
                kb_ids=kb_ids,
                **kwargs,
            )
        )
        return dialog

    def create_knowledgebase(self, name="Test KB", created_by=None, **kwargs):
        """Helper to create a knowledge base."""
        if created_by is None:
            created_by = self.test_user_id
        store = get_knowledge_base_store()
        kb = asyncio.run(
            run_db_operation(
                store.create_knowledgebase,
                tenant_id=self.test_tenant_id,
                name=name,
                created_by=created_by,
                **kwargs,
            )
        )
        return kb
