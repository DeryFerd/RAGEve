"""
Connector store for external data source management.

Manages connectors, their mappings to knowledgebases, and sync logs.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.models_peewee import (
    Connector,
    Connector2Kb,
    Knowledgebase,
    SyncLogs,
    get_database,
)

_log = logging.getLogger(__name__)


class ConnectorStore:
    """CRUD operations for connectors and sync logs."""

    # ==================== Connectors ====================

    def create_connector(
        self,
        tenant_id: str,
        name: str,
        source: str,
        input_type: str,
        config: dict | None = None,
        refresh_freq: int = 0,
        prune_freq: int = 0,
        timeout_secs: int = 3600,
        status: str = "schedule",
    ) -> Connector:
        """Create a new connector."""
        with get_database().connection_context():
            c = Connector.create_connector(
                tenant_id=tenant_id,
                name=name,
                source=source,
                input_type=input_type,
                config=config or {},
                refresh_freq=refresh_freq,
                prune_freq=prune_freq,
                timeout_secs=timeout_secs,
                status=status,
            )
            _log.info("Created connector %s for tenant %s", c.id, tenant_id)
            return c

    def get_connector(self, connector_id: str) -> Connector | None:
        """Get a connector by ID."""
        with get_database().connection_context():
            try:
                return Connector.get(Connector.id == connector_id)
            except Connector.DoesNotExist:
                return None

    def list_connectors(
        self,
        tenant_id: str | None = None,
        source: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """List connectors with optional filters."""
        with get_database().connection_context():
            query = Connector.select()
            if tenant_id:
                query = query.where(Connector.tenant_id == tenant_id)
            if source:
                query = query.where(Connector.source == source)
            if status:
                query = query.where(Connector.status == status)
            query = query.order_by(Connector.create_time.desc())
            return [c.to_dict() for c in query]

    def update_connector(self, connector_id: str, **updates: Any) -> Connector | None:
        """Update a connector."""
        with get_database().connection_context():
            try:
                c = Connector.get(Connector.id == connector_id)
                for key, value in updates.items():
                    if hasattr(c, key):
                        setattr(c, key, value)
                c.save()
                _log.info("Updated connector %s", connector_id)
                return c
            except Connector.DoesNotExist:
                return None

    def delete_connector(self, connector_id: str) -> bool:
        """Delete a connector."""
        with get_database().connection_context():
            try:
                c = Connector.get(Connector.id == connector_id)
                c.delete_instance(recursive=True)  # cascade to mappings and sync logs?
                _log.info("Deleted connector %s", connector_id)
                return True
            except Connector.DoesNotExist:
                return False

    # ==================== Connector-Knowledgebase Mappings ====================

    def link_connector_to_kb(
        self,
        connector_id: str,
        kb_id: str,
        auto_parse: str = "1",
    ) -> Connector2Kb:
        """Link a connector to a knowledgebase."""
        with get_database().connection_context():
            # Check if exists
            try:
                link = Connector2Kb.get(
                    (Connector2Kb.connector_id == connector_id)
                    & (Connector2Kb.kb_id == kb_id)
                )
                link.auto_parse = auto_parse
                link.save()
                return link
            except Connector2Kb.DoesNotExist:
                link = Connector2Kb.create_link(
                    connector_id=connector_id,
                    kb_id=kb_id,
                    auto_parse=auto_parse,
                )
                _log.info(
                    "Linked connector %s to knowledgebase %s", connector_id, kb_id
                )
                return link

    def get_knowledgebases_for_connector(
        self, connector_id: str
    ) -> list[Knowledgebase]:
        """Get all knowledgebases linked to a connector."""
        with get_database().connection_context():
            query = (
                Knowledgebase.select()
                .join(Connector2Kb, on=(Knowledgebase.id == Connector2Kb.kb_id))
                .where(Connector2Kb.connector_id == connector_id)
            )
            return list(query)

    def unlink_connector_from_kb(self, connector_id: str, kb_id: str) -> bool:
        """Remove link between connector and knowledgebase."""
        with get_database().connection_context():
            try:
                link = Connector2Kb.get(
                    (Connector2Kb.connector_id == connector_id)
                    & (Connector2Kb.kb_id == kb_id)
                )
                link.delete_instance()
                _log.info(
                    "Unlinked connector %s from knowledgebase %s", connector_id, kb_id
                )
                return True
            except Connector2Kb.DoesNotExist:
                return False

    # ==================== Sync Logs ====================

    def create_sync_log(
        self,
        connector_id: str,
        status: str,
        kb_id: str,
        from_beginning: str = "0",
        new_docs_indexed: int = 0,
        total_docs_indexed: int = 0,
        docs_removed_from_index: int = 0,
    ) -> SyncLogs:
        """Create a sync log entry."""
        with get_database().connection_context():
            log = SyncLogs.create_log(
                connector_id=connector_id,
                status=status,
                kb_id=kb_id,
                from_beginning=from_beginning,
                new_docs_indexed=new_docs_indexed,
                total_docs_indexed=total_docs_indexed,
                docs_removed_from_index=docs_removed_from_index,
            )
            return log

    def update_sync_log(
        self,
        log_id: str,
        **updates: Any,
    ) -> SyncLogs | None:
        """Update sync log (e.g., set completion time, error info)."""
        with get_database().connection_context():
            try:
                log = SyncLogs.get(SyncLogs.id == log_id)
                for key, value in updates.items():
                    if hasattr(log, key):
                        setattr(log, key, value)
                log.save()
                return log
            except SyncLogs.DoesNotExist:
                return None

    def get_sync_logs(
        self,
        connector_id: str | None = None,
        kb_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get sync logs with filters."""
        with get_database().connection_context():
            query = SyncLogs.select()
            if connector_id:
                query = query.where(SyncLogs.connector_id == connector_id)
            if kb_id:
                query = query.where(SyncLogs.kb_id == kb_id)
            if status:
                query = query.where(SyncLogs.status == status)
            query = query.order_by(SyncLogs.create_time.desc()).limit(limit)
            return [l.to_dict() for l in query]


# Singleton
_connector_store: ConnectorStore | None = None


def get_connector_store() -> ConnectorStore:
    global _connector_store
    if _connector_store is None:
        _connector_store = ConnectorStore()
    return _connector_store
