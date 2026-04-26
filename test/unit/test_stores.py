"""
Comprehensive tests for all store services.

Tests CRUD operations, relationships, and business logic in the service layer.

Run: uv run python test/unit/test_stores.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from test.unit.test_config import TestDatabase

# Stores
from backend.services.tenant_user_store import get_tenant_user_store
from backend.services.knowledge_base_store import get_knowledge_base_store
from backend.services.dialog_store import get_dialog_store
from backend.services.conversation_store import get_conversation_store
from backend.services.llm_store import get_llm_store
from backend.services.connector_store import get_connector_store
from backend.services.canvas_store import get_canvas_store
from backend.services.evaluation_store import get_evaluation_store
from backend.services.system_store import get_system_store

# Models (for assertions and direct comparisons)
from backend.models_peewee import (
    User, Tenant, UserTenant,
    Knowledgebase, Document, File, File2Document, Task,
    Dialog, Conversation,
    LLMFactories, LLM, TenantLLM,
    Connector, Connector2Kb, SyncLogs,
    UserCanvas, CanvasTemplate,
    EvaluationDataset, EvaluationCase, EvaluationRun, EvaluationResult,
    SystemSettings, APIToken, MCP, PipelineOperationLog,
)

# Simple password hasher for tests
def hash_password(password: str) -> str:
    return f"test_hash_{password}"


# Test database fixture
test_db = TestDatabase()


def section(title: str):
    bar = "=" * 60
    print(f"\n{bar}\n  {title}\n{bar}")


def ok(msg):
    print(f"  ✓ {msg}")


def fail(msg):
    print(f"  ✗ {msg}")
    raise AssertionError(msg)


# ==================== TenantUserStore Tests ====================

async def test_tenant_user_store():
    section("TenantUserStore")
    store = get_tenant_user_store()

    # Tenant CRUD via store
    tenant = await asyncio.to_thread(
        store.create_tenant,
        name="Store Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        created_by="admin",
        parser_ids="pdf,docx",
    )
    assert tenant.id is not None
    assert tenant.name == "Store Test Tenant"
    ok("TenantUserStore.create_tenant")

    fetched = await asyncio.to_thread(store.get_tenant, tenant.id)
    assert fetched is not None
    assert fetched.id == tenant.id
    ok("TenantUserStore.get_tenant")

    # List tenants
    tenants, total = await asyncio.to_thread(
        store.list_tenants, created_by="admin"
    )
    assert len(tenants) >= 1
    ok("TenantUserStore.list_tenants")

    # Update tenant
    updated = await asyncio.to_thread(
        store.update_tenant,
        tenant.id,
        name="Renamed Store Tenant",
    )
    assert updated is not None
    assert updated.name == "Renamed Store Tenant"
    ok("TenantUserStore.update_tenant")

    # User CRUD via store
    user = await asyncio.to_thread(
        store.create_user,
        email="storetest@example.com",
        password=hash_password("pass"),
        username="storetest",
        full_name="Store Tester",
    )
    assert user.id is not None
    assert user.email == "storetest@example.com"
    ok("TenantUserStore.create_user")

    fetched_user = await asyncio.to_thread(store.get_user, user.id)
    assert fetched_user is not None
    assert fetched_user.id == user.id
    ok("TenantUserStore.get_user")

    # Get by email
    by_email = await asyncio.to_thread(
        store.get_user_by_email, "storetest@example.com"
    )
    assert by_email is not None
    assert by_email.id == user.id
    ok("TenantUserStore.get_user_by_email")

    # List users
    users, total = await asyncio.to_thread(store.list_users, is_active=True)
    assert len(users) >= 1
    ok("TenantUserStore.list_users")

    # Deactivate and reactivate
    deactivated = await asyncio.to_thread(store.deactivate_user, user.id)
    assert deactivated is True
    ok("TenantUserStore.deactivate_user")

    # Update user
    updated_user = await asyncio.to_thread(
        store.update_user,
        user.id,
        full_name="Updated Store User",
    )
    assert updated_user is not None
    assert updated_user.full_name == "Updated Store User"
    ok("TenantUserStore.update_user")

    # User-Tenant relationships
    ut = await asyncio.to_thread(
        store.add_user_to_tenant,
        user_id=user.id,
        tenant_id=tenant.id,
        invited_by=user.id,
        role="admin",
    )
    assert ut is not None
    ok("TenantUserStore.add_user_to_tenant")

    # Get tenants for user
    user_tenants = await asyncio.to_thread(
        store.get_tenants_for_user, user.id
    )
    assert len(user_tenants) >= 1
    assert any(t.id == tenant.id for t in user_tenants)
    ok("TenantUserStore.get_tenants_for_user")

    # Get users in tenant
    tenant_users = await asyncio.to_thread(
        store.get_users_in_tenant, tenant.id
    )
    assert len(tenant_users) >= 1
    assert any(u["id"] == user.id for u in tenant_users)
    ok("TenantUserStore.get_users_in_tenant")

    # Get user role in tenant
    role = await asyncio.to_thread(
        store.get_user_role_in_tenant, user.id, tenant.id
    )
    assert role == "admin"
    ok("TenantUserStore.get_user_role_in_tenant")

    # Remove user from tenant
    removed = await asyncio.to_thread(
        store.remove_user_from_tenant, user.id, tenant.id
    )
    assert removed is True
    ok("TenantUserStore.remove_user_from_tenant")

    # Clean up
    await asyncio.to_thread(user.delete_instance)
    await asyncio.to_thread(tenant.delete_instance)
    ok("TenantUserStore cleanup")


# ==================== KnowledgeBaseStore Tests ====================

async def test_knowledge_base_store():
    section("KnowledgeBaseStore")
    store = get_knowledge_base_store()

    # Create tenant for KB
    tenant = await asyncio.to_thread(
        Tenant.create_tenant,
        name="KB Store Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf,docx",
    )

    # Knowledgebase CRUD via store
    kb = await asyncio.to_thread(
        store.create_knowledgebase,
        tenant_id=tenant.id,
        name="Store Test KB",
        created_by="user123",
        description="Testing KB store",
        parser_ids="pdf,docx",
    )
    assert kb.id is not None
    assert kb.name == "Store Test KB"
    ok("KnowledgeBaseStore.create_knowledgebase")

    fetched = await asyncio.to_thread(store.get_knowledgebase, kb.id)
    assert fetched is not None
    assert fetched.id == kb.id
    ok("KnowledgeBaseStore.get_knowledgebase")

    # List knowledgebases
    kbs, total = await asyncio.to_thread(
        store.list_knowledgebases, tenant_id=tenant.id
    )
    assert len(kbs) >= 1
    ok("KnowledgeBaseStore.list_knowledgebases")

    # Update knowledgebase
    updated_kb = await asyncio.to_thread(
        store.update_knowledgebase,
        kb.id,
        description="Updated KB description",
    )
    assert updated_kb is not None
    assert updated_kb.description == "Updated KB description"
    ok("KnowledgeBaseStore.update_knowledgebase")

    # Document operations
    doc = await asyncio.to_thread(
        store.create_document,
        kb_id=kb.id,
        name="test_doc.pdf",
        parser_id="pdf",
        created_by="user123",
    )
    assert doc.id is not None
    assert doc.progress == 0
    ok("KnowledgeBaseStore.create_document")

    fetched_doc = await asyncio.to_thread(store.get_document, doc.id)
    assert fetched_doc is not None
    assert fetched_doc.id == doc.id
    ok("KnowledgeBaseStore.get_document")

    # Update progress
    progress_doc = await asyncio.to_thread(
        store.update_document_progress,
        doc.id,
        progress=50.0,
        progress_msg="Processing...",
    )
    assert progress_doc.progress == 50.0
    ok("KnowledgeBaseStore.update_document_progress")

    # Complete document
    completed_doc = await asyncio.to_thread(
        store.complete_document,
        doc.id,
        duration=123.4,
        doc_metadata={"chunks": 50},
    )
    assert completed_doc.progress == 100.0
    ok("KnowledgeBaseStore.complete_document")

    # List documents
    docs, total = await asyncio.to_thread(
        store.list_documents, kb_id=kb.id
    )
    assert len(docs) >= 1
    ok("KnowledgeBaseStore.list_documents")

    # File operations
    file = await asyncio.to_thread(
        store.create_file,
        name="uploaded_file.pdf",
        size=204800,
        file_type="pdf",
        created_by="user123",
    )
    assert file.id is not None
    ok("KnowledgeBaseStore.create_file")

    fetched_file = await asyncio.to_thread(store.get_file, file.id)
    assert fetched_file is not None
    assert fetched_file.id == file.id
    ok("KnowledgeBaseStore.get_file")

    # Link file to document
    link = await asyncio.to_thread(
        store.link_file_to_document,
        file_id=file.id,
        doc_id=doc.id,
    )
    assert link.id is not None
    ok("KnowledgeBaseStore.link_file_to_document")

    # Get documents for file
    file_docs = await asyncio.to_thread(
        store.get_documents_for_file, file.id
    )
    assert len(file_docs) >= 1
    assert any(d.id == doc.id for d in file_docs)
    ok("KnowledgeBaseStore.get_documents_for_file")

    # Task operations
    task = await asyncio.to_thread(
        store.create_task,
        doc_id=doc.id,
        task_type="ingestion",
        from_page=0,
        to_page=10,
    )
    assert task.id is not None
    assert task.progress == 0
    ok("KnowledgeBaseStore.create_task")

    fetched_task = await asyncio.to_thread(store.get_task, task.id)
    assert fetched_task is not None
    assert fetched_task.id == task.id
    ok("KnowledgeBaseStore.get_task")

    # Start task
    started_task = await asyncio.to_thread(store.start_task, task.id)
    assert started_task.begin_at is not None
    ok("KnowledgeBaseStore.start_task")

    # Update task progress
    prog_task = await asyncio.to_thread(
        store.update_task_progress,
        task.id,
        75.0,
        "Embedding chunks",
    )
    assert prog_task.progress == 75.0
    ok("KnowledgeBaseStore.update_task_progress")

    # Complete task
    completed_task = await asyncio.to_thread(
        store.complete_task, task.id, 45.6
    )
    assert completed_task.progress == 100.0
    ok("KnowledgeBaseStore.complete_task")

    # Get document tasks
    doc_tasks = await asyncio.to_thread(
        store.get_document_tasks, doc.id
    )
    assert len(doc_tasks) >= 1
    ok("KnowledgeBaseStore.get_document_tasks")

    # Clean up (cascade delete KB will delete document, file2doc, tasks)
    await asyncio.to_thread(store.delete_knowledgebase, kb.id)
    ok("KnowledgeBaseStore.delete_knowledgebase")

    # Clean up tenant
    await asyncio.to_thread(tenant.delete_instance)
    ok("KnowledgeBaseStore cleanup")


# ==================== DialogStore Tests ====================

async def test_dialog_store():
    section("DialogStore")
    store = get_dialog_store()

    # Create tenant for dialogs
    tenant = await asyncio.to_thread(
        Tenant.create_tenant,
        name="Dialog Store Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf,docx",
    )

    dialog = await asyncio.to_thread(
        store.create_dialog,
        tenant_id=tenant.id,
        name="Store Test Dialog",
        llm_id="llama3.2:latest",
        created_by="user123",
        description="Testing dialog store",
        top_k=10,
        kb_ids=["kb1"],
    )
    assert dialog.id is not None
    assert dialog.name == "Store Test Dialog"
    ok("DialogStore.create_dialog")

    fetched = await asyncio.to_thread(store.get_dialog, dialog.id)
    assert fetched is not None
    assert fetched.id == dialog.id
    ok("DialogStore.get_dialog")

    # Get by name
    by_name = await asyncio.to_thread(
        store.get_dialog_by_name,
        tenant_id=tenant.id,
        name="Store Test Dialog",
    )
    assert by_name is not None
    assert by_name.id == dialog.id
    ok("DialogStore.get_dialog_by_name")

    # List dialogs
    dialogs, total = await asyncio.to_thread(
        store.list_dialogs, tenant_id=tenant.id
    )
    assert len(dialogs) >= 1
    ok("DialogStore.list_dialogs")

    # Update dialog
    updated = await asyncio.to_thread(
        store.update_dialog,
        dialog.id,
        name="Renamed Store Dialog",
        top_k=20,
    )
    assert updated is not None
    assert updated.name == "Renamed Store Dialog"
    assert updated.top_k == 20
    ok("DialogStore.update_dialog")

    # Delete dialog
    deleted = await asyncio.to_thread(store.delete_dialog, dialog.id)
    assert deleted is True
    ok("DialogStore.delete_dialog")

    # Clean up tenant
    await asyncio.to_thread(tenant.delete_instance)
    ok("DialogStore cleanup")


# ==================== ConversationStore Tests ====================

async def test_conversation_store():
    section("ConversationStore")
    store = get_conversation_store()

    # Create a dialog first
    dialog = await asyncio.to_thread(
        Dialog.create_dialog,
        tenant_id="tenant123",
        name="Conv Store Dialog",
        llm_id="llama3.2:latest",
        created_by="user123",
    )

    conv = await asyncio.to_thread(
        store.create_conversation,
        dialog_id=dialog.id,
        name="Store Test Conversation",
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ],
        user_id="user123",
    )
    assert conv.id is not None
    assert conv.name == "Store Test Conversation"
    assert len(conv.message) == 2
    ok("ConversationStore.create_conversation")

    fetched = await asyncio.to_thread(store.get_conversation, conv.id)
    assert fetched is not None
    assert fetched.id == conv.id
    ok("ConversationStore.get_conversation")

    # List conversations
    convs, total = await asyncio.to_thread(
        store.list_conversations, dialog_id=dialog.id
    )
    assert len(convs) >= 1
    ok("ConversationStore.list_conversations")

    # Append message
    msg = await asyncio.to_thread(
        store.append_message,
        conv.id,
        "user",
        "How are you?",
        token_count=5,
    )
    assert msg["role"] == "user"
    assert msg["content"] == "How are you?"
    ok("ConversationStore.append_message")

    # Get conversation context
    context = await asyncio.to_thread(
        store.get_conversation_context,
        conv.id,
        max_turns=1,
    )
    assert len(context) <= 2
    ok("ConversationStore.get_conversation_context")

    # Update conversation
    updated_conv = await asyncio.to_thread(
        store.update_conversation,
        conv.id,
        name="Renamed Store Conversation",
    )
    assert updated_conv is not None
    assert updated_conv.name == "Renamed Store Conversation"
    ok("ConversationStore.update_conversation")

    # Delete conversation
    deleted = await asyncio.to_thread(
        store.delete_conversation, conv.id
    )
    assert deleted is True
    ok("ConversationStore.delete_conversation")

    # Clean up dialog
    await asyncio.to_thread(dialog.delete_instance)
    ok("ConversationStore cleanup")


# ==================== LLMStore Tests ====================

async def test_llm_store():
    section("LLMStore")
    store = get_llm_store()

    # Factory CRUD via store
    factory = await asyncio.to_thread(
        store.create_factory,
        name="Store Ollama",
        llm_name="llama3.2",
        api_base="http://localhost:11434",
        description="Test factory",
    )
    assert factory.id is not None
    ok("LLMStore.create_factory")

    fetched = await asyncio.to_thread(store.get_factory, factory.id)
    assert fetched is not None
    assert fetched.id == factory.id
    ok("LLMStore.get_factory")

    # List factories
    factories = await asyncio.to_thread(store.list_factories)
    assert len(factories) >= 1
    ok("LLMStore.list_factories")

    # LLM model CRUD
    llm = await asyncio.to_thread(
        store.create_model,
        fid=factory.id,
        llm_name="store-llm",
        model_type="chat",
        max_tokens=4096,
        is_tools=True,
    )
    assert llm.id is not None
    ok("LLMStore.create_model")

    fetched_llm = await asyncio.to_thread(store.get_model, llm.id)
    assert fetched_llm is not None
    assert fetched_llm.id == llm.id
    ok("LLMStore.get_model")

    # List models by factory
    models = await asyncio.to_thread(
        store.list_models, fid=factory.id
    )
    assert len(models) >= 1
    ok("LLMStore.list_models")

    # TenantLLM CRUD
    tenant = await asyncio.to_thread(
        Tenant.create_tenant,
        name="LLM Store Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf,docx",
    )

    tllm = await asyncio.to_thread(
        store.create_tenant_llm,
        tenant_id=tenant.id,
        llm_factory="ollama",
        llm_name="llama3.2",
        model_type="chat",
        api_key="sk-test",
    )
    assert tllm.id is not None
    ok("LLMStore.create_tenant_llm")

    fetched_tllm = await asyncio.to_thread(
        store.get_tenant_llm, tenant.id, "chat"
    )
    assert fetched_tllm is not None
    assert fetched_tllm.id == tllm.id
    ok("LLMStore.get_tenant_llm")

    # List tenant LLMs
    tenant_llms = await asyncio.to_thread(
        store.list_tenant_llms, tenant_id=tenant.id
    )
    assert len(tenant_llms) >= 1
    ok("LLMStore.list_tenant_llms")

    # Clean up
    await asyncio.to_thread(tllm.delete_instance)
    await asyncio.to_thread(llm.delete_instance)
    await asyncio.to_thread(factory.delete_instance)
    await asyncio.to_thread(tenant.delete_instance)
    ok("LLMStore cleanup")


# ==================== ConnectorStore Tests ====================

async def test_connector_store():
    section("ConnectorStore")
    store = get_connector_store()

    connector = await asyncio.to_thread(
        store.create_connector,
        tenant_id="tenant123",
        name="Store Connector",
        source="website",
        input_type="poll",
        config={"url": "https://example.com"},
        refresh_freq=3600,
    )
    assert connector.id is not None
    ok("ConnectorStore.create_connector")

    fetched = await asyncio.to_thread(store.get_connector, connector.id)
    assert fetched is not None
    ok("ConnectorStore.get_connector")

    # List connectors
    connectors = await asyncio.to_thread(
        store.list_connectors, tenant_id="tenant123"
    )
    assert len(connectors) >= 1
    ok("ConnectorStore.list_connectors")

    # Update connector
    updated = await asyncio.to_thread(
        store.update_connector,
        connector.id,
        name="Renamed Connector",
    )
    assert updated is not None
    assert updated.name == "Renamed Connector"
    ok("ConnectorStore.update_connector")

    # Link to KB (need a KB)
    kb = await asyncio.to_thread(
        Knowledgebase.create_kb,
        tenant_id="tenant123",
        name="Connector KB",
        created_by="user123",
    )
    link = await asyncio.to_thread(
        store.link_connector_to_kb,
        connector_id=connector.id,
        kb_id=kb.id,
        auto_parse="1",
    )
    assert link.id is not None
    ok("ConnectorStore.link_connector_to_kb")

    # Get KBs for connector
    kb_list = await asyncio.to_thread(
        store.get_kbs_for_connector, connector.id
    )
    assert len(kb_list) >= 1
    ok("ConnectorStore.get_kbs_for_connector")

    # Create sync log
    sync = await asyncio.to_thread(
        store.create_sync_log,
        connector_id=connector.id,
        status="completed",
        from_beginning="1",
        new_docs_indexed=10,
        total_docs_indexed=100,
        kb_id=kb.id,
    )
    assert sync.id is not None
    ok("ConnectorStore.create_sync_log")

    # Get sync logs for connector
    logs = await asyncio.to_thread(
        store.get_sync_logs_for_connector, connector.id
    )
    assert len(logs) >= 1
    ok("ConnectorStore.get_sync_logs_for_connector")

    # Clean up
    await asyncio.to_thread(sync.delete_instance)
    await asyncio.to_thread(link.delete_instance)
    await asyncio.to_thread(kb.delete_instance)
    await asyncio.to_thread(connector.delete_instance)
    ok("ConnectorStore cleanup")


# ==================== CanvasStore Tests ====================

async def test_canvas_store():
    section("CanvasStore")
    store = get_canvas_store()

    user = await asyncio.to_thread(
        User.create_user,
        email="canvasstore@example.com",
        password=hash_password("pass"),
        username="canvasstore",
    )

    canvas = await asyncio.to_thread(
        store.create_canvas,
        user_id=user.id,
        title="Store Test Canvas",
        permission="private",
        canvas_type="rag",
        dsl={"nodes": [], "edges": []},
    )
    assert canvas.id is not None
    ok("CanvasStore.create_canvas")

    fetched = await asyncio.to_thread(store.get_canvas, canvas.id)
    assert fetched is not None
    ok("CanvasStore.get_canvas")

    # List canvases for user
    canvases = await asyncio.to_thread(
        store.list_canvases, user_id=user.id
    )
    assert len(canvases) >= 1
    ok("CanvasStore.list_canvases")

    # Update canvas
    updated = await asyncio.to_thread(
        store.update_canvas,
        canvas.id,
        title="Updated Store Canvas",
    )
    assert updated is not None
    assert updated.title == "Updated Store Canvas"
    ok("CanvasStore.update_canvas")

    # Template tests
    template = await asyncio.to_thread(
        store.create_template,
        title={"en": "Store Template"},
        description={"en": "A store template"},
        canvas_type="rag",
        dsl={"nodes": [{"id": "1"}], "edges": []},
    )
    assert template.id is not None
    ok("CanvasStore.create_template")

    fetched_template = await asyncio.to_thread(
        store.get_template, template.id
    )
    assert fetched_template is not None
    ok("CanvasStore.get_template")

    # List templates
    templates = await asyncio.to_thread(store.list_templates)
    assert len(templates) >= 1
    ok("CanvasStore.list_templates")

    # Clean up
    await asyncio.to_thread(canvas.delete_instance)
    await asyncio.to_thread(template.delete_instance)
    await asyncio.to_thread(user.delete_instance)
    ok("CanvasStore cleanup")


# ==================== EvaluationStore Tests ====================

async def test_evaluation_store():
    section("EvaluationStore")
    store = get_evaluation_store()

    # Create dataset
    ds = await asyncio.to_thread(
        store.create_dataset,
        tenant_id="tenant123",
        name="Store Eval Dataset",
        description="Store testing",
        kb_ids=["kb1"],
        created_by="user123",
    )
    assert ds.id is not None
    ok("EvaluationStore.create_dataset")

    fetched = await asyncio.to_thread(store.get_dataset, ds.id)
    assert fetched is not None
    ok("EvaluationStore.get_dataset")

    # List datasets
    datasets = await asyncio.to_thread(
        store.list_datasets, tenant_id="tenant123"
    )
    assert len(datasets) >= 1
    ok("EvaluationStore.list_datasets")

    # Add case
    case = await asyncio.to_thread(
        store.create_case,
        dataset_id=ds.id,
        question="What is RAG?",
        reference_answer="Retrieval-Augmented Generation",
    )
    assert case.id is not None
    ok("EvaluationStore.create_case")

    # List cases
    cases = await asyncio.to_thread(
        store.list_cases, dataset_id=ds.id
    )
    assert len(cases) >= 1
    ok("EvaluationStore.list_cases")

    # Create run
    run = await asyncio.to_thread(
        store.create_run,
        dataset_id=ds.id,
        dialog_id="dialog123",
        name="Store Test Run",
        created_by="user123",
        config_snapshot={"model": "llama3.2"},
    )
    assert run.id is not None
    ok("EvaluationStore.create_run")

    fetched_run = await asyncio.to_thread(store.get_run, run.id)
    assert fetched_run is not None
    ok("EvaluationStore.get_run")

    # Add result
    result = await asyncio.to_thread(
        store.create_result,
        run_id=run.id,
        case_id=case.id,
        generated_answer="RAG is...",
        retrieved_chunks=[{"chunk_id": "1", "text": "..."}],
        metrics={"ndcg": 0.85},
        execution_time=1.23,
    )
    assert result.id is not None
    ok("EvaluationStore.create_result")

    # List results for run
    results = await asyncio.to_thread(
        store.list_results, run_id=run.id
    )
    assert len(results) >= 1
    ok("EvaluationStore.list_results")

    # Clean up
    await asyncio.to_thread(result.delete_instance)
    await asyncio.to_thread(run.delete_instance)
    await asyncio.to_thread(case.delete_instance)
    await asyncio.to_thread(ds.delete_instance)
    ok("EvaluationStore cleanup")


# ==================== SystemStore Tests ====================

async def test_system_store():
    section("SystemStore")
    store = get_system_store()

    # SystemSettings
    setting = await asyncio.to_thread(
        store.set_setting,
        name="store.test",
        source="system",
        data_type="string",
        value="test_value",
    )
    assert setting.name == "store.test"
    ok("SystemStore.set_setting")

    val = await asyncio.to_thread(store.get_setting, "store.test")
    assert val == "test_value"
    ok("SystemStore.get_setting")

    # APIToken
    token = await asyncio.to_thread(
        store.create_api_token,
        tenant_id="tenant123",
        dialog_id="dialog456",
        source="web",
        token="hashed_token_store",
        beta=False,
    )
    assert token.tenant_id == "tenant123"
    ok("SystemStore.create_api_token")

    # Verify token
    verified = await asyncio.to_thread(
        store.verify_api_token, "hashed_token_store"
    )
    assert verified is not None
    ok("SystemStore.verify_api_token")

    # MCP
    mcp = await asyncio.to_thread(
        store.create_mcp,
        tenant_id="tenant123",
        name="Store MCP",
        url="http://localhost:8080",
        server_type="stdio",
        description="MCP for store test",
        variables={"API_KEY": "secret"},
    )
    assert mcp.id is not None
    ok("SystemStore.create_mcp")

    # PipelineOperationLog
    kb = await asyncio.to_thread(
        Knowledgebase.create_kb,
        tenant_id="tenant123",
        name="Store Log KB",
        created_by="user123",
    )
    doc = await asyncio.to_thread(
        Document.create_document,
        kb_id=kb.id,
        name="log_test.pdf",
        parser_id="pdf",
        created_by="user123",
    )
    log = await asyncio.to_thread(
        store.create_pipeline_log,
        document_id=doc.id,
        tenant_id="tenant123",
        kb_id=kb.id,
        parser_id="pdf",
        document_name="log_test.pdf",
        document_suffix=".pdf",
        document_type="pdf",
        source_from="upload",
        operation_status="completed",
    )
    assert log.id is not None
    ok("SystemStore.create_pipeline_log")

    # Clean up
    await asyncio.to_thread(log.delete_instance)
    await asyncio.to_thread(doc.delete_instance)
    await asyncio.to_thread(kb.delete_instance)
    await asyncio.to_thread(mcp.delete_instance)
    await asyncio.to_thread(token.delete_instance)
    await asyncio.to_thread(setting.delete_instance)
    ok("SystemStore cleanup")


# ==================== Main ====================

async def run_all_tests():
    print("=" * 60)
    print("  Store Services Comprehensive Test Suite")
    print("=" * 60)

    await test_db.setup()
    try:
        await test_tenant_user_store()
        await test_knowledge_base_store()
        await test_dialog_store()
        await test_conversation_store()
        await test_llm_store()
        await test_connector_store()
        await test_canvas_store()
        await test_evaluation_store()
        await test_system_store()

        section("ALL STORE TESTS PASSED")
        print("\n✅ All store services tested successfully!\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        raise
    finally:
        await test_db.teardown()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
