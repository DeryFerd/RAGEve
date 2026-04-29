"""
System and API management store.

Manages system settings, API tokens, MCP servers, search configs,
and pipeline operation logs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.models_peewee import (
    MCP,
    API4Conversation,
    APIToken,
    PipelineOperationLog,
    Search,
    SystemSettings,
    get_database,
)

_log = logging.getLogger(__name__)


class SystemStore:
    """CRUD operations for system and API management tables."""

    # ==================== SystemSettings ====================

    def get_setting(self, name: str, default: Any = None) -> Any:
        """Get a system setting value."""
        with get_database().connection_context():
            try:
                setting = SystemSettings.get(SystemSettings.name == name)
                value = setting.value
                # Deserialize JSON if data_type is json
                if setting.data_type == "json":
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return default
                return value
            except SystemSettings.DoesNotExist:
                return default

    def set_setting(
        self,
        name: str,
        value: Any,
        source: str = "system",
        data_type: str = "string",
    ) -> SystemSettings:
        """Create or update a system setting."""
        with get_database().connection_context():
            # Serialize to JSON if data_type is json
            if data_type == "json" and isinstance(value, (dict, list)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            setting = SystemSettings.set_value(
                name=name,
                value=value_str,
                source=source,
                data_type=data_type,
            )
            return setting

    def list_settings(self) -> list[dict]:
        """List all system settings."""
        with get_database().connection_context():
            query = SystemSettings.select()
            return [s.to_dict() for s in query]

    # ==================== API Tokens ====================

    def create_api_token(
        self,
        tenant_id: str,
        token: str,
        dialog_id: str | None = None,
        source: str | None = None,
        beta: str | None = None,
    ) -> APIToken:
        """Create a new API token."""
        with get_database().connection_context():
            t = APIToken.create_token(
                tenant_id=tenant_id,
                token=token,
                dialog_id=dialog_id,
                source=source,
                beta=beta,
            )
            _log.info("Created API token for tenant %s", tenant_id)
            return t

    def verify_api_token(
        self, token: str, tenant_id: str | None = None
    ) -> APIToken | None:
        """Verify an API token and return associated token record."""
        with get_database().connection_context():
            try:
                query = APIToken.select().where(APIToken.token == token)
                if tenant_id:
                    query = query.where(APIToken.tenant_id == tenant_id)
                return query.get()
            except APIToken.DoesNotExist:
                return None

    def revoke_api_token(self, tenant_id: str, token: str) -> bool:
        """Revoke (delete) an API token."""
        with get_database().connection_context():
            try:
                t = APIToken.get(
                    (APIToken.tenant_id == tenant_id) & (APIToken.token == token)
                )
                t.delete_instance()
                _log.info("Revoked API token for tenant %s", tenant_id)
                return True
            except APIToken.DoesNotExist:
                return False

    # ==================== API Conversation Logs ====================

    def log_api_conversation(
        self,
        dialog_id: str,
        user_id: str,
        message: list | None = None,
        reference: list | None = None,
        tokens: int = 0,
        source: str | None = None,
        dsl: dict | None = None,
        duration: float = 0,
        round: int = 0,
        thumb_up: int = 0,
        errors: str | None = None,
    ) -> API4Conversation:
        """Log an API conversation for analytics."""
        with get_database().connection_context():
            log = API4Conversation.log_conversation(
                dialog_id=dialog_id,
                user_id=user_id,
                message=message,
                reference=reference,
                tokens=tokens,
                source=source,
                dsl=dsl,
                duration=duration,
                round=round,
                thumb_up=thumb_up,
                errors=errors,
            )
            return log

    # ==================== MCP Servers ====================

    def create_mcp_server(
        self,
        tenant_id: str,
        name: str,
        url: str,
        server_type: str,
        description: str | None = None,
        variables: dict | None = None,
        headers: dict | None = None,
    ) -> MCP:
        """Create an MCP server configuration."""
        with get_database().connection_context():
            mcp = MCP.create_mcp_server(
                tenant_id=tenant_id,
                name=name,
                url=url,
                server_type=server_type,
                description=description,
                variables=variables or {},
                headers=headers or {},
            )
            _log.info("Created MCP server %s for tenant %s", name, tenant_id)
            return mcp

    def list_mcp_servers(self, tenant_id: str) -> list[dict]:
        """List MCP servers for a tenant."""
        with get_database().connection_context():
            query = MCP.select().where(MCP.tenant_id == tenant_id)
            return [m.to_dict() for m in query]

    def delete_mcp_server(self, mcp_id: str) -> bool:
        """Delete an MCP server."""
        with get_database().connection_context():
            try:
                mcp = MCP.get(MCP.id == mcp_id)
                mcp.delete_instance()
                _log.info("Deleted MCP server %s", mcp_id)
                return True
            except MCP.DoesNotExist:
                return False

    # ==================== Search Configs ====================

    def create_search(
        self,
        tenant_id: str,
        name: str,
        created_by: str,
        description: str | None = None,
        search_config: dict | None = None,
        status: str = "1",
    ) -> Search:
        """Create a saved search configuration."""
        with get_database().connection_context():
            s = Search.create_search(
                tenant_id=tenant_id,
                name=name,
                created_by=created_by,
                description=description,
                search_config=search_config,
                status=status,
            )
            _log.info("Created search config %s for tenant %s", s.id, tenant_id)
            return s

    def list_searches(
        self,
        tenant_id: str | None = None,
        created_by: str | None = None,
    ) -> list[dict]:
        """List saved searches."""
        with get_database().connection_context():
            query = Search.select()
            if tenant_id:
                query = query.where(Search.tenant_id == tenant_id)
            if created_by:
                query = query.where(Search.created_by == created_by)
            return [s.to_dict() for s in query]

    # ==================== Pipeline Operation Logs ====================

    def create_pipeline_log(
        self,
        document_id: str,
        tenant_id: str,
        kb_id: str,
        parser_id: str,
        document_name: str,
        document_suffix: str,
        document_type: str,
        source_from: str,
        task_type: str = "",
        operation_status: str = "",
        pipeline_id: str | None = None,
        pipeline_title: str | None = None,
    ) -> PipelineOperationLog:
        """Create a pipeline operation log entry."""
        with get_database().connection_context():
            log = PipelineOperationLog.create_log(
                document_id=document_id,
                tenant_id=tenant_id,
                kb_id=kb_id,
                parser_id=parser_id,
                document_name=document_name,
                document_suffix=document_suffix,
                document_type=document_type,
                source_from=source_from,
                task_type=task_type,
                operation_status=operation_status,
                pipeline_id=pipeline_id,
                pipeline_title=pipeline_title,
            )
            return log

    def update_pipeline_log_progress(
        self,
        log_id: str,
        progress: float,
        msg: str | None = None,
        status: str = "1",
    ) -> PipelineOperationLog | None:
        """Update pipeline log progress."""
        with get_database().connection_context():
            try:
                log = PipelineOperationLog.get(PipelineOperationLog.id == log_id)
                log.progress = progress
                if msg:
                    log.progress_msg = msg
                log.status = status
                log.save()
                return log
            except PipelineOperationLog.DoesNotExist:
                return None

    def get_pipeline_logs(
        self,
        document_id: str | None = None,
        tenant_id: str | None = None,
        kb_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get pipeline operation logs with filters."""
        with get_database().connection_context():
            query = PipelineOperationLog.select()
            if document_id:
                query = query.where(PipelineOperationLog.document_id == document_id)
            if tenant_id:
                query = query.where(PipelineOperationLog.tenant_id == tenant_id)
            if kb_id:
                query = query.where(PipelineOperationLog.kb_id == kb_id)
            query = query.order_by(PipelineOperationLog.create_time.desc()).limit(limit)
            return [l.to_dict() for l in query]


# Singleton
_system_store: SystemStore | None = None


def get_system_store() -> SystemStore:
    global _system_store
    if _system_store is None:
        _system_store = SystemStore()
    return _system_store
