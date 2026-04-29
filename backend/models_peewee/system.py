"""
System and API management models.

Tables:
- SystemSettings: Global configuration settings
- APIToken: API authentication tokens
- API4Conversation: API conversation tracking (usage analytics)
- MCP: Model Context Protocol server configuration
- Search: Saved search configurations
- PipelineOperationLog: Document processing pipeline logs
"""

from __future__ import annotations

import uuid
from typing import Optional

import peewee

from .base import BaseModel, JSONTextField


class SystemSettings(BaseModel):
    """System configuration settings (key-value store)."""

    name = peewee.CharField(max_length=128, primary_key=True)
    source = peewee.CharField(max_length=32, null=False)
    data_type = peewee.CharField(max_length=32, null=False)
    value = peewee.CharField(max_length=1024, null=False)

    class Meta:
        table_name = "system_settings"

    @classmethod
    def get_value(cls, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get setting value by name."""
        try:
            setting = cls.get(cls.name == name)
            return setting.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(
        cls, name: str, value: str, source: str = "system", data_type: str = "string"
    ):
        """Set setting value (create or update)."""
        setting, created = cls.get_or_create(
            name=name,
            defaults={
                "source": source,
                "data_type": data_type,
                "value": value,
            },
        )
        if not created:
            setting.source = source
            setting.data_type = data_type
            setting.value = value
            setting.save()
        return setting


class APIToken(BaseModel):
    """API authentication tokens (tenant-based)."""

    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    token = peewee.CharField(max_length=255, null=False, index=True)
    dialog_id = peewee.CharField(max_length=32, null=True, index=True)
    source = peewee.CharField(max_length=16, null=True, index=True)
    beta = peewee.CharField(max_length=255, null=True, index=True)

    class Meta:
        table_name = "api_token"
        primary_key = peewee.CompositeKey("tenant_id", "token")

    @classmethod
    def create_token(
        cls,
        tenant_id: str,
        token: str,
        dialog_id: Optional[str] = None,
        source: Optional[str] = None,
        beta: Optional[str] = None,
    ) -> "APIToken":
        """Create a new API token."""
        return cls.create(
            tenant_id=tenant_id,
            token=token,
            dialog_id=dialog_id,
            source=source,
            beta=beta,
        )


class API4Conversation(BaseModel):
    """API conversation tracking (for usage analytics)."""

    id = peewee.CharField(max_length=32, primary_key=True)
    dialog_id = peewee.CharField(max_length=32, null=False, index=True)
    user_id = peewee.CharField(max_length=255, null=False, index=True)
    message = JSONTextField(null=True)
    reference = JSONTextField(null=True, default=[])
    tokens = peewee.IntegerField(null=False, default=0)
    source = peewee.CharField(max_length=16, null=True, index=True)
    dsl = JSONTextField(null=True, default={})
    duration = peewee.FloatField(null=False, default=0, index=True)
    round = peewee.IntegerField(null=False, default=0, index=True)
    thumb_up = peewee.IntegerField(null=False, default=0, index=True)
    errors = peewee.TextField(null=True)

    class Meta:
        table_name = "api_4_conversation"

    @classmethod
    def log_conversation(
        cls,
        dialog_id: str,
        user_id: str,
        message: Optional[list] = None,
        reference: Optional[list] = None,
        tokens: int = 0,
        source: Optional[str] = None,
        dsl: Optional[dict] = None,
        duration: float = 0,
        round: int = 0,
        thumb_up: int = 0,
        errors: Optional[str] = None,
    ) -> "API4Conversation":
        """Log an API conversation for analytics."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            dialog_id=dialog_id,
            user_id=user_id,
            message=message,
            reference=reference or [],
            tokens=tokens,
            source=source,
            dsl=dsl or {},
            duration=duration,
            round=round,
            thumb_up=thumb_up,
            errors=errors or "",
        )


class MCP(BaseModel):
    """Model Context Protocol server configuration."""

    id = peewee.CharField(max_length=32, primary_key=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=255, null=False)
    url = peewee.CharField(max_length=2048, null=False)
    server_type = peewee.CharField(max_length=32, null=False)
    description = peewee.TextField(null=True)
    variables = JSONTextField(null=True, default={})
    headers = JSONTextField(null=True, default={})

    class Meta:
        table_name = "mcp_server"

    @classmethod
    def create_mcp_server(
        cls,
        tenant_id: str,
        name: str,
        url: str,
        server_type: str,
        description: Optional[str] = None,
        variables: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> "MCP":
        """Create an MCP server configuration."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            tenant_id=tenant_id,
            name=name,
            url=url,
            server_type=server_type,
            description=description,
            variables=variables or {},
            headers=headers or {},
        )


class Search(BaseModel):
    """Saved search configurations."""

    id = peewee.CharField(max_length=32, primary_key=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=128, null=False, index=True)
    description = peewee.TextField(null=True)
    created_by = peewee.CharField(max_length=32, null=False, index=True)
    search_config = JSONTextField(
        null=False,
        default={
            "kb_ids": [],
            "doc_ids": [],
            "similarity_threshold": 0.2,
            "vector_similarity_weight": 0.3,
            "use_kg": False,
            "rerank_id": "",
            "top_k": 1024,
            "summary": False,
            "chat_id": "",
            "chat_settingcross_languages": [],
            "highlight": False,
            "keyword": False,
            "web_search": False,
            "related_search": False,
            "query_mindmap": False,
        },
    )
    status = peewee.CharField(max_length=1, null=True, default="1", index=True)

    class Meta:
        table_name = "search"

    @classmethod
    def create_search(
        cls,
        tenant_id: str,
        name: str,
        created_by: str,
        description: Optional[str] = None,
        search_config: Optional[dict] = None,
        status: str = "1",
    ) -> "Search":
        """Create a saved search configuration."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            tenant_id=tenant_id,
            name=name,
            description=description,
            created_by=created_by,
            search_config=search_config
            or {
                "kb_ids": [],
                "doc_ids": [],
                "similarity_threshold": 0.2,
                "vector_similarity_weight": 0.3,
                "use_kg": False,
                "rerank_id": "",
                "top_k": 1024,
                "summary": False,
                "chat_id": "",
                "chat_settingcross_languages": [],
                "highlight": False,
                "keyword": False,
                "web_search": False,
                "related_search": False,
                "query_mindmap": False,
            },
            status=status,
        )


class PipelineOperationLog(BaseModel):
    """Document processing pipeline logs."""

    id = peewee.CharField(max_length=32, primary_key=True)
    document_id = peewee.CharField(max_length=32, null=False, index=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    kb_id = peewee.CharField(max_length=32, null=False, index=True)
    pipeline_id = peewee.CharField(max_length=32, null=True, index=True)
    pipeline_title = peewee.CharField(max_length=32, null=True, index=True)
    parser_id = peewee.CharField(max_length=32, null=False, index=True)
    document_name = peewee.CharField(max_length=255, null=False)
    document_suffix = peewee.CharField(max_length=255, null=False)
    document_type = peewee.CharField(max_length=255, null=False)
    source_from = peewee.CharField(max_length=255, null=False)
    progress = peewee.FloatField(null=False, default=0, index=True)
    progress_msg = peewee.TextField(null=True, default="")
    process_begin_at = peewee.DateTimeField(null=True, index=True)
    process_duation = peewee.FloatField(null=False, default=0)
    dsl = JSONTextField(null=True, default={})
    task_type = peewee.CharField(max_length=32, null=False, default="")
    operation_status = peewee.CharField(max_length=32, null=False)
    avatar = peewee.TextField(null=True)
    status = peewee.CharField(max_length=1, null=True, default="1", index=True)

    class Meta:
        table_name = "pipeline_operation_log"

    @classmethod
    def create_log(
        cls,
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
        pipeline_id: Optional[str] = None,
        pipeline_title: Optional[str] = None,
    ) -> "PipelineOperationLog":
        """Create a pipeline operation log entry."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            document_id=document_id,
            tenant_id=tenant_id,
            kb_id=kb_id,
            pipeline_id=pipeline_id,
            pipeline_title=pipeline_title,
            parser_id=parser_id,
            document_name=document_name,
            document_suffix=document_suffix,
            document_type=document_type,
            source_from=source_from,
            progress=0,
            progress_msg="",
            process_begin_at=None,
            process_duation=0,
            dsl={},
            task_type=task_type,
            operation_status=operation_status,
            avatar=None,
            status="1",
        )
