"""
Tenant and user management service.

Handles multi-tenancy: tenants, users, and their relationships.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.models_peewee import Tenant, User, UserTenant, get_database

_log = logging.getLogger(__name__)


class TenantUserStore:
    """CRUD operations for tenants, users, and their relationships."""

    # ==================== Tenants ====================

    def create_tenant(
        self,
        name: str,
        llm_id: str,
        embd_id: str,
        created_by: str,
        parser_ids: str = "",
        asr_id: str | None = None,
        img2txt_id: str | None = None,
        rerank_id: str = "BAAI/bge-reranker-v2-m3",
    ) -> Tenant:
        """Create a new tenant."""
        with get_database().connection_context():
            tenant = Tenant.create_tenant(
                name=name,
                llm_id=llm_id,
                embd_id=embd_id,
                parser_ids=parser_ids,
                asr_id=asr_id,
                img2txt_id=img2txt_id,
                rerank_id=rerank_id,
            )
            _log.info("Created tenant %s (name: %s)", tenant.id, name)
            return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID."""
        with get_database().connection_context():
            try:
                return Tenant.get(Tenant.id == tenant_id)
            except Tenant.DoesNotExist:
                return None

    def list_tenants(
        self,
        created_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List tenants with optional filter."""
        with get_database().connection_context():
            query = Tenant.select()
            if created_by:
                query = query.where(Tenant.created_by == created_by)

            total = query.count()
            results = (
                query.order_by(Tenant.create_time.desc()).limit(limit).offset(offset)
            )
            return [t.to_dict() for t in results], total

    def update_tenant(self, tenant_id: str, **updates: Any) -> Tenant | None:
        """Update tenant fields."""
        with get_database().connection_context():
            try:
                tenant = Tenant.get(Tenant.id == tenant_id)
                for key, value in updates.items():
                    if hasattr(tenant, key):
                        setattr(tenant, key, value)
                tenant.save()
                _log.info("Updated tenant %s", tenant_id)
                return tenant
            except Tenant.DoesNotExist:
                return None

    # ==================== Users ====================

    def create_user(
        self,
        email: str,
        password: str,
        username: str | None = None,
        full_name: str | None = None,
        nickname: str | None = None,
        is_superuser: bool = False,
        creator: str | None = None,
        email_verified: bool = False,
        verification_token: str | None = None,
        verification_token_expires: datetime | None = None,
        last_login_at: datetime | None = None,
    ) -> User:
        """Create a new user."""
        with get_database().connection_context():
            user = User.create_user(
                email=email,
                password=password,
                username=username,
                full_name=full_name,
                nickname=nickname,
                is_superuser=is_superuser,
                creator=creator,
                email_verified=email_verified,
                verification_token=verification_token,
                verification_token_expires=verification_token_expires,
                last_login_at=last_login_at,
            )
            _log.info("Created user %s (email: %s)", user.id, email)
            return user

    def get_user(self, user_id: str) -> User | None:
        """Get a user by ID."""
        with get_database().connection_context():
            try:
                return User.get(User.id == user_id)
            except User.DoesNotExist:
                return None

    def get_user_by_id(self, user_id: str) -> User | None:
        """Alias for get_user (for compatibility)."""
        return self.get_user(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        """Get a user by email."""
        with get_database().connection_context():
            try:
                return User.get(User.email == email)
            except User.DoesNotExist:
                return None

    def get_user_by_username(self, username: str) -> User | None:
        """Get a user by username."""
        with get_database().connection_context():
            try:
                return User.get(User.username == username)
            except User.DoesNotExist:
                return None

    def get_user_by_verification_token(self, token: str) -> User | None:
        """Get a user by verification token."""
        with get_database().connection_context():
            try:
                return User.get(User.verification_token == token)
            except User.DoesNotExist:
                return None

    def list_users(
        self,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List users with optional filter."""
        with get_database().connection_context():
            query = User.select()
            if is_active is not None:
                # Filter by status field: '1' for active, '0' for inactive
                status_val = "1" if is_active else "0"
                query = query.where(User.status == status_val)

            total = query.count()
            results = (
                query.order_by(User.create_time.desc()).limit(limit).offset(offset)
            )
            return [u.to_dict() for u in results], total

    def list_all_users(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """List all users (returns just the list, no total)."""
        users, _ = self.list_users(is_active=None, limit=limit, offset=offset)
        return users

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user (set status to '0'). Returns True if user existed, False otherwise."""
        with get_database().connection_context():
            try:
                user = User.get(User.id == user_id)
                user.status = "0"
                user.save()
                _log.info("Deactivated user %s", user_id)
                return True
            except User.DoesNotExist:
                return False

    def update_user(self, user_id: str, **updates: Any) -> User | None:
        """Update user fields."""
        with get_database().connection_context():
            try:
                user = User.get(User.id == user_id)
                for key, value in updates.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.save()
                _log.info("Updated user %s", user_id)
                return user
            except User.DoesNotExist:
                return None

    def verify_email(self, user_id: str) -> User | None:
        """Mark user's email as verified and clear verification token."""
        with get_database().connection_context():
            try:
                user = User.get(User.id == user_id)
                user.email_verified = True
                user.verification_token = None
                user.verification_token_expires = None
                user.save()
                _log.info("Verified email for user %s", user_id)
                return user
            except User.DoesNotExist:
                return None

    def update_last_login(self, user_id: str) -> User | None:
        """Update last_login_at to now."""
        with get_database().connection_context():
            try:
                user = User.get(User.id == user_id)
                user.last_login_at = datetime.now(timezone.utc)
                user.save()
                return user
            except User.DoesNotExist:
                return None

    def change_password(self, user_id: str, new_hashed_password: str) -> User | None:
        """Change user's password."""
        with get_database().connection_context():
            try:
                user = User.get(User.id == user_id)
                user.password = new_hashed_password
                user.save()
                _log.info("Changed password for user %s", user_id)
                return user
            except User.DoesNotExist:
                return None

    # ==================== User-Tenant Relationships ====================

    def add_user_to_tenant(
        self,
        user_id: str,
        tenant_id: str,
        invited_by: str,
        role: str = "normal",
    ) -> UserTenant:
        """Associate a user with a tenant."""
        with get_database().connection_context():
            # Check if already exists
            try:
                existing = UserTenant.get(
                    (UserTenant.user_id == user_id)
                    & (UserTenant.tenant_id == tenant_id)
                )
                # Update role if exists
                existing.role = role
                existing.invited_by = invited_by
                existing.save()
                _log.info(
                    "Updated user %s role in tenant %s to %s", user_id, tenant_id, role
                )
                return existing
            except UserTenant.DoesNotExist:
                ut = UserTenant.add_user_to_tenant(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    invited_by=invited_by,
                    role=role,
                )
                _log.info(
                    "Added user %s to tenant %s (role: %s)", user_id, tenant_id, role
                )
                return ut

    def remove_user_from_tenant(self, user_id: str, tenant_id: str) -> bool:
        """Remove a user from a tenant."""
        with get_database().connection_context():
            try:
                ut = UserTenant.get(
                    (UserTenant.user_id == user_id)
                    & (UserTenant.tenant_id == tenant_id)
                )
                ut.delete_instance()
                _log.info("Removed user %s from tenant %s", user_id, tenant_id)
                return True
            except UserTenant.DoesNotExist:
                return False

    def get_tenants_for_user(self, user_id: str) -> list[Tenant]:
        """Get all tenants that a user belongs to."""
        with get_database().connection_context():
            query = (
                Tenant.select()
                .join(UserTenant, on=(Tenant.id == UserTenant.tenant_id))
                .where(UserTenant.user_id == user_id)
            )
            return list(query)

    def get_users_in_tenant(
        self,
        tenant_id: str,
        role: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get all users in a tenant, optionally filtered by role."""
        with get_database().connection_context():
            query = (
                User.select()
                .join(UserTenant, on=(User.id == UserTenant.user_id))
                .where(UserTenant.tenant_id == tenant_id)
            )
            if role:
                query = query.where(UserTenant.role == role)

            results = query.limit(limit).offset(offset)
            return [u.to_dict() for u in results]

    def get_user_role_in_tenant(self, user_id: str, tenant_id: str) -> str | None:
        """Get the role of a user within a specific tenant."""
        with get_database().connection_context():
            try:
                ut = UserTenant.get(
                    (UserTenant.user_id == user_id)
                    & (UserTenant.tenant_id == tenant_id)
                )
                return ut.role
            except UserTenant.DoesNotExist:
                return None


# Singleton
_tenant_user_store: TenantUserStore | None = None


def get_tenant_user_store() -> TenantUserStore:
    global _tenant_user_store
    if _tenant_user_store is None:
        _tenant_user_store = TenantUserStore()
    return _tenant_user_store
