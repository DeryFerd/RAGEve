"""
Comprehensive unit tests for all store service classes.

Stores tested: TenantUserStore, KnowledgeBaseStore, DialogStore,
ConversationStore, LLMStore, ConnectorStore, CanvasStore, EvaluationStore, SystemStore.
Run: uv run python test/test_stores.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

import peewee
from peewee import SqliteDatabase

import backend.models_peewee as mp
from backend.config_loader import settings
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
from backend.services.auth import hash_password, verify_password
from backend.services.canvas_store import get_canvas_store
from backend.services.connector_store import get_connector_store
from backend.services.conversation_store import get_conversation_store
from backend.services.database import _executor, run_db_operation
from backend.services.dialog_store import get_dialog_store
from backend.services.evaluation_store import get_evaluation_store
from backend.services.knowledge_base_store import get_knowledge_base_store
from backend.services.llm_store import get_llm_store
from backend.services.system_store import get_system_store

# Import all store getters
from backend.services.tenant_user_store import get_tenant_user_store

# Global test database reference
_test_db: SqliteDatabase = None


async def setup_test_db():
    """Initialize a file-based SQLite database for testing."""
    global _test_db
    _test_db = SqliteDatabase("./test_stores.db")

    # List of all models to bind
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

    # Bind models to test database
    for model in models:
        model._meta.database = _test_db

    # Create tables
    await asyncio.get_event_loop().run_in_executor(
        _executor, lambda: _test_db.create_tables(models, safe=True)
    )

    # Override the global database singleton
    mp._database = _test_db

    # Reset all store singletons
    for module_name, attr_name in [
        ("backend.services.tenant_user_store", "_tenant_user_store"),
        ("backend.services.knowledge_base_store", "_kb_store"),
        ("backend.services.dialog_store", "_dialog_store"),
        ("backend.services.conversation_store", "_conversation_store"),
        ("backend.services.llm_store", "_llm_store"),
        ("backend.services.connector_store", "_connector_store"),
        ("backend.services.canvas_store", "_canvas_store"),
        ("backend.services.evaluation_store", "_evaluation_store"),
        ("backend.services.system_store", "_system_store"),
    ]:
        if module_name in sys.modules:
            mod = sys.modules[module_name]
            if hasattr(mod, attr_name):
                setattr(mod, attr_name, None)

    print("Test database initialized (file: ./test_stores.db).")


async def teardown_test_db():
    """Clean up test database."""
    global _test_db
    if _test_db:
        await asyncio.get_event_loop().run_in_executor(_executor, _test_db.close)
        _test_db = None
    try:
        import os

        if os.path.exists("./test_stores.db"):
            os.remove("./test_stores.db")
    except Exception:
        pass
    print("Test database closed and cleaned.")


# ==================== TenantUserStore Tests ====================


async def test_tenant_user_store():
    store = get_tenant_user_store()

    # Create user
    user = await run_db_operation(
        store.create_user,
        email="user@example.com",
        password=hash_password("password123"),
        username="testuser",
        full_name="Test User",
    )
    assert user.id is not None
    assert user.email == "user@example.com"
    print("✓ TenantUserStore.create_user works")

    # Get user by email
    fetched = await run_db_operation(store.get_user_by_email, "user@example.com")
    assert fetched is not None
    assert fetched.id == user.id
    print("✓ TenantUserStore.get_user_by_email works")

    # Get user by username
    fetched = await run_db_operation(store.get_user_by_username, "testuser")
    assert fetched is not None
    assert fetched.id == user.id
    print("✓ TenantUserStore.get_user_by_username works")

    # Get user by ID
    fetched = await run_db_operation(store.get_user, user.id)
    assert fetched is not None
    assert fetched.id == user.id
    print("✓ TenantUserStore.get_user works")

    # Create tenant
    tenant = await run_db_operation(
        store.create_tenant,
        name="Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf,docx",
        created_by=user.id,
    )
    assert tenant.id is not None
    print("✓ TenantUserStore.create_tenant works")

    # Get tenant
    fetched_tenant = await run_db_operation(store.get_tenant, tenant.id)
    assert fetched_tenant is not None
    assert fetched_tenant.name == "Test Tenant"
    print("✓ TenantUserStore.get_tenant works")

    # Add user to tenant
    user_tenant = await run_db_operation(
        store.add_user_to_tenant,
        user_id=user.id,
        tenant_id=tenant.id,
        invited_by=user.id,
        role="owner",
    )
    assert user_tenant.user_id == user.id
    assert user_tenant.tenant_id == tenant.id
    print("✓ TenantUserStore.add_user_to_tenant works")

    # Get tenants for user
    tenants = await run_db_operation(store.get_tenants_for_user, user.id)
    assert len(tenants) == 1
    assert tenants[0].id == tenant.id
    print("✓ TenantUserStore.get_tenants_for_user works")

    # Get users in tenant
    users = await run_db_operation(store.get_users_in_tenant, tenant.id)
    assert len(users) == 1
    assert users[0]["id"] == user.id
    print("✓ TenantUserStore.get_users_in_tenant works")

    # Get user role in tenant
    role = await run_db_operation(store.get_user_role_in_tenant, user.id, tenant.id)
    assert role == "owner"
    print("✓ TenantUserStore.get_user_role_in_tenant works")

    # Remove user from tenant
    removed = await run_db_operation(store.remove_user_from_tenant, user.id, tenant.id)
    assert removed is True
    tenants = await run_db_operation(store.get_tenants_for_user, user.id)
    assert len(tenants) == 0
    print("✓ TenantUserStore.remove_user_from_tenant works")

    # List all users
    all_users = await run_db_operation(store.list_all_users)
    assert len(all_users) >= 1
    print("✓ TenantUserStore.list_all_users works")

    # Update user
    updated_user = await run_db_operation(
        store.update_user,
        user.id,
        full_name="Updated Name",
        is_superuser=True,
    )
    assert updated_user is not None
    assert updated_user.full_name == "Updated Name"
    print("✓ TenantUserStore.update_user works")

    # Deactivate user
    deactivated = await run_db_operation(store.deactivate_user, user.id)
    assert deactivated is True
    inactive_user = await run_db_operation(store.get_user, user.id)
    assert inactive_user.status == "0"
    print("✓ TenantUserStore.deactivate_user works")


# ==================== KnowledgeBaseStore Tests ====================


async def test_knowledge_base_store():
    store = get_knowledge_base_store()
    tenant_user_store = get_tenant_user_store()

    # Create tenant and user
    tenant = await run_db_operation(
        tenant_user_store.create_tenant,
        name="KB Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf",
        created_by="user123",
    )
    user = await run_db_operation(
        tenant_user_store.create_user,
        email="kbuser@example.com",
        password=hash_password("pass"),
        username="kbuser",
    )

    # Create knowledgebase
    kb = await run_db_operation(
        store.create_knowledgebase,
        tenant_id=tenant.id,
        name="Test Knowledgebase",
        description="Test description",
        created_by=user.id,
    )
    assert kb.id is not None
    assert kb.name == "Test Knowledgebase"
    print("✓ KnowledgeBaseStore.create_knowledgebase works")

    # Get knowledgebase
    fetched = await run_db_operation(store.get_knowledgebase, kb.id)
    assert fetched is not None
    assert fetched.name == "Test Knowledgebase"
    print("✓ KnowledgeBaseStore.get_knowledgebase works")

    # List knowledgebases by tenant
    kbs, total = await run_db_operation(store.list_knowledgebases, tenant_id=tenant.id)
    assert len(kbs) >= 1
    print("✓ KnowledgeBaseStore.list_knowledgebases works")

    # Update knowledgebase
    updated = await run_db_operation(
        store.update_knowledgebase,
        kb.id,
        name="Updated KB",
        description="Updated desc",
    )
    assert updated.name == "Updated KB"
    print("✓ KnowledgeBaseStore.update_knowledgebase works")

    # Create document
    doc = await run_db_operation(
        store.create_document,
        kb_id=kb.id,
        name="Test Document",
        parser_id="pdf",
        created_by=user.id,
        doc_type="pdf",
    )
    assert doc.id is not None
    print("✓ KnowledgeBaseStore.create_document works")

    # Get document
    fetched_doc = await run_db_operation(store.get_document, doc.id)
    assert fetched_doc is not None
    assert fetched_doc.name == "Test Document"
    print("✓ KnowledgeBaseStore.get_document works")

    # List documents
    docs, total = await run_db_operation(store.list_documents, kb_id=kb.id)
    assert len(docs) >= 1
    print("✓ KnowledgeBaseStore.list_documents works")

    # Update document progress
    updated_doc = await run_db_operation(
        store.update_document_progress,
        doc.id,
        progress=50.0,
        progress_msg="Processing...",
    )
    assert updated_doc is not None
    print("✓ KnowledgeBaseStore.update_document_progress works")

    # Complete document
    completed_doc = await run_db_operation(
        store.complete_document,
        doc.id,
        duration=10.5,
        doc_metadata={"pages": 5},
    )
    assert completed_doc is not None
    print("✓ KnowledgeBaseStore.complete_document works")

    # Create file
    file = await run_db_operation(
        store.create_file,
        name="test.pdf",
        size=1024,
        file_type="pdf",
        created_by=user.id,
    )
    assert file.id is not None
    print("✓ KnowledgeBaseStore.create_file works")

    # Get file
    fetched_file = await run_db_operation(store.get_file, file.id)
    assert fetched_file is not None
    print("✓ KnowledgeBaseStore.get_file works")

    # Link file to document
    link = await run_db_operation(
        store.link_file_to_document,
        file_id=file.id,
        doc_id=doc.id,
    )
    assert link is not None
    print("✓ KnowledgeBaseStore.link_file_to_document works")

    # Get documents for file
    file_docs = await run_db_operation(store.get_documents_for_file, file.id)
    assert len(file_docs) == 1
    assert file_docs[0].id == doc.id
    print("✓ KnowledgeBaseStore.get_documents_for_file works")

    # Create task
    task = await run_db_operation(
        store.create_task,
        doc_id=doc.id,
        task_type="embedding",
        from_page=0,
        to_page=5,
    )
    assert task.id is not None
    print("✓ KnowledgeBaseStore.create_task works")

    # Get task
    fetched_task = await run_db_operation(store.get_task, task.id)
    assert fetched_task is not None
    print("✓ KnowledgeBaseStore.get_task works")

    # Start task
    started = await run_db_operation(store.start_task, task.id)
    assert started is not None
    print("✓ KnowledgeBaseStore.start_task works")

    # Update task progress
    updated_task = await run_db_operation(
        store.update_task_progress,
        task.id,
        progress=75.0,
        msg="Half done",
    )
    assert updated_task is not None
    print("✓ KnowledgeBaseStore.update_task_progress works")

    # Complete task
    completed = await run_db_operation(store.complete_task, task.id, 15.0)
    assert completed is not None
    print("✓ KnowledgeBaseStore.complete_task works")

    # Get document tasks
    doc_tasks = await run_db_operation(store.get_document_tasks, doc.id)
    assert len(doc_tasks) >= 1
    print("✓ KnowledgeBaseStore.get_document_tasks works")

    # Delete knowledgebase (cascades to documents, files, tasks)
    deleted = await run_db_operation(store.delete_knowledgebase, kb.id)
    assert deleted is True
    print("✓ KnowledgeBaseStore.delete_knowledgebase works")


# ==================== DialogStore Tests ====================


async def test_dialog_store():
    store = get_dialog_store()
    tenant_user_store = get_tenant_user_store()

    # Create tenant
    tenant = await run_db_operation(
        tenant_user_store.create_tenant,
        name="Dialog Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf",
        created_by="user123",
    )

    # Create dialog
    dialog = await run_db_operation(
        store.create_dialog,
        tenant_id=tenant.id,
        name="Test Dialog",
        llm_id="llama3.2:latest",
        created_by="user123",
        description="A test dialog",
        prompt_type="chat",
        llm_setting={"temperature": 0.7},
    )
    assert dialog.id is not None
    assert dialog.name == "Test Dialog"
    print("✓ DialogStore.create_dialog works")

    # Get dialog
    fetched = await run_db_operation(store.get_dialog, dialog.id)
    assert fetched is not None
    assert fetched.name == "Test Dialog"
    print("✓ DialogStore.get_dialog works")

    # Get dialog by name
    fetched_name = await run_db_operation(
        store.get_dialog_by_name, tenant.id, "Test Dialog"
    )
    assert fetched_name is not None
    assert fetched_name.id == dialog.id
    print("✓ DialogStore.get_dialog_by_name works")

    # Update dialog
    updated = await run_db_operation(
        store.update_dialog,
        dialog.id,
        name="Updated Dialog",
        llm_setting={"temperature": 0.5},
    )
    assert updated.name == "Updated Dialog"
    print("✓ DialogStore.update_dialog works")

    # List dialogs
    dialogs, total = await run_db_operation(store.list_dialogs, tenant_id=tenant.id)
    assert len(dialogs) >= 1
    print("✓ DialogStore.list_dialogs works")

    # Delete dialog
    deleted = await run_db_operation(store.delete_dialog, dialog.id)
    assert deleted is True
    print("✓ DialogStore.delete_dialog works")


# ==================== ConversationStore Tests ====================


async def test_conversation_store():
    store = get_conversation_store()
    tenant_user_store = get_tenant_user_store()
    dialog_store = get_dialog_store()

    # Create tenant and user
    tenant = await run_db_operation(
        tenant_user_store.create_tenant,
        name="Conv Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf",
        created_by="user123",
    )
    user = await run_db_operation(
        tenant_user_store.create_user,
        email="convuser@example.com",
        password=hash_password("pass"),
        username="convuser",
    )

    # Create dialog
    dialog = await run_db_operation(
        dialog_store.create_dialog,
        tenant_id=tenant.id,
        name="Conv Dialog",
        llm_id="llama3.2:latest",
        created_by=user.id,
    )

    # Create conversation
    conv = await run_db_operation(
        store.create_conversation,
        dialog_id=dialog.id,
        user_id=user.id,
        name="Test Conversation",
        messages=[],
    )
    assert conv.id is not None
    assert conv.name == "Test Conversation"
    print("✓ ConversationStore.create_conversation works")

    # Get conversation
    fetched = await run_db_operation(store.get_conversation, conv.id)
    assert fetched is not None
    assert fetched.name == "Test Conversation"
    print("✓ ConversationStore.get_conversation works")

    # Append message
    msg1 = await run_db_operation(
        store.append_message,
        conversation_id=conv.id,
        role="user",
        content="Hello, world!",
        token_count=10,
    )
    assert msg1 is not None
    assert msg1["role"] == "user"
    assert msg1["content"] == "Hello, world!"
    print("✓ ConversationStore.append_message works")

    # Append another message
    msg2 = await run_db_operation(
        store.append_message,
        conversation_id=conv.id,
        role="assistant",
        content="Hi there!",
        token_count=5,
    )
    assert msg2["role"] == "assistant"
    print("✓ ConversationStore.append_message (2nd) works")

    # Get messages via conversation model
    conv_model = await run_db_operation(store.get_conversation, conv.id)
    messages = conv_model.get_messages()
    assert len(messages) == 2
    assert messages[0]["content"] == "Hello, world!"
    assert messages[1]["content"] == "Hi there!"
    print("✓ Conversation.get_messages works")

    # Get conversation context (max_turns)
    context = await run_db_operation(
        store.get_conversation_context, conv.id, max_turns=1
    )
    assert len(context) == 2  # user + assistant
    print("✓ ConversationStore.get_conversation_context works")

    # Update conversation
    updated_conv = await run_db_operation(
        store.update_conversation,
        conv.id,
        name="Updated Conversation",
        reference=["ref1"],
    )
    assert updated_conv.name == "Updated Conversation"
    print("✓ ConversationStore.update_conversation works")

    # List conversations by dialog
    convs, total = await run_db_operation(store.list_conversations, dialog_id=dialog.id)
    assert len(convs) >= 1
    print("✓ ConversationStore.list_conversations works")

    # Delete conversation
    deleted = await run_db_operation(store.delete_conversation, conv.id)
    assert deleted is True
    msgs = await run_db_operation(store.get_conversation, conv.id)
    assert msgs is None
    print("✓ ConversationStore.delete_conversation works")


# ==================== LLMStore Tests ====================


async def test_llm_store():
    store = get_llm_store()

    # Create factory
    factory = await run_db_operation(
        store.create_factory,
        name="Test Factory",
        llm_name="llama3.2:latest",
        api_base="http://localhost:11434",
        description="Test LLM factory",
        status="1",
        rank=1,
    )
    assert factory.id is not None
    assert factory.name == "Test Factory"
    print("✓ LLMStore.create_factory works")

    # Get factory
    fetched = await run_db_operation(store.get_factory, "Test Factory")
    assert fetched is not None
    assert fetched.llm_name == "llama3.2:latest"
    print("✓ LLMStore.get_factory works")

    # List factories
    factories = await run_db_operation(store.list_factories)
    assert len(factories) >= 1
    print("✓ LLMStore.list_factories works")

    # Update factory
    updated = await run_db_operation(
        store.update_factory,
        "Test Factory",
        description="Updated description",
    )
    assert updated.description == "Updated description"
    print("✓ LLMStore.update_factory works")

    # Create LLM
    llm = await run_db_operation(
        store.create_llm,
        fid="Test Factory",
        llm_name="llama3.2:latest",
        model_type="chat",
        max_tokens=4096,
        tags=["test"],
        is_tools=False,
    )
    assert llm.id is not None
    print("✓ LLMStore.create_llm works")

    # Get LLM
    fetched_llm = await run_db_operation(store.get_llm, llm.id)
    assert fetched_llm is not None
    assert fetched_llm.llm_name == "llama3.2:latest"
    print("✓ LLMStore.get_llm works")

    # List LLMs
    llms = await run_db_operation(store.list_llms, fid="Test Factory")
    assert len(llms) >= 1
    print("✓ LLMStore.list_llms works")

    # Update LLM usage
    updated_llm = await run_db_operation(store.update_llm_usage, llm.id, 100)
    assert updated_llm.used_tokens == 100
    print("✓ LLMStore.update_llm_usage works")

    # Set tenant LLM
    tenant_llm = await run_db_operation(
        store.set_tenant_llm,
        tenant_id="tenant123",
        llm_factory="Test Factory",
        llm_name="llama3.2:latest",
        model_type="chat",
        api_key="testkey",
        max_tokens=8192,
    )
    assert tenant_llm.id is not None
    print("✓ LLMStore.set_tenant_llm works")

    # Get tenant LLM
    fetched_tllm = await run_db_operation(store.get_tenant_llm, "tenant123", "chat")
    assert fetched_tllm is not None
    assert fetched_tllm.llm_name == "llama3.2:latest"
    print("✓ LLMStore.get_tenant_llm works")

    # List tenant LLMs
    tllms = await run_db_operation(store.list_tenant_llms, "tenant123")
    assert len(tllms) >= 1
    print("✓ LLMStore.list_tenant_llms works")

    # Delete tenant LLM
    deleted = await run_db_operation(store.delete_tenant_llm, "tenant123", "chat")
    assert deleted is True
    print("✓ LLMStore.delete_tenant_llm works")


# ==================== ConnectorStore Tests ====================


async def test_connector_store():
    store = get_connector_store()
    tenant_user_store = get_tenant_user_store()
    kb_store = get_knowledge_base_store()

    # Create tenant
    tenant = await run_db_operation(
        tenant_user_store.create_tenant,
        name="Connector Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf",
        created_by="user123",
    )

    # Create knowledgebase for linking
    kb = await run_db_operation(
        kb_store.create_knowledgebase,
        tenant_id=tenant.id,
        name="Connector KB",
        created_by="user123",
    )

    # Create connector
    connector = await run_db_operation(
        store.create_connector,
        tenant_id=tenant.id,
        name="Test Connector",
        source="web",
        input_type="url",
        config={"url": "https://example.com"},
        refresh_freq=3600,
    )
    assert connector.id is not None
    assert connector.name == "Test Connector"
    print("✓ ConnectorStore.create_connector works")

    # Get connector
    fetched = await run_db_operation(store.get_connector, connector.id)
    assert fetched is not None
    assert fetched.name == "Test Connector"
    print("✓ ConnectorStore.get_connector works")

    # List connectors
    connectors = await run_db_operation(store.list_connectors, tenant_id=tenant.id)
    assert len(connectors) >= 1
    print("✓ ConnectorStore.list_connectors works")

    # Update connector
    updated = await run_db_operation(
        store.update_connector,
        connector.id,
        name="Updated Connector",
        config={"url": "https://updated.com"},
    )
    assert updated.name == "Updated Connector"
    print("✓ ConnectorStore.update_connector works")

    # Link connector to knowledgebase
    link = await run_db_operation(
        store.link_connector_to_kb,
        connector_id=connector.id,
        kb_id=kb.id,
        auto_parse="1",
    )
    assert link is not None
    print("✓ ConnectorStore.link_connector_to_kb works")

    # Get knowledgebases for connector
    conn_kbs = await run_db_operation(
        store.get_knowledgebases_for_connector, connector.id
    )
    assert len(conn_kbs) == 1
    assert conn_kbs[0].id == kb.id
    print("✓ ConnectorStore.get_knowledgebases_for_connector works")

    # Create sync log
    sync_log = await run_db_operation(
        store.create_sync_log,
        connector_id=connector.id,
        status="completed",
        kb_id=kb.id,
        new_docs_indexed=5,
        total_docs_indexed=10,
    )
    assert sync_log.id is not None
    print("✓ ConnectorStore.create_sync_log works")

    # Get sync logs
    logs = await run_db_operation(store.get_sync_logs, connector_id=connector.id)
    assert len(logs) >= 1
    print("✓ ConnectorStore.get_sync_logs works")

    # Update sync log
    updated_log = await run_db_operation(
        store.update_sync_log,
        sync_log.id,
        status="failed",
        error_msg="Test error",
    )
    assert updated_log.status == "failed"
    print("✓ ConnectorStore.update_sync_log works")

    # Unlink connector from kb
    unlinked = await run_db_operation(
        store.unlink_connector_from_kb,
        connector.id,
        kb.id,
    )
    assert unlinked is True
    print("✓ ConnectorStore.unlink_connector_from_kb works")

    # Delete connector
    deleted = await run_db_operation(store.delete_connector, connector.id)
    assert deleted is True
    print("✓ ConnectorStore.delete_connector works")


# ==================== CanvasStore Tests ====================


async def test_canvas_store():
    store = get_canvas_store()
    tenant_user_store = get_tenant_user_store()

    # Create user (canvas is user-centric, no tenant needed)
    user = await run_db_operation(
        tenant_user_store.create_user,
        email="canvasuser@example.com",
        password=hash_password("pass"),
        username="canvasuser",
    )

    # Create canvas
    canvas = await run_db_operation(
        store.create_canvas,
        user_id=user.id,
        title="Test Canvas",
        description="A test canvas",
        canvas_type="agent",
        canvas_category="agent_canvas",
        dsl={"nodes": [{"id": "1", "type": "input"}]},
    )
    assert canvas.id is not None
    assert canvas.title == "Test Canvas"
    print("✓ CanvasStore.create_canvas works")

    # Get canvas
    fetched = await run_db_operation(store.get_canvas, canvas.id)
    assert fetched is not None
    assert fetched.title == "Test Canvas"
    print("✓ CanvasStore.get_canvas works")

    # List user canvases
    user_canvases = await run_db_operation(store.list_user_canvases, user_id=user.id)
    assert len(user_canvases) >= 1
    print("✓ CanvasStore.list_user_canvases works")

    # Update canvas
    updated = await run_db_operation(
        store.update_canvas,
        canvas.id,
        title="Updated Canvas",
        dsl={"nodes": [{"id": "2", "type": "output"}]},
    )
    assert updated.title == "Updated Canvas"
    print("✓ CanvasStore.update_canvas works")

    # Create template
    template = await run_db_operation(
        store.create_template,
        title={"en": "Test Template"},
        description={"en": "A test template"},
        canvas_type="agent",
        dsl={"nodes": []},
    )
    assert template.id is not None
    print("✓ CanvasStore.create_template works")

    # Get template
    fetched_template = await run_db_operation(store.get_template, template.id)
    assert fetched_template is not None
    print("✓ CanvasStore.get_template works")

    # List templates
    templates = await run_db_operation(store.list_templates)
    assert len(templates) >= 1
    print("✓ CanvasStore.list_templates works")

    # Update template
    updated_template = await run_db_operation(
        store.update_template,
        template.id,
        title={"en": "Updated Template"},
    )
    assert updated_template.title["en"] == "Updated Template"
    print("✓ CanvasStore.update_template works")

    # Delete canvas
    deleted = await run_db_operation(store.delete_canvas, canvas.id)
    assert deleted is True
    print("✓ CanvasStore.delete_canvas works")

    # Delete template
    deleted_tmpl = await run_db_operation(store.delete_template, template.id)
    assert deleted_tmpl is True
    print("✓ CanvasStore.delete_template works")


# ==================== EvaluationStore Tests ====================


async def test_evaluation_store():
    store = get_evaluation_store()
    tenant_user_store = get_tenant_user_store()

    # Create tenant
    tenant = await run_db_operation(
        tenant_user_store.create_tenant,
        name="Eval Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf",
        created_by="user123",
    )

    # Create evaluation dataset
    dataset = await run_db_operation(
        store.create_dataset,
        tenant_id=tenant.id,
        name="Test Evaluation Dataset",
        created_by="user123",
        description="Test dataset",
        kb_ids=["kb1", "kb2"],
        status=1,
    )
    assert dataset.id is not None
    assert dataset.name == "Test Evaluation Dataset"
    print("✓ EvaluationStore.create_dataset works")

    # Get dataset
    fetched = await run_db_operation(store.get_dataset, dataset.id)
    assert fetched is not None
    assert fetched.name == "Test Evaluation Dataset"
    print("✓ EvaluationStore.get_dataset works")

    # List datasets
    datasets, total = await run_db_operation(store.list_datasets, tenant_id=tenant.id)
    assert len(datasets) >= 1
    print("✓ EvaluationStore.list_datasets works")

    # Add case
    case = await run_db_operation(
        store.add_case,
        dataset_id=dataset.id,
        question="What is RAG?",
        reference_answer="Retrieval-Augmented Generation",
        relevant_doc_ids=["doc1"],
        relevant_chunk_ids=["chunk1"],
        metadata={"difficulty": "easy"},
    )
    assert case.id is not None
    print("✓ EvaluationStore.add_case works")

    # Get cases
    cases = await run_db_operation(store.get_cases, dataset.id)
    assert len(cases) >= 1
    assert cases[0].question == "What is RAG?"
    print("✓ EvaluationStore.get_cases works")

    # Create evaluation run
    run = await run_db_operation(
        store.create_run,
        dataset_id=dataset.id,
        dialog_id="dialog123",
        name="Test Run",
        created_by="user123",
        config_snapshot={"model": "llama3.2"},
        status="PENDING",
    )
    assert run.id is not None
    print("✓ EvaluationStore.create_run works")

    # Get run
    fetched_run = await run_db_operation(store.get_run, run.id)
    assert fetched_run is not None
    assert fetched_run.name == "Test Run"
    print("✓ EvaluationStore.get_run works")

    # List runs
    runs, total = await run_db_operation(store.list_runs, dataset_id=dataset.id)
    assert len(runs) >= 1
    print("✓ EvaluationStore.list_runs works")

    # Record result
    result = await run_db_operation(
        store.record_result,
        run_id=run.id,
        case_id=case.id,
        generated_answer="Retrieval-Augmented Generation is...",
        retrieved_chunks=[{"id": "chunk1", "text": "..."}],
        metrics={"ndcg": 0.85, "relevance": 0.9},
        execution_time=1.5,
        token_usage={"input": 100, "output": 50},
    )
    assert result.id is not None
    print("✓ EvaluationStore.record_result works")

    # Get results
    results = await run_db_operation(store.get_results, run.id)
    assert len(results) >= 1
    print("✓ EvaluationStore.get_results works")

    # Get result stats
    stats = await run_db_operation(store.get_result_stats, run.id)
    assert "ndcg" in stats
    assert "mean" in stats["ndcg"]
    print("✓ EvaluationStore.get_result_stats works")

    # Finish run
    finished = await run_db_operation(
        store.finish_run,
        run.id,
        metrics_summary={"avg_ndcg": 0.87},
        complete_time=int(datetime.now(timezone.utc).timestamp()),
    )
    assert finished.status == "COMPLETED"
    print("✓ EvaluationStore.finish_run works")


# ==================== SystemStore Tests ====================


async def test_system_store():
    store = get_system_store()

    # Set system setting
    setting = await run_db_operation(
        store.set_setting,
        name="test_setting",
        value={"nested": {"value": 123}},
        data_type="json",
    )
    assert setting.name == "test_setting"
    print("✓ SystemStore.set_setting works")

    # Get setting
    val = await run_db_operation(store.get_setting, "test_setting")
    assert val == {"nested": {"value": 123}}
    print("✓ SystemStore.get_setting works")

    # List settings
    settings_list = await run_db_operation(store.list_settings)
    assert len(settings_list) >= 1
    print("✓ SystemStore.list_settings works")

    # Create API token
    token = await run_db_operation(
        store.create_api_token,
        tenant_id="tenant123",
        token="test-token-abc123",
        dialog_id="dialog456",
        source="test",
    )
    assert token.tenant_id == "tenant123"
    assert token.token == "test-token-abc123"
    print("✓ SystemStore.create_api_token works")

    # Verify API token (returns token record)
    verified = await run_db_operation(store.verify_api_token, "test-token-abc123")
    assert verified is not None
    assert verified.tenant_id == token.tenant_id
    assert verified.token == token.token
    print("✓ SystemStore.verify_api_token works")

    # Revoke (delete) API token
    revoked = await run_db_operation(
        store.revoke_api_token, "tenant123", "test-token-abc123"
    )
    assert revoked is True
    print("✓ SystemStore.revoke_api_token works")

    # Log API conversation
    log = await run_db_operation(
        store.log_api_conversation,
        dialog_id="dialog456",
        user_id="user789",
        message=[{"role": "user", "content": "test"}],
        reference=[{"doc": "doc1"}],
        tokens=150,
        duration=2.5,
    )
    assert log.id is not None
    print("✓ SystemStore.log_api_conversation works")

    # Create MCP server
    mcp = await run_db_operation(
        store.create_mcp_server,
        tenant_id="tenant123",
        name="Test MCP",
        url="https://mcp.example.com",
        server_type="stdio",
        description="Test MCP server",
        variables={"key": "value"},
    )
    assert mcp.id is not None
    assert mcp.name == "Test MCP"
    print("✓ SystemStore.create_mcp_server works")

    # List MCP servers
    mcps = await run_db_operation(store.list_mcp_servers, "tenant123")
    assert len(mcps) >= 1
    print("✓ SystemStore.list_mcp_servers works")

    # Delete MCP server
    deleted_mcp = await run_db_operation(store.delete_mcp_server, mcp.id)
    assert deleted_mcp is True
    print("✓ SystemStore.delete_mcp_server works")

    # Create search config
    search = await run_db_operation(
        store.create_search,
        tenant_id="tenant123",
        name="Test Search",
        created_by="user123",
        description="Test search preset",
        search_config={"filters": {}},
    )
    assert search.id is not None
    print("✓ SystemStore.create_search works")

    # List searches
    searches = await run_db_operation(store.list_searches, tenant_id="tenant123")
    assert len(searches) >= 1
    print("✓ SystemStore.list_searches works")

    # Create pipeline log
    pipe_log = await run_db_operation(
        store.create_pipeline_log,
        document_id="doc123",
        tenant_id="tenant123",
        kb_id="kb123",
        parser_id="pdf",
        document_name="test.pdf",
        document_suffix=".pdf",
        document_type="pdf",
        source_from="upload",
        task_type="embedding",
        pipeline_id="pipeline1",
    )
    assert pipe_log.id is not None
    print("✓ SystemStore.create_pipeline_log works")

    # Update pipeline log progress
    updated_pipe = await run_db_operation(
        store.update_pipeline_log_progress,
        pipe_log.id,
        progress=75.0,
        msg="Processing",
    )
    assert updated_pipe.progress == 75.0
    print("✓ SystemStore.update_pipeline_log_progress works")

    # Get pipeline logs
    pipe_logs = await run_db_operation(store.get_pipeline_logs, document_id="doc123")
    assert len(pipe_logs) >= 1
    print("✓ SystemStore.get_pipeline_logs works")


# ==================== MCP and Search Direct Model Tests ====================


async def test_mcp_and_search_models():
    """Test MCP and Search models directly (no store service yet)."""
    import uuid

    # Create MCP with explicit id
    mcp = await asyncio.to_thread(
        MCP.create,
        id=str(uuid.uuid4()).replace("-", "")[:32],
        name="Direct MCP",
        description="Direct MCP creation",
        tenant_id="tenant123",
        url="https://example.com",
        server_type="stdio",
    )
    assert mcp.id is not None
    print("✓ MCP model direct creation works")

    # Create Search with explicit id
    search = await asyncio.to_thread(
        Search.create,
        id=str(uuid.uuid4()).replace("-", "")[:32],
        name="Direct Search",
        description="Direct search creation",
        tenant_id="tenant123",
        created_by="system",
        search_config={"query": "test"},
    )
    assert search.id is not None
    print("✓ Search model direct creation works")


async def main():
    print("=" * 60)
    print("Running ALL Store Service Unit Tests")
    print("=" * 60)
    await setup_test_db()
    try:
        print("\n--- TenantUserStore ---")
        await test_tenant_user_store()

        print("\n--- KnowledgeBaseStore ---")
        await test_knowledge_base_store()

        print("\n--- DialogStore ---")
        await test_dialog_store()

        print("\n--- ConversationStore ---")
        await test_conversation_store()

        print("\n--- LLMStore ---")
        await test_llm_store()

        print("\n--- ConnectorStore ---")
        await test_connector_store()

        print("\n--- CanvasStore ---")
        await test_canvas_store()

        print("\n--- EvaluationStore ---")
        await test_evaluation_store()

        print("\n--- SystemStore ---")
        await test_system_store()

        print("\n--- MCP & Search Models ---")
        await test_mcp_and_search_models()

        print("\n" + "=" * 60)
        print("✅ ALL STORE SERVICE TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        import traceback

        traceback.print_exc()
        raise
    finally:
        await teardown_test_db()


if __name__ == "__main__":
    asyncio.run(main())
