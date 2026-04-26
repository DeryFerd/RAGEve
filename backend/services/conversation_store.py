"""
Conversation persistence layer using Peewee ORM.

Provides synchronous CRUD operations for the Conversation model,
designed to be called via run_db_operation() from async FastAPI routes.
"""

from __future__ import annotations

from typing import Any


from backend.models_peewee.dialog import Conversation
from backend.models_peewee import get_database


class ConversationStore:
    """Synchronous CRUD operations for conversations."""

    def create_conversation(
        self,
        dialog_id: str,
        name: str,
        messages: list[dict[str, Any]] | None = None,
        reference: list | None = None,
        user_id: str | None = None,
    ) -> Conversation:
        """Create a new conversation."""
        with get_database().connection_context():
            conv = Conversation.create_conversation(
                dialog_id=dialog_id,
                name=name,
                messages=messages or [],
                reference=reference or [],
                user_id=user_id,
            )
            return conv

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        with get_database().connection_context():
            try:
                return Conversation.get(Conversation.id == conversation_id)
            except Conversation.DoesNotExist:
                return None

    def list_conversations(
        self,
        dialog_id: str | None = None,
        user_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List conversations with optional filters. Returns (list, total_count)."""
        with get_database().connection_context():
            query = Conversation.select()

            if dialog_id:
                query = query.where(Conversation.dialog_id == dialog_id)
            if user_id:
                query = query.where(Conversation.user_id == user_id)

            total = query.count()
            # Order by creation time descending (most recent first)
            results = query.order_by(Conversation.create_time.desc()).limit(limit).offset(offset)

            convs = [conv.to_dict() for conv in results]
            return convs, total

    def update_conversation(self, conversation_id: str, **updates: Any) -> Conversation | None:
        """Update conversation fields (name, reference, user_id)."""
        with get_database().connection_context():
            try:
                conv = Conversation.get(Conversation.id == conversation_id)
            except Conversation.DoesNotExist:
                return None

            for field in ["name", "reference", "user_id"]:
                if field in updates:
                    setattr(conv, field, updates[field])
            conv.save()
            return conv

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation. Returns True if deleted."""
        with get_database().connection_context():
            try:
                conv = Conversation.get(Conversation.id == conversation_id)
                conv.delete_instance(recursive=True)
                return True
            except Conversation.DoesNotExist:
                return False

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        **extra_fields: Any,
    ) -> dict[str, Any] | None:
        """
        Append a message to the conversation's message JSON array.
        Extra fields (token_count, sources, etc.) are stored in the message object.
        Returns the appended message dict, or None if conversation not found.
        """
        with get_database().connection_context():
            try:
                conv = Conversation.get(Conversation.id == conversation_id)
            except Conversation.DoesNotExist:
                return None

            msg = conv.add_message(role=role, content=content, **extra_fields)
            return msg

    def get_conversation_context(
        self,
        conversation_id: str,
        max_turns: int = 6,
    ) -> list[dict[str, str]]:
        """
        Return conversation history as list of {"role": str, "content": str} dicts.
        Limits to last N turns (each turn = one user+assistant exchange).
        """
        with get_database().connection_context():
            try:
                conv = Conversation.get(Conversation.id == conversation_id)
            except Conversation.DoesNotExist:
                return []

            messages = conv.get_messages(max_turns=max_turns)
            # Return only role and content for LLM context
            return [{"role": m["role"], "content": m["content"]} for m in messages]


# Singleton accessor
_conversation_store: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = ConversationStore()
    return _conversation_store
