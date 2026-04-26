"""
Dialog (agent) configuration store.

Manages dialog/agent configurations stored in the database.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.models_peewee import Dialog, get_database

_log = logging.getLogger(__name__)


class DialogStore:
    """CRUD operations for dialogs (agents)."""

    def create_dialog(
        self,
        tenant_id: str,
        name: str,
        llm_id: str,
        created_by: str,
        **kwargs: Any,
    ) -> Dialog:
        """Create a new dialog (agent)."""
        with get_database().connection_context():
            dialog = Dialog.create_dialog(
                tenant_id=tenant_id,
                name=name,
                llm_id=llm_id,
                created_by=created_by,
                **kwargs,
            )
            _log.info("Created dialog %s (tenant %s)", dialog.id, tenant_id)
            return dialog

    def get_dialog(self, dialog_id: str) -> Dialog | None:
        """Get a dialog by ID."""
        with get_database().connection_context():
            try:
                return Dialog.get(Dialog.id == dialog_id)
            except Dialog.DoesNotExist:
                return None

    def list_dialogs(
        self,
        tenant_id: str | None = None,
        created_by: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List dialogs with optional filters."""
        with get_database().connection_context():
            query = Dialog.select()
            if tenant_id:
                query = query.where(Dialog.tenant_id == tenant_id)
            if created_by:
                query = query.where(Dialog.created_by == created_by)
            if status:
                query = query.where(Dialog.status == status)

            total = query.count()
            results = query.order_by(Dialog.create_time.desc()).limit(limit).offset(offset)
            return [d.to_dict() for d in results], total

    def update_dialog(
        self,
        dialog_id: str,
        **updates: Any,
    ) -> Dialog | None:
        """Update dialog fields."""
        with get_database().connection_context():
            try:
                dialog = Dialog.get(Dialog.id == dialog_id)
                for key, value in updates.items():
                    if hasattr(dialog, key):
                        setattr(dialog, key, value)
                # Update timestamp
                from datetime import datetime
                now = datetime.utcnow()
                dialog.update_date = now
                dialog.update_time = int(now.timestamp())
                dialog.save()
                _log.info("Updated dialog %s", dialog_id)
                return dialog
            except Dialog.DoesNotExist:
                return None

    def delete_dialog(self, dialog_id: str) -> bool:
        """Delete a dialog and its associated conversations."""
        from backend.models_peewee import Conversation

        with get_database().connection_context():
            try:
                dialog = Dialog.get(Dialog.id == dialog_id)
            except Dialog.DoesNotExist:
                return False

        # Delete conversations first (no FK constraint)
        with get_database().atomic():
            Conversation.delete().where(Conversation.dialog_id == dialog_id).execute()
            dialog.delete_instance()

        _log.info("Deleted dialog %s and its conversations", dialog_id)
        return True

    def get_dialog_by_name(
        self,
        tenant_id: str,
        name: str,
    ) -> Dialog | None:
        """Get a dialog by name within a tenant."""
        with get_database().connection_context():
            try:
                return Dialog.get(
                    (Dialog.tenant_id == tenant_id) & (Dialog.name == name)
                )
            except Dialog.DoesNotExist:
                return None


# Singleton
_dialog_store: DialogStore | None = None


def get_dialog_store() -> DialogStore:
    global _dialog_store
    if _dialog_store is None:
        _dialog_store = DialogStore()
    return _dialog_store
