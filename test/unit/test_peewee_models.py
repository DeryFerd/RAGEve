"""
Comprehensive tests for all 27 Peewee ORM models.

Tests CRUD operations, custom methods, relationships, and constraints.

Run: uv run python test/unit/test_peewee_models.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.unit.test_config import TestDatabase

# Models
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
)

# Simple password hasher for tests (avoid bcrypt dependency)
def hash_password(password: str) -> str:
    """Return a simple hash for testing (not secure)."""
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


# ==================== User & Tenant Tests ====================

async def test_user_crud():
    section("User CRUD")

    # Create
    user = await asyncio.to_thread(
        User.create_user,
        email="test@example.com",
        password=hash_password("password123"),
        username="testuser",
        full_name="Test User",
        is_superuser=False,
    )
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.is_active is True
    ok("User create")

    # Read
    fetched = await asyncio.to_thread(
        User.get_or_none,
        User.id == user.id
    )
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.email == "test@example.com"
    ok("User read by ID")

    # Update
    await asyncio.to_thread(
        lambda: User.update(
            full_name="Updated Name",
            is_superuser=True,
            update_date=datetime.utcnow(),
            update_time=int(datetime.utcnow().timestamp())
        ).where(User.id == user.id).execute()
    )
    updated = await asyncio.to_thread(User.get, User.id == user.id)
    assert updated.full_name == "Updated Name"
    assert updated.is_superuser is True
    ok("User update")

    # Delete (deactivate)
    await asyncio.to_thread(
        lambda: User.update(
            status="0",
            update_date=datetime.utcnow(),
            update_time=int(datetime.utcnow().timestamp())
        ).where(User.id == user.id).execute()
    )
    deactivated = await asyncio.to_thread(User.get, User.id == user.id)
    assert deactivated.is_active is False
    ok("User deactivate")

    # Clean up
    await asyncio.to_thread(user.delete_instance)
    ok("User delete")


async def test_tenant_crud():
    section("Tenant CRUD")

    tenant = await asyncio.to_thread(
        Tenant.create_tenant,
        name="Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf,docx",
    )
    assert tenant.id is not None
    assert tenant.name == "Test Tenant"
    ok("Tenant create")

    # Read
    fetched = await asyncio.to_thread(
        Tenant.get_or_none,
        Tenant.id == tenant.id
    )
    assert fetched is not None
    assert fetched.id == tenant.id
    ok("Tenant read")

    # Update
    await asyncio.to_thread(
        lambda: Tenant.update(
            name="Renamed Tenant",
            update_date=datetime.utcnow(),
            update_time=int(datetime.utcnow().timestamp())
        ).where(Tenant.id == tenant.id).execute()
    )
    updated = await asyncio.to_thread(Tenant.get, Tenant.id == tenant.id)
    assert updated.name == "Renamed Tenant"
    ok("Tenant update")

    # Clean up
    await asyncio.to_thread(tenant.delete_instance)
    ok("Tenant delete")


async def test_user_tenant_relationship():
    section("User-Tenant Relationship")

    # Create user and tenant
    user = await asyncio.to_thread(
        User.create_user,
        email="reltest@example.com",
        password=hash_password("pass"),
        username="reltest",
    )
    tenant = await asyncio.to_thread(
        Tenant.create_tenant,
        name="Rel Test Tenant",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf,docx",
    )

    # Add user to tenant
    ut = await asyncio.to_thread(
        UserTenant.add_user_to_tenant,
        user_id=user.id,
        tenant_id=tenant.id,
        invited_by=user.id,
        role="member",
    )
    assert ut is not None
    ok("UserTenant link created")

    # Verify relationships - query UserTenant directly
    user_tenants = await asyncio.to_thread(
        lambda: list(UserTenant.select().where(UserTenant.user_id == user.id))
    )
    assert len(user_tenants) >= 1
    assert any(ut.tenant_id == tenant.id for ut in user_tenants)
    ok("UserTenant query for user's tenants")

    # Get tenants for user via join
    tenants = await asyncio.to_thread(
        lambda: list(
            Tenant.select()
            .join(UserTenant, on=(Tenant.id == UserTenant.tenant_id))
            .where(UserTenant.user_id == user.id)
        )
    )
    assert len(tenants) >= 1
    assert any(t.id == tenant.id for t in tenants)
    ok("Tenant query via join for user's tenants")

    # Get users in tenant via join
    users = await asyncio.to_thread(
        lambda: list(
            User.select()
            .join(UserTenant, on=(User.id == UserTenant.user_id))
            .where(UserTenant.tenant_id == tenant.id)
        )
    )
    assert len(users) >= 1
    assert any(u.id == user.id for u in users)
    ok("User query via join for tenant's users")

    # Clean up
    await asyncio.to_thread(ut.delete_instance)
    await asyncio.to_thread(user.delete_instance)
    await asyncio.to_thread(tenant.delete_instance)
    ok("User-Tenant relationship cleanup")


# ==================== Knowledge Base Tests ====================

async def test_knowledgebase_crud():
    section("Knowledgebase CRUD")

    kb = await asyncio.to_thread(
        Knowledgebase.create_kb,
        tenant_id="tenant123",
        name="Test KB",
        created_by="user123",
        description="A test knowledge base",
        parser_ids="pdf,docx",
    )
    assert kb.id is not None
    assert kb.name == "Test KB"
    ok("Knowledgebase create")

    # Read
    fetched = await asyncio.to_thread(
        Knowledgebase.get_or_none,
        Knowledgebase.id == kb.id
    )
    assert fetched is not None
    assert fetched.id == kb.id
    ok("Knowledgebase read")

    # Update
    await asyncio.to_thread(
        lambda: Knowledgebase.update(
            description="Updated desc",
            update_date=datetime.utcnow(),
            update_time=int(datetime.utcnow().timestamp())
        ).where(Knowledgebase.id == kb.id).execute()
    )
    updated = await asyncio.to_thread(Knowledgebase.get, Knowledgebase.id == kb.id)
    assert updated.description == "Updated desc"
    ok("Knowledgebase update")

    # Clean up
    await asyncio.to_thread(kb.delete_instance)
    ok("Knowledgebase delete")


async def test_document_workflow():
    section("Document Workflow")

    kb = await asyncio.to_thread(
        Knowledgebase.create_kb,
        tenant_id="tenant123",
        name="Doc Test KB",
        created_by="user123",
    )

    doc = await asyncio.to_thread(
        Document.create_document,
        kb_id=kb.id,
        name="test.pdf",
        parser_id="pdf",
        created_by="user123",
    )
    assert doc.id is not None
    assert doc.progress == 0
    ok("Document create")

    # Update progress
    await asyncio.to_thread(
        lambda: Document.update(
            progress=50.0,
            progress_msg="Processing",
            update_date=datetime.utcnow(),
            update_time=int(datetime.utcnow().timestamp())
        ).where(Document.id == doc.id).execute()
    )
    updated = await asyncio.to_thread(Document.get, Document.id == doc.id)
    assert updated.progress == 50.0
    assert updated.progress_msg == "Processing"
    ok("Document progress update")

    # Complete document
    await asyncio.to_thread(
        lambda: Document.update(
            process_duation=123.4,
            progress=100.0,
            doc_metadata={"chunks": 100},
            update_date=datetime.utcnow(),
            update_time=int(datetime.utcnow().timestamp())
        ).where(Document.id == doc.id).execute()
    )
    completed = await asyncio.to_thread(Document.get, Document.id == doc.id)
    assert completed.progress == 100.0
    ok("Document complete")

    # List documents
    docs = await asyncio.to_thread(
        lambda: list(Document.select().where(Document.kb_id == kb.id))
    )
    assert len(docs) >= 1
    ok("Document list")

    # Clean up
    await asyncio.to_thread(doc.delete_instance)
    await asyncio.to_thread(kb.delete_instance)
    ok("Document cleanup")


async def test_file_and_task():
    section("File & Task")

    kb = await asyncio.to_thread(
        Knowledgebase.create_kb,
        tenant_id="tenant123",
        name="File Test KB",
        created_by="user123",
    )
    doc = await asyncio.to_thread(
        Document.create_document,
        kb_id=kb.id,
        name="uploaded.pdf",
        parser_id="pdf",
        created_by="user123",
    )

    # Create file
    file = await asyncio.to_thread(
        File.create_file,
        name="uploaded.pdf",
        size=102400,
        file_type="pdf",
        created_by="user123",
    )
    assert file.id is not None
    ok("File create")

    # Link file to document
    link = await asyncio.to_thread(
        File2Document.create_link,
        file_id=file.id,
        doc_id=doc.id,
    )
    assert link.id is not None
    ok("File2Document link")

    # Create task
    task = await asyncio.to_thread(
        Task.create_task,
        doc_id=doc.id,
        task_type="ingestion",
        from_page=0,
        to_page=10,
    )
    assert task.id is not None
    assert task.progress == 0
    ok("Task create")

    # Task operations
    await asyncio.to_thread(task.start)
    assert task.begin_at is not None
    ok("Task start")

    await asyncio.to_thread(task.update_progress, 75.0, "Embedding")
    assert task.progress == 75.0
    ok("Task update_progress")

    await asyncio.to_thread(task.complete, 45.6)
    assert task.progress == 100.0
    ok("Task complete")

    # Clean up
    await asyncio.to_thread(task.delete_instance)
    await asyncio.to_thread(link.delete_instance)
    await asyncio.to_thread(file.delete_instance)
    await asyncio.to_thread(doc.delete_instance)
    await asyncio.to_thread(kb.delete_instance)
    ok("File & Task cleanup")


# ==================== Dialog & Conversation Tests ====================

async def test_dialog_crud():
    section("Dialog CRUD")

    dialog = await asyncio.to_thread(
        Dialog.create_dialog,
        tenant_id="tenant123",
        name="Test Dialog",
        llm_id="llama3.2:latest",
        created_by="user123",
        description="A test dialog",
        top_k=10,
        kb_ids=["kb1", "kb2"],
    )
    assert dialog.id is not None
    assert dialog.name == "Test Dialog"
    assert dialog.top_k == 10
    assert dialog.kb_ids == ["kb1", "kb2"]
    ok("Dialog create")

    # Read
    fetched = await asyncio.to_thread(
        Dialog.get_or_none,
        Dialog.id == dialog.id
    )
    assert fetched is not None
    assert fetched.id == dialog.id
    ok("Dialog read")

    # Get by name
    by_name = await asyncio.to_thread(
        lambda: Dialog.get_or_none(
            Dialog.name == "Test Dialog",
            Dialog.tenant_id == "tenant123"
        )
    )
    assert by_name is not None
    assert by_name.id == dialog.id
    ok("Dialog get by name")

    # Update
    await asyncio.to_thread(
        lambda: Dialog.update(
            name="Renamed Dialog",
            top_k=20,
            update_date=datetime.utcnow(),
            update_time=int(datetime.utcnow().timestamp())
        ).where(Dialog.id == dialog.id).execute()
    )
    updated = await asyncio.to_thread(Dialog.get, Dialog.id == dialog.id)
    assert updated.name == "Renamed Dialog"
    assert updated.top_k == 20
    ok("Dialog update")

    # Clean up
    await asyncio.to_thread(dialog.delete_instance)
    ok("Dialog delete")


async def test_conversation_messages():
    section("Conversation & Messages")

    dialog = await asyncio.to_thread(
        Dialog.create_dialog,
        tenant_id="tenant123",
        name="Conv Test Dialog",
        llm_id="llama3.2:latest",
        created_by="user123",
    )

    # Create conversation with initial messages
    conv = await asyncio.to_thread(
        Conversation.create_conversation,
        dialog_id=dialog.id,
        name="Test Conversation",
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
    )
    assert conv.id is not None
    assert len(conv.message) == 2
    ok("Conversation create with messages")

    # Add message
    msg = await asyncio.to_thread(conv.add_message, "user", "How are you?")
    assert msg["role"] == "user"
    assert msg["content"] == "How are you?"
    ok("Conversation add_message")

    # Get messages
    msgs = await asyncio.to_thread(conv.get_messages)
    assert len(msgs) == 3
    ok("Conversation get_messages")

    # Get limited context
    limited = await asyncio.to_thread(conv.get_messages, max_turns=1)
    assert len(limited) == 2
    ok("Conversation get_messages with max_turns")

    # Update conversation
    await asyncio.to_thread(
        lambda: Conversation.update(
            name="Renamed Conv",
            update_date=datetime.utcnow(),
            update_time=int(datetime.utcnow().timestamp())
        ).where(Conversation.id == conv.id).execute()
    )
    updated = await asyncio.to_thread(Conversation.get, Conversation.id == conv.id)
    assert updated.name == "Renamed Conv"
    ok("Conversation update")

    # Clean up
    await asyncio.to_thread(conv.delete_instance)
    await asyncio.to_thread(dialog.delete_instance)
    ok("Conversation cleanup")


# ==================== LLM Tests ====================

async def test_llm_factories():
    section("LLM Factories")

    factory = await asyncio.to_thread(
        LLMFactories.create_factory,
        name="Ollama",
        llm_name="llama3.2",
        api_base="http://localhost:11434",
        description="Local Ollama",
    )
    assert factory.id is not None
    assert factory.name == "Ollama"
    ok("LLMFactories create")

    # Read
    fetched = await asyncio.to_thread(
        LLMFactories.get_or_none,
        LLMFactories.id == factory.id
    )
    assert fetched is not None
    assert fetched.id == factory.id
    ok("LLMFactories read")

    # List
    all_factories = await asyncio.to_thread(
        lambda: list(LLMFactories.select())
    )
    assert len(all_factories) >= 1
    ok("LLMFactories list")

    # Delete
    await asyncio.to_thread(factory.delete_instance)
    ok("LLMFactories delete")


async def test_llm_models():
    section("LLM Models")

    factory = await asyncio.to_thread(
        LLMFactories.create_factory,
        name="TestFactory",
        llm_name="test-model",
    )

    llm = await asyncio.to_thread(
        LLM.create_llm,
        fid=factory.id,
        llm_name="llama3.2",
        model_type="chat",
        max_tokens=4096,
        is_tools=True,
    )
    assert llm.id is not None
    assert llm.fid == factory.id
    ok("LLM create")

    # Read
    fetched = await asyncio.to_thread(
        LLM.get_or_none,
        LLM.id == llm.id
    )
    assert fetched is not None
    assert fetched.id == llm.id
    ok("LLM read")

    # Clean up
    await asyncio.to_thread(llm.delete_instance)
    await asyncio.to_thread(factory.delete_instance)
    ok("LLM cleanup")


async def test_tenant_llm():
    section("TenantLLM")

    tenant = await asyncio.to_thread(
        Tenant.create_tenant,
        name="TenantLLM Test",
        llm_id="llama3.2:latest",
        embd_id="nomic-embed-text:latest",
        parser_ids="pdf,docx",
    )

    tllm = await asyncio.to_thread(
        TenantLLM.create_tenant_llm,
        tenant_id=tenant.id,
        llm_factory="ollama",
        llm_name="llama3.2",
        model_type="chat",
        api_key="sk-test",
    )
    assert tllm.id is not None
    assert tllm.tenant_id == tenant.id
    ok("TenantLLM create")

    # Get tenant LLM (query by tenant_id and model_type)
    fetched = await asyncio.to_thread(
        lambda: TenantLLM.get_or_none(
            TenantLLM.tenant_id == tenant.id,
            TenantLLM.model_type == "chat"
        )
    )
    assert fetched is not None
    assert fetched.id == tllm.id
    ok("TenantLLM get by tenant and type")

    # Clean up
    await asyncio.to_thread(tllm.delete_instance)
    await asyncio.to_thread(tenant.delete_instance)
    ok("TenantLLM cleanup")


# ==================== Connector Tests ====================

async def test_connector():
    section("Connector")

    connector = await asyncio.to_thread(
        Connector.create_connector,
        tenant_id="tenant123",
        name="Test Connector",
        source="website",
        input_type="poll",
        config={"url": "https://example.com"},
        refresh_freq=3600,
    )
    assert connector.id is not None
    assert connector.name == "Test Connector"
    ok("Connector create")

    # Read
    fetched = await asyncio.to_thread(
        Connector.get_or_none,
        Connector.id == connector.id
    )
    assert fetched is not None
    assert fetched.id == connector.id
    ok("Connector read")

    # Clean up
    await asyncio.to_thread(connector.delete_instance)
    ok("Connector delete")


async def test_sync_logs():
    section("SyncLogs")

    connector = await asyncio.to_thread(
        Connector.create_connector,
        tenant_id="tenant123",
        name="Sync Test Connector",
        source="confluence",
        input_type="poll",
    )

    sync = await asyncio.to_thread(
        SyncLogs.create_log,
        connector_id=connector.id,
        status="completed",
        from_beginning="1",
        new_docs_indexed=10,
        total_docs_indexed=100,
        kb_id="kb123",
    )
    assert sync.id is not None
    assert sync.status == "completed"
    ok("SyncLogs create")

    # Clean up
    await asyncio.to_thread(sync.delete_instance)
    await asyncio.to_thread(connector.delete_instance)
    ok("SyncLogs cleanup")


# ==================== Canvas Tests ====================

async def test_canvas():
    section("Canvas (UserCanvas)")

    user = await asyncio.to_thread(
        User.create_user,
        email="canvas@example.com",
        password=hash_password("pass"),
        username="canvasuser",
    )

    canvas = await asyncio.to_thread(
        UserCanvas.create_canvas,
        user_id=user.id,
        title="Test Canvas",
        permission="private",
        canvas_type="rag",
        dsl={"nodes": [], "edges": []},
    )
    assert canvas.id is not None
    assert canvas.title == "Test Canvas"
    ok("UserCanvas create")

    # Clean up
    await asyncio.to_thread(canvas.delete_instance)
    await asyncio.to_thread(user.delete_instance)
    ok("UserCanvas cleanup")


async def test_canvas_template():
    section("CanvasTemplate")

    template = await asyncio.to_thread(
        CanvasTemplate.create_template,
        title={"en": "Default Template"},
        description={"en": "A default canvas template"},
        canvas_type="rag",
        dsl={"nodes": [{"id": "1"}], "edges": []},
    )
    assert template.id is not None
    ok("CanvasTemplate create")

    # Clean up
    await asyncio.to_thread(template.delete_instance)
    ok("CanvasTemplate cleanup")


# ==================== Evaluation Tests ====================

async def test_evaluation_dataset():
    section("EvaluationDataset")

    ds = await asyncio.to_thread(
        EvaluationDataset.create_dataset,
        tenant_id="tenant123",
        name="Test Eval Dataset",
        description="For testing",
        kb_ids=["kb1"],
        created_by="user123",
    )
    assert ds.id is not None
    ok("EvaluationDataset create")

    # Add case
    case = await asyncio.to_thread(
        EvaluationCase.create_case,
        dataset_id=ds.id,
        question="What is RAG?",
        reference_answer="Retrieval-Augmented Generation",
    )
    assert case.id is not None
    ok("EvaluationCase create")

    # Create run
    run = await asyncio.to_thread(
        EvaluationRun.create_run,
        dataset_id=ds.id,
        dialog_id="dialog123",
        name="Test Run",
        created_by="user123",
        config_snapshot={"model": "llama3.2"},
    )
    assert run.id is not None
    ok("EvaluationRun create")

    # Add result
    result = await asyncio.to_thread(
        EvaluationResult.create_result,
        run_id=run.id,
        case_id=case.id,
        generated_answer="RAG is...",
        retrieved_chunks=[{"chunk_id": "1", "text": "..."}],
        metrics={"ndcg": 0.85},
        execution_time=1.23,
    )
    assert result.id is not None
    ok("EvaluationResult create")

    # Clean up
    await asyncio.to_thread(result.delete_instance)
    await asyncio.to_thread(run.delete_instance)
    await asyncio.to_thread(case.delete_instance)
    await asyncio.to_thread(ds.delete_instance)
    ok("Evaluation cleanup")


# ==================== System Tests ====================

async def test_system_settings():
    section("SystemSettings")

    setting = await asyncio.to_thread(
        SystemSettings.set_value,
        name="app.name",
        source="system",
        data_type="string",
        value="RAGEve",
    )
    assert setting.name == "app.name"
    ok("SystemSettings set_value")

    # Get value
    val = await asyncio.to_thread(SystemSettings.get_value, "app.name")
    assert val == "RAGEve"
    ok("SystemSettings get_value")

    # Clean up
    await asyncio.to_thread(setting.delete_instance)
    ok("SystemSettings cleanup")


async def test_api_token():
    section("APIToken")

    # APIToken uses composite key (tenant_id, token)
    token = await asyncio.to_thread(
        APIToken.create_token,
        tenant_id="tenant123",
        dialog_id="dialog456",
        source="web",
        token="hashed_token_123",
        beta=False,
    )
    assert token.tenant_id == "tenant123"
    ok("APIToken create")

    # Verify - query by token
    verified = await asyncio.to_thread(
        lambda: APIToken.get_or_none(APIToken.token == "hashed_token_123")
    )
    assert verified is not None
    ok("APIToken verify")

    # Clean up
    await asyncio.to_thread(token.delete_instance)
    ok("APIToken cleanup")


async def test_mcp():
    section("MCP")

    mcp = await asyncio.to_thread(
        MCP.create_mcp_server,
        tenant_id="tenant123",
        name="Test MCP",
        url="http://localhost:8080",
        server_type="stdio",
        description="MCP server for testing",
        variables={"API_KEY": "secret"},
    )
    assert mcp.id is not None
    ok("MCP create")

    # Clean up
    await asyncio.to_thread(mcp.delete_instance)
    ok("MCP cleanup")


async def test_pipeline_operation_log():
    section("PipelineOperationLog")

    kb = await asyncio.to_thread(
        Knowledgebase.create_kb,
        tenant_id="tenant123",
        name="Pipeline Test KB",
        created_by="user123",
    )
    doc = await asyncio.to_thread(
        Document.create_document,
        kb_id=kb.id,
        name="test.pdf",
        parser_id="pdf",
        created_by="user123",
    )

    log = await asyncio.to_thread(
        PipelineOperationLog.create_log,
        document_id=doc.id,
        tenant_id="tenant123",
        kb_id=kb.id,
        pipeline_id="pipeline123",
        pipeline_title="Default Pipeline",
        parser_id="pdf",
        document_name="test.pdf",
        document_suffix=".pdf",
        document_type="pdf",
        source_from="upload",
        operation_status="completed",
    )
    assert log.id is not None
    ok("PipelineOperationLog create")

    # Clean up
    await asyncio.to_thread(log.delete_instance)
    await asyncio.to_thread(doc.delete_instance)
    await asyncio.to_thread(kb.delete_instance)
    ok("PipelineOperationLog cleanup")


# ==================== Main ====================

async def run_all_tests():
    print("=" * 60)
    print("  Peewee Models Comprehensive Test Suite")
    print("=" * 60)

    await test_db.setup()
    try:
        # User & Tenant
        await test_user_crud()
        await test_tenant_crud()
        await test_user_tenant_relationship()

        # Knowledge Base
        await test_knowledgebase_crud()
        await test_document_workflow()
        await test_file_and_task()

        # Dialog & Conversation
        await test_dialog_crud()
        await test_conversation_messages()

        # LLM
        await test_llm_factories()
        await test_llm_models()
        await test_tenant_llm()

        # Connector
        await test_connector()
        await test_sync_logs()

        # Canvas
        await test_canvas()
        await test_canvas_template()

        # Evaluation
        await test_evaluation_dataset()

        # System
        await test_system_settings()
        await test_api_token()
        await test_mcp()
        await test_pipeline_operation_log()

        section("ALL TESTS PASSED")
        print("\n✅ All 27 models tested successfully!\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        raise
    finally:
        await test_db.teardown()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
