"""
LLM provider and model configuration models.

Tables:
- LLMFactories: LLM provider definitions (OpenAI, Anthropic, Ollama, etc.)
- LLM: Individual LLM model configurations per factory
- TenantLLM: Tenant-specific LLM overrides
"""

from __future__ import annotations

import uuid
from typing import Optional

import peewee

from .base import BaseModel, JSONTextField


class LLMFactories(BaseModel):
    """LLM provider/factory definition."""

    id = peewee.CharField(max_length=32, primary_key=True)
    name = peewee.CharField(
        max_length=128,
        null=False,
        unique=True,
        index=True,
        help_text="Provider name: OpenAI, Anthropic, etc.",
    )
    llm_name = peewee.CharField(max_length=256, null=False, help_text="Model name")
    api_base = peewee.CharField(max_length=512, null=True, help_text="API endpoint URL")
    api_key = peewee.TextField(null=True, help_text="API key (encrypted)")
    description = peewee.TextField(null=True)
    status = peewee.CharField(max_length=1, null=False, default="1", index=True)
    rank = peewee.IntegerField(null=False, default=0, index=True)

    class Meta:
        table_name = "llm_factories"

    @classmethod
    def create_factory(
        cls,
        name: str,
        llm_name: str,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        description: Optional[str] = None,
        status: str = "1",
        rank: int = 0,
    ) -> "LLMFactories":
        """Create a new LLM factory."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            name=name,
            llm_name=llm_name,
            api_base=api_base,
            api_key=api_key,
            description=description,
            status=status,
            rank=rank,
        )


class LLM(BaseModel):
    """Individual LLM model configuration within a factory."""

    id = peewee.CharField(max_length=32, primary_key=True)
    fid = peewee.CharField(
        max_length=128,
        null=False,
        index=True,
        help_text="Factory ID (foreign key to llm_factories.name)",
    )
    llm_name = peewee.CharField(max_length=256, null=False, help_text="Model name")
    model_type = peewee.CharField(
        max_length=32,
        null=False,
        default="chat",
        help_text="chat/embedding/rerank/asr/image2text",
    )
    max_tokens = peewee.IntegerField(null=False, default=8192)
    used_tokens = peewee.BigIntegerField(null=False, default=0)
    tags = JSONTextField(null=True, default=[])
    is_tools = peewee.BooleanField(
        null=False, default=False, help_text="Support tool calling"
    )

    class Meta:
        table_name = "llm"

    @classmethod
    def create_llm(
        cls,
        fid: str,
        llm_name: str,
        model_type: str = "chat",
        max_tokens: int = 8192,
        tags: Optional[list] = None,
        is_tools: bool = False,
    ) -> "LLM":
        """Create a new LLM model entry."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            fid=fid,
            llm_name=llm_name,
            model_type=model_type,
            max_tokens=max_tokens,
            used_tokens=0,
            tags=tags or [],
            is_tools=is_tools,
        )


class TenantLLM(BaseModel):
    """Tenant-specific LLM configuration (overrides factory defaults)."""

    id = peewee.CharField(max_length=32, primary_key=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    llm_factory = peewee.CharField(
        max_length=128, null=False, help_text="Provider name"
    )
    llm_name = peewee.CharField(max_length=256, null=False, help_text="Model name")
    model_type = peewee.CharField(
        max_length=32, null=False, help_text="chat/embedding/rerank"
    )
    api_key = peewee.TextField(null=True, help_text="API key (overrides factory)")
    max_tokens = peewee.IntegerField(null=False, default=8192)
    used_tokens = peewee.BigIntegerField(null=False, default=0)
    status = peewee.CharField(max_length=1, null=False, default="1", index=True)

    class Meta:
        table_name = "tenant_llm"

    @classmethod
    def create_tenant_llm(
        cls,
        tenant_id: str,
        llm_factory: str,
        llm_name: str,
        model_type: str,
        api_key: Optional[str] = None,
        max_tokens: int = 8192,
        status: str = "1",
    ) -> "TenantLLM":
        """Create a tenant-specific LLM override."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            tenant_id=tenant_id,
            llm_factory=llm_factory,
            llm_name=llm_name,
            model_type=model_type,
            api_key=api_key,
            max_tokens=max_tokens,
            used_tokens=0,
            status=status,
        )
