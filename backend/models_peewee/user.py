"""
User and multi-tenancy models.

Tables:
- User: User account
- Tenant: Organization/tenant
- UserTenant: Many-to-many relationship between users and tenants
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import peewee

from .base import BaseModel, JSONTextField


class User(BaseModel):
    """User account."""

    id = peewee.CharField(max_length=32, primary_key=True)
    email = peewee.CharField(max_length=255, unique=True, index=True)
    password = peewee.CharField(max_length=255, null=False)
    username = peewee.CharField(max_length=255, unique=True, index=True, null=True)
    full_name = peewee.CharField(max_length=255, null=True)
    nickname = peewee.CharField(max_length=255, null=True, index=True)
    is_superuser = peewee.BooleanField(null=False, default=False)
    status = peewee.CharField(max_length=1, null=False, default="1", index=True)
    creator = peewee.CharField(max_length=255, null=True)
    email_verified = peewee.BooleanField(null=False, default=False)
    verification_token = peewee.CharField(max_length=255, null=True)
    verification_token_expires = peewee.DateTimeField(null=True)
    last_login_at = peewee.DateTimeField(null=True)

    class Meta:
        table_name = "user"

    @classmethod
    def create_user(
        cls,
        email: str,
        password: str,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        nickname: Optional[str] = None,
        is_superuser: bool = False,
        creator: Optional[str] = None,
        email_verified: bool = False,
        verification_token: Optional[str] = None,
        verification_token_expires: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None,
    ) -> "User":
        """Create a new user with UUID id."""
        now = datetime.utcnow()
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            email=email,
            password=password,
            username=username,
            full_name=full_name,
            nickname=nickname,
            is_superuser=is_superuser,
            status="1",
            creator=creator,
            email_verified=email_verified,
            verification_token=verification_token,
            verification_token_expires=verification_token_expires,
            last_login_at=last_login_at,
            create_date=now,
            create_time=int(now.timestamp()),
            update_date=now,
            update_time=int(now.timestamp()),
        )

    @property
    def is_active(self) -> bool:
        """Check if user account is active (status == '1')."""
        return self.status == "1"

    @property
    def is_admin(self) -> bool:
        """Alias for is_superuser for compatibility."""
        return self.is_superuser

    @property
    def user_id(self) -> str:
        """Alias for id to maintain compatibility with old code."""
        return self.id

    @property
    def hashed_password(self) -> str:
        """Alias for password to maintain compatibility."""
        return self.password

    @property
    def created_at(self):
        """Alias for create_date to maintain compatibility."""
        return self.create_date


class Tenant(BaseModel):
    """Organization/tenant with default LLM and embedding configurations."""

    id = peewee.CharField(max_length=32, primary_key=True)
    name = peewee.CharField(max_length=255, null=False, index=True)
    llm_id = peewee.CharField(
        max_length=128, null=False, help_text="Default chat model ID"
    )
    embd_id = peewee.CharField(
        max_length=128, null=False, help_text="Default embedding model ID"
    )
    asr_id = peewee.CharField(
        max_length=256, null=True, help_text="Default ASR model ID"
    )
    parser_ids = peewee.TextField(null=False, help_text="Comma-separated parser IDs")
    img2txt_id = peewee.CharField(
        max_length=256, null=True, help_text="Default image-to-text model ID"
    )
    rerank_id = peewee.CharField(
        max_length=128, null=False, default="BAAI/bge-reranker-v2-m3"
    )

    class Meta:
        table_name = "tenant"

    @classmethod
    def create_tenant(
        cls,
        name: str,
        llm_id: str,
        embd_id: str,
        parser_ids: str,
        asr_id: Optional[str] = None,
        img2txt_id: Optional[str] = None,
        rerank_id: str = "BAAI/bge-reranker-v2-m3",
    ) -> "Tenant":
        """Create a new tenant with UUID id."""
        now = datetime.utcnow()
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            name=name,
            llm_id=llm_id,
            embd_id=embd_id,
            asr_id=asr_id,
            parser_ids=parser_ids,
            img2txt_id=img2txt_id,
            rerank_id=rerank_id,
            create_date=now,
            create_time=int(now.timestamp()),
            update_date=now,
            update_time=int(now.timestamp()),
        )


class UserTenant(BaseModel):
    """Many-to-many relationship between users and tenants.

    Composite primary key: (user_id, tenant_id)
    """

    user_id = peewee.CharField(max_length=255, null=False, index=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    invited_by = peewee.CharField(max_length=32, null=False)
    role = peewee.CharField(
        max_length=16, null=False, default="normal", index=True
    )  # owner/admin/normal/invite

    class Meta:
        table_name = "user_tenant"
        primary_key = peewee.CompositeKey("user_id", "tenant_id")

    @classmethod
    def add_user_to_tenant(
        cls,
        user_id: str,
        tenant_id: str,
        invited_by: str,
        role: str = "normal",
    ) -> "UserTenant":
        """Associate a user with a tenant."""
        return cls.create(
            user_id=user_id,
            tenant_id=tenant_id,
            invited_by=invited_by,
            role=role,
        )
