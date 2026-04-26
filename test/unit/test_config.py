"""
Test configuration for using SQLite in-memory database.

This module provides a base test class that sets up an isolated
SQLite database for each test, overriding the global Peewee database.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import peewee
from peewee import SqliteDatabase

# Add project root to path
import sys
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from backend.models_peewee import (
    # User & Tenancy
    User, Tenant, UserTenant,
    # Knowledge Base
    Knowledgebase, Document, File, File2Document, Task,
    # Dialog
    Dialog, Conversation,
    # LLM
    LLMFactories, LLM, TenantLLM,
    # Connector
    Connector, Connector2Kb, SyncLogs,
    # Canvas
    UserCanvas, CanvasTemplate,
    # Evaluation
    EvaluationDataset, EvaluationCase, EvaluationRun, EvaluationResult,
    # System
    SystemSettings, APIToken, API4Conversation, MCP, Search, PipelineOperationLog,
    BaseModel as PeeweeBaseModel,
)
import backend.models_peewee as mp
from backend.services.database import _executor as db_executor


class TestDatabase:
    """Manages a test SQLite database with all models bound."""

    def __init__(self):
        self.db: SqliteDatabase | None = None
        self.models = [
            User, Tenant, UserTenant,
            Knowledgebase, Document, File, File2Document, Task,
            Dialog, Conversation,
            LLMFactories, LLM, TenantLLM,
            Connector, Connector2Kb, SyncLogs,
            UserCanvas, CanvasTemplate,
            EvaluationDataset, EvaluationCase, EvaluationRun, EvaluationResult,
            SystemSettings, APIToken, API4Conversation, MCP, Search, PipelineOperationLog,
        ]

    async def setup(self):
        """Create file-based test database and bind all models."""
        loop = asyncio.get_event_loop()
        # Use a file-based SQLite database so that schema is visible across threads
        # (in-memory databases are per-connection, which breaks when using thread pools)
        self.db = SqliteDatabase("./test_ragev_unit.db")

        # Bind all models to test database
        for model in self.models:
            model._meta.database = self.db

        # Create tables (run in executor to avoid blocking)
        await loop.run_in_executor(db_executor, lambda: self.db.create_tables(self.models, safe=True))

        # Override the global database singleton
        mp._database = self.db

        # Reset all store singletons
        # Clear module-level singletons
        for module in [
            "backend.services.tenant_user_store",
            "backend.services.dialog_store",
            "backend.services.conversation_store",
            "backend.services.knowledge_base_store",
            "backend.services.llm_store",
            "backend.services.connector_store",
            "backend.services.canvas_store",
            "backend.services.evaluation_store",
            "backend.services.system_store",
        ]:
            if module in sys.modules:
                mod = sys.modules[module]
                for attr in dir(mod):
                    if attr.startswith("_" + attr.lower()[:attr.find("_")] if "_" in attr else "_") and attr.endswith("_store"):
                        setattr(mod, attr, None)

        print("✓ Test database initialized (SQLite file: ./test_ragev_unit.db)")

    async def teardown(self):
        """Close database and clean up."""
        if self.db:
            await asyncio.get_event_loop().run_in_executor(db_executor, self.db.close)
            self.db = None
        mp._database = None
        # Delete the test database file
        try:
            import os
            if os.path.exists("./test_ragev_unit.db"):
                os.remove("./test_ragev_unit.db")
        except Exception:
            pass
        print("✓ Test database closed and cleaned")

    @staticmethod
    def generate_id(length: int = 32) -> str:
        """Generate a random ID."""
        import uuid
        return str(uuid.uuid4()).replace("-", "")[:length]
