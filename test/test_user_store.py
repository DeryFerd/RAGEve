"""
Unit tests for backend.services.tenant_user_store.TenantUserStore.

Uses an in-memory SQLite database for isolation.
Run: uv run python test/test_user_store.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is in path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from datetime import datetime, timezone
import peewee
from peewee import SqliteDatabase

from backend.config import settings
from backend.models_peewee import (
    User, Tenant, UserTenant, Knowledgebase, Document, File, File2Document, Task,
    Dialog, Conversation, LLMFactories, LLM, TenantLLM, Connector, Connector2Kb,
    SyncLogs, UserCanvas, CanvasTemplate, EvaluationDataset, EvaluationCase,
    EvaluationRun, EvaluationResult, SystemSettings, APIToken, API4Conversation,
    MCP, Search, PipelineOperationLog,
)
import backend.models_peewee as mp
from backend.services.auth import hash_password, verify_password
from backend.services.tenant_user_store import get_tenant_user_store
from backend.services.database import run_db_operation, _executor


# Global test database reference
_test_db: SqliteDatabase = None


async def setup_test_db():
    """Initialize a file-based SQLite database for testing."""
    global _test_db
    _test_db = peewee.SqliteDatabase("./test_user_store.db")

    # List of all models to bind
    models = [
        User, Tenant, UserTenant, Knowledgebase, Document, File, File2Document, Task,
        Dialog, Conversation, LLMFactories, LLM, TenantLLM, Connector, Connector2Kb,
        SyncLogs, UserCanvas, CanvasTemplate, EvaluationDataset, EvaluationCase,
        EvaluationRun, EvaluationResult, SystemSettings, APIToken, API4Conversation,
        MCP, Search, PipelineOperationLog,
    ]

    # Bind models to test database
    for model in models:
        model._meta.database = _test_db

    # Create tables
    _test_db.create_tables(models, safe=True)

    # Override the global database singleton to use our test DB
    mp._database = _test_db

    # Reset store singletons
    # (get_tenant_user_store uses a module-level singleton)
    import backend.services.tenant_user_store as tus
    tus._tenant_user_store = None

    print("Test database initialized (SQLite in-memory).")


async def teardown_test_db():
    """Clean up test database."""
    global _test_db
    if _test_db:
        await asyncio.get_event_loop().run_in_executor(_executor, _test_db.close)
        _test_db = None
    try:
        import os
        if os.path.exists("./test_user_store.db"):
            os.remove("./test_user_store.db")
    except Exception:
        pass
    print("Test database closed and cleaned.")


async def test_create_user():
    email = "alice@example.com"
    username = "alice"
    password = "secure_password_123"
    hashed = hash_password(password)

    store = get_tenant_user_store()
    user = await run_db_operation(
        store.create_user,
        email=email,
        password=hashed,
        username=username,
        full_name="Alice",
        is_superuser=False,
    )

    assert user.email == email
    assert user.username == username
    assert user.full_name == "Alice"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.id is not None
    print("✓ create_user works")


async def test_get_user_by_email():
    email = "bob@example.com"
    username = "bob"
    hashed = hash_password("password")
    store = get_tenant_user_store()
    created = await run_db_operation(
        store.create_user,
        email=email,
        password=hashed,
        username=username,
    )

    fetched = await run_db_operation(store.get_user_by_email, email)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.username == username
    assert verify_password("password", fetched.password)

    # Not found
    assert await run_db_operation(store.get_user_by_email, "unknown@example.com") is None
    print("✓ get_user_by_email works")


async def test_get_user_by_username():
    username = "charlie"
    hashed = hash_password("pass")
    store = get_tenant_user_store()
    user = await run_db_operation(
        store.create_user,
        email="c@example.com",
        password=hashed,
        username=username,
    )

    fetched = await run_db_operation(store.get_user_by_username, username)
    assert fetched is not None
    assert fetched.id == user.id

    assert await run_db_operation(store.get_user_by_username, "nonexistent") is None
    print("✓ get_user_by_username works")


async def test_get_user_by_id():
    hashed = hash_password("pass")
    store = get_tenant_user_store()
    user = await run_db_operation(
        store.create_user,
        email="d@example.com",
        password=hashed,
        username="dave",
    )

    fetched = await run_db_operation(store.get_user_by_id, user.id)
    assert fetched is not None
    assert fetched.id == user.id

    assert await run_db_operation(store.get_user_by_id, "fake-id") is None
    print("✓ get_user_by_id works")


async def test_duplicate_email_and_username():
    email = "e@example.com"
    username = "eve"
    hashed = hash_password("pass")
    store = get_tenant_user_store()
    await run_db_operation(
        store.create_user,
        email=email,
        password=hashed,
        username=username,
    )

    # Duplicate email
    try:
        await run_db_operation(
            store.create_user,
            email=email,
            password=hash_password("other"),
            username="other_user",
        )
        assert False, "Expected IntegrityError for duplicate email"
    except peewee.IntegrityError:
        pass  # expected

    # Duplicate username
    try:
        await run_db_operation(
            store.create_user,
            email="f@example.com",
            password=hash_password("other"),
            username=username,
        )
        assert False, "Expected IntegrityError for duplicate username"
    except peewee.IntegrityError:
        pass  # expected

    print("✓ duplicate email/username raises IntegrityError")


async def test_update_user():
    hashed = hash_password("pass")
    store = get_tenant_user_store()
    user = await run_db_operation(
        store.create_user,
        email="g@example.com",
        password=hashed,
        username="gina",
    )

    # Update full_name and is_superuser
    updated = await run_db_operation(
        store.update_user,
        user.id,
        full_name="Gina Full",
        is_superuser=True,
    )
    assert updated is not None
    assert updated.full_name == "Gina Full"
    assert updated.is_superuser is True

    # Update non-existent user returns None
    result = await run_db_operation(store.update_user, "fake-id", full_name="No One")
    assert result is None
    print("✓ update_user works")


async def test_verify_email():
    hashed = hash_password("pass")
    store = get_tenant_user_store()
    user = await run_db_operation(
        store.create_user,
        email="h@example.com",
        password=hashed,
        username="henry",
        email_verified=False,
        verification_token="token123",
        verification_token_expires=datetime.now(timezone.utc),
    )

    # Initially not verified
    fresh = await run_db_operation(store.get_user_by_id, user.id)
    assert fresh.email_verified is False
    assert fresh.verification_token == "token123"

    # Verify
    await run_db_operation(store.verify_email, user.id)
    verified = await run_db_operation(store.get_user_by_id, user.id)
    assert verified.email_verified is True
    assert verified.verification_token is None
    assert verified.verification_token_expires is None
    print("✓ verify_email works")


async def test_change_password():
    hashed = hash_password("oldpass")
    store = get_tenant_user_store()
    user = await run_db_operation(
        store.create_user,
        email="i@example.com",
        password=hashed,
        username="ivy",
    )

    new_hashed = hash_password("newpass")
    await run_db_operation(store.change_password, user.id, new_hashed)

    fresh = await run_db_operation(store.get_user_by_id, user.id)
    assert verify_password("newpass", fresh.password)
    assert not verify_password("oldpass", fresh.password)
    print("✓ change_password works")


async def test_update_last_login():
    hashed = hash_password("pass")
    store = get_tenant_user_store()
    user = await run_db_operation(
        store.create_user,
        email="j@example.com",
        password=hashed,
        username="jack",
    )

    # Initially None
    before = await run_db_operation(store.get_user_by_id, user.id)
    assert before.last_login_at is None

    await run_db_operation(store.update_last_login, user.id)
    after = await run_db_operation(store.get_user_by_id, user.id)
    assert after.last_login_at is not None
    # Should be recent (within last few seconds)
    now = datetime.now(timezone.utc)
    delta = now - after.last_login_at
    assert delta.total_seconds() < 5
    print("✓ update_last_login works")


async def test_deactivate_user():
    hashed = hash_password("pass")
    store = get_tenant_user_store()
    user = await run_db_operation(
        store.create_user,
        email="k@example.com",
        password=hashed,
        username="kate",
    )

    # Initially active
    fresh = await run_db_operation(store.get_user_by_id, user.id)
    assert fresh.is_active is True

    result = await run_db_operation(store.deactivate_user, user.id)
    assert result is True
    deactivated = await run_db_operation(store.get_user_by_id, user.id)
    assert deactivated.is_active is False

    # Deactivating again returns True (still exists)
    result2 = await run_db_operation(store.deactivate_user, user.id)
    assert result2 is True
    print("✓ deactivate_user works")


async def test_list_all_users():
    store = get_tenant_user_store()
    # Create a few users
    for i in range(3):
        await run_db_operation(
            store.create_user,
            email=f"user{i}@example.com",
            password=hash_password("pass"),
            username=f"user{i}",
        )

    all_users = await run_db_operation(store.list_all_users)
    assert len(all_users) >= 3
    print("✓ list_all_users works")


async def main():
    print("Running TenantUserStore unit tests...")
    await setup_test_db()
    try:
        await test_create_user()
        await test_get_user_by_email()
        await test_get_user_by_username()
        await test_get_user_by_id()
        await test_duplicate_email_and_username()
        await test_update_user()
        await test_verify_email()
        await test_change_password()
        await test_update_last_login()
        await test_deactivate_user()
        await test_list_all_users()
        print("\nAll TenantUserStore unit tests passed.")
    finally:
        await teardown_test_db()


if __name__ == "__main__":
    asyncio.run(main())
