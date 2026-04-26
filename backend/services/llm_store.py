"""
LLM provider and model configuration store.

Manages LLM factories, models, and tenant-specific overrides.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.models_peewee import (
    LLMFactories,
    LLM,
    TenantLLM,
    get_database,
)

_log = logging.getLogger(__name__)


class LLMStore:
    """CRUD operations for LLM configurations."""

    # ==================== Factories ====================

    def create_factory(
        self,
        name: str,
        llm_name: str,
        api_base: str | None = None,
        api_key: str | None = None,
        description: str | None = None,
        status: str = "1",
        rank: int = 0,
    ) -> LLMFactories:
        """Create a new LLM factory (provider)."""
        with get_database().connection_context():
            factory = LLMFactories.create_factory(
                name=name,
                llm_name=llm_name,
                api_base=api_base,
                api_key=api_key,
                description=description,
                status=status,
                rank=rank,
            )
            _log.info("Created LLM factory %s", name)
            return factory

    def get_factory(self, name: str) -> LLMFactories | None:
        """Get a factory by name."""
        with get_database().connection_context():
            try:
                return LLMFactories.get(LLMFactories.name == name)
            except LLMFactories.DoesNotExist:
                return None

    def list_factories(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List all factories, optionally filtered by status."""
        with get_database().connection_context():
            query = LLMFactories.select()
            if status:
                query = query.where(LLMFactories.status == status)
            query = query.order_by(LLMFactories.rank.asc())
            results = query.limit(limit)
            return [f.to_dict() for f in results]

    def update_factory(self, name: str, **updates: Any) -> LLMFactories | None:
        """Update factory by name."""
        with get_database().connection_context():
            try:
                factory = LLMFactories.get(LLMFactories.name == name)
                for key, value in updates.items():
                    if hasattr(factory, key):
                        setattr(factory, key, value)
                factory.save()
                _log.info("Updated factory %s", name)
                return factory
            except LLMFactories.DoesNotExist:
                return None

    # ==================== LLM Models ====================

    def create_llm(
        self,
        fid: str,
        llm_name: str,
        model_type: str = "chat",
        max_tokens: int = 8192,
        tags: list | None = None,
        is_tools: bool = False,
    ) -> LLM:
        """Create a new LLM model entry."""
        with get_database().connection_context():
            llm = LLM.create_llm(
                fid=fid,
                llm_name=llm_name,
                model_type=model_type,
                max_tokens=max_tokens,
                tags=tags,
                is_tools=is_tools,
            )
            _log.info("Created LLM %s (factory: %s, type: %s)", llm_name, fid, model_type)
            return llm

    def get_llm(self, llm_id: str) -> LLM | None:
        """Get an LLM by ID."""
        with get_database().connection_context():
            try:
                return LLM.get(LLM.id == llm_id)
            except LLM.DoesNotExist:
                return None

    def list_llms(
        self,
        fid: str | None = None,
        model_type: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List LLMs with optional filters."""
        with get_database().connection_context():
            query = LLM.select()
            if fid:
                query = query.where(LLM.fid == fid)
            if model_type:
                query = query.where(LLM.model_type == model_type)
            results = query.limit(limit)
            return [m.to_dict() for m in results]

    def update_llm_usage(self, llm_id: str, tokens: int) -> LLM | None:
        """Increment used_tokens for an LLM."""
        with get_database().connection_context():
            try:
                llm = LLM.get(LLM.id == llm_id)
                llm.used_tokens += tokens
                llm.save()
                return llm
            except LLM.DoesNotExist:
                return None

    # ==================== Tenant LLM Overrides ====================

    def set_tenant_llm(
        self,
        tenant_id: str,
        llm_factory: str,
        llm_name: str,
        model_type: str,
        api_key: str | None = None,
        max_tokens: int = 8192,
        status: str = "1",
    ) -> TenantLLM:
        """Set or update a tenant-specific LLM override."""
        with get_database().connection_context():
            # Check if exists
            try:
                tllm = TenantLLM.get(
                    (TenantLLM.tenant_id == tenant_id) &
                    (TenantLLM.llm_factory == llm_factory) &
                    (TenantLLM.model_type == model_type)
                )
                tllm.llm_name = llm_name
                tllm.api_key = api_key
                tllm.max_tokens = max_tokens
                tllm.status = status
                tllm.save()
                _log.info("Updated tenant LLM override for tenant %s", tenant_id)
                return tllm
            except TenantLLM.DoesNotExist:
                tllm = TenantLLM.create_tenant_llm(
                    tenant_id=tenant_id,
                    llm_factory=llm_factory,
                    llm_name=llm_name,
                    model_type=model_type,
                    api_key=api_key,
                    max_tokens=max_tokens,
                    status=status,
                )
                _log.info("Created tenant LLM override for tenant %s", tenant_id)
                return tllm

    def get_tenant_llm(
        self,
        tenant_id: str,
        model_type: str,
    ) -> TenantLLM | None:
        """Get tenant-specific LLM override for a model type."""
        with get_database().connection_context():
            try:
                return TenantLLM.get(
                    (TenantLLM.tenant_id == tenant_id) &
                    (TenantLLM.model_type == model_type) &
                    (TenantLLM.status == "1")
                )
            except TenantLLM.DoesNotExist:
                return None

    def list_tenant_llms(self, tenant_id: str) -> list[dict]:
        """List all LLM overrides for a tenant."""
        with get_database().connection_context():
            query = TenantLLM.select().where(TenantLLM.tenant_id == tenant_id)
            return [t.to_dict() for t in query]

    def delete_tenant_llm(self, tenant_id: str, model_type: str) -> bool:
        """Delete a tenant LLM override."""
        with get_database().connection_context():
            try:
                tllm = TenantLLM.get(
                    (TenantLLM.tenant_id == tenant_id) &
                    (TenantLLM.model_type == model_type)
                )
                tllm.delete_instance()
                _log.info("Deleted tenant LLM override (tenant %s, type: %s)", tenant_id, model_type)
                return True
            except TenantLLM.DoesNotExist:
                return False


# Singleton
_llm_store: LLMStore | None = None


def get_llm_store() -> LLMStore:
    global _llm_store
    if _llm_store is None:
        _llm_store = LLMStore()
    return _llm_store
