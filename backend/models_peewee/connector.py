"""
External data source connector models.

Tables:
- Connector: External data source configuration (website, confluence, etc.)
- Connector2Kb: Many-to-many mapping between connectors and knowledgebases
- SyncLogs: History of connector sync operations
"""

from __future__ import annotations

import uuid
from typing import Optional

import peewee

from .base import BaseModel, JSONTextField


class Connector(BaseModel):
    """External data source connector."""

    id = peewee.CharField(max_length=32, primary_key=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=128, null=False)
    source = peewee.CharField(
        max_length=128,
        null=False,
        index=True,
        help_text="DataSource: website, confluence, etc.",
    )
    input_type = peewee.CharField(
        max_length=128, null=False, index=True, help_text="poll/event/slim_retrieval"
    )
    config = JSONTextField(null=False, default={})
    refresh_freq = peewee.IntegerField(
        null=False, default=0, help_text="Refresh frequency in seconds"
    )
    prune_freq = peewee.IntegerField(null=False, default=0)
    timeout_secs = peewee.IntegerField(null=False, default=3600)
    indexing_start = peewee.DateTimeField(null=True, index=True)
    status = peewee.CharField(max_length=16, null=True, default="schedule", index=True)

    class Meta:
        table_name = "connector"

    @classmethod
    def create_connector(
        cls,
        tenant_id: str,
        name: str,
        source: str,
        input_type: str,
        config: Optional[dict] = None,
        refresh_freq: int = 0,
        prune_freq: int = 0,
        timeout_secs: int = 3600,
        status: str = "schedule",
    ) -> "Connector":
        """Create a new connector."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            tenant_id=tenant_id,
            name=name,
            source=source,
            input_type=input_type,
            config=config or {},
            refresh_freq=refresh_freq,
            prune_freq=prune_freq,
            timeout_secs=timeout_secs,
            indexing_start=None,
            status=status,
        )


class Connector2Kb(BaseModel):
    """Many-to-many mapping between connectors and knowledgebases."""

    id = peewee.CharField(max_length=32, primary_key=True)
    connector_id = peewee.CharField(max_length=32, null=False, index=True)
    kb_id = peewee.CharField(max_length=32, null=False, index=True)
    auto_parse = peewee.CharField(max_length=1, null=False, default="1")

    class Meta:
        table_name = "connector2kb"

    @classmethod
    def create_link(
        cls, connector_id: str, kb_id: str, auto_parse: str = "1"
    ) -> "Connector2Kb":
        """Create a link between a connector and a knowledge base."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            connector_id=connector_id,
            kb_id=kb_id,
            auto_parse=auto_parse,
        )


class SyncLogs(BaseModel):
    """Connector sync history log."""

    id = peewee.CharField(max_length=32, primary_key=True)
    connector_id = peewee.CharField(max_length=32, null=False, index=True)
    status = peewee.CharField(max_length=128, null=False, index=True)
    from_beginning = peewee.CharField(max_length=1, null=True, default="0")
    new_docs_indexed = peewee.IntegerField(null=False, default=0)
    total_docs_indexed = peewee.IntegerField(null=False, default=0)
    docs_removed_from_index = peewee.IntegerField(null=False, default=0)
    error_msg = peewee.TextField(null=True, default="")
    error_count = peewee.IntegerField(null=False, default=0)
    full_exception_trace = peewee.TextField(null=True)
    time_started = peewee.DateTimeField(null=True, index=True)
    poll_range_start = peewee.DateTimeField(null=True, index=True)
    poll_range_end = peewee.DateTimeField(null=True, index=True)
    kb_id = peewee.CharField(max_length=32, null=False, index=True)

    class Meta:
        table_name = "sync_logs"

    @classmethod
    def create_log(
        cls,
        connector_id: str,
        status: str,
        kb_id: str,
        from_beginning: str = "0",
        new_docs_indexed: int = 0,
        total_docs_indexed: int = 0,
        docs_removed_from_index: int = 0,
    ) -> "SyncLogs":
        """Create a sync log entry."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            connector_id=connector_id,
            status=status,
            from_beginning=from_beginning,
            new_docs_indexed=new_docs_indexed,
            total_docs_indexed=total_docs_indexed,
            docs_removed_from_index=docs_removed_from_index,
            error_msg="",
            error_count=0,
            full_exception_trace=None,
            time_started=None,
            poll_range_start=None,
            poll_range_end=None,
            kb_id=kb_id,
        )
