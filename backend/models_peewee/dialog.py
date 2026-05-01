"""
Dialog (agent) and conversation models.

Tables:
- Dialog: Chatbot/assistant configuration (replaces RAGEve's agents)
- Conversation: Chat conversation history with messages stored as JSON array
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import peewee

from .base import BaseModel, JSONTextField, ListField


class Dialog(BaseModel):
    """Chatbot/assistant configuration.

    This replaces RAGEve's JSON file-based agents.
    """

    id = peewee.CharField(max_length=32, primary_key=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=255, null=True, index=True)
    description = peewee.TextField(null=True)
    language = peewee.CharField(max_length=32, null=True, default="English", index=True)
    llm_id = peewee.CharField(max_length=128, null=False, help_text="Default LLM ID")
    llm_setting = JSONTextField(
        null=False,
        default=lambda: {
            "temperature": 0.1,
            "top_p": 0.3,
            "frequency_penalty": 0.7,
            "presence_penalty": 0.4,
            "max_tokens": 512,
        },
    )
    prompt_type = peewee.CharField(
        max_length=16, null=False, default="simple", index=True
    )
    prompt_config = JSONTextField(
        null=False,
        default=lambda: {
            "system": "",
            "prologue": "Hi! I'm your assistant. What can I do for you?",
            "parameters": [],
            "empty_response": "Sorry! No relevant content was found in the knowledge base!",
        },
    )
    meta_data_filter = JSONTextField(null=True, default=dict)
    similarity_threshold = peewee.FloatField(null=False, default=0.2)
    vector_similarity_weight = peewee.FloatField(null=False, default=0.3)
    top_n = peewee.IntegerField(null=False, default=6)
    top_k = peewee.IntegerField(null=False, default=1024)
    do_refer = peewee.CharField(
        max_length=1, null=False, default="1", help_text="Include references (1=yes)"
    )
    rerank_id = peewee.CharField(max_length=128, null=False, default="")
    kb_ids = ListField(null=False, default=list)
    status = peewee.CharField(max_length=1, null=True, default="1", index=True)

    class Meta:
        table_name = "dialog"

    @classmethod
    def create_dialog(
        cls,
        tenant_id: str,
        name: str,
        llm_id: str,
        created_by: str,
        description: Optional[str] = None,
        language: str = "English",
        llm_setting: Optional[dict] = None,
        prompt_type: str = "simple",
        prompt_config: Optional[dict] = None,
        meta_data_filter: Optional[dict] = None,
        kb_ids: Optional[list[str]] = None,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        top_n: int = 6,
        top_k: int = 1024,
        do_refer: str = "1",
        rerank_id: str = "",
        status: str = "1",
    ) -> "Dialog":
        """Create a new dialog (agent)."""
        now = datetime.utcnow()
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            tenant_id=tenant_id,
            name=name,
            description=description,
            language=language,
            llm_id=llm_id,
            llm_setting=llm_setting
            or {
                "temperature": 0.1,
                "top_p": 0.3,
                "frequency_penalty": 0.7,
                "presence_penalty": 0.4,
                "max_tokens": 512,
            },
            prompt_type=prompt_type,
            prompt_config=prompt_config
            or {
                "system": "",
                "prologue": "Hi! I'm your assistant. What can I do for you?",
                "parameters": [],
                "empty_response": "Sorry! No relevant content was found in the knowledge base!",
            },
            meta_data_filter=meta_data_filter or {},
            similarity_threshold=similarity_threshold,
            vector_similarity_weight=vector_similarity_weight,
            top_n=top_n,
            top_k=top_k,
            do_refer=do_refer,
            rerank_id=rerank_id,
            kb_ids=kb_ids or [],
            status=status,
            create_date=now,
            create_time=int(now.timestamp()),
            update_date=now,
            update_time=int(now.timestamp()),
        )


class Conversation(BaseModel):
    """Chat conversation history.

    Messages are stored as a JSON array in the `message` field.
    Each message object should have: {"role": "user"|"assistant"|"system", "content": "..."}
    """

    id = peewee.CharField(max_length=32, primary_key=True)
    dialog_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=255, null=True, index=True)
    message = JSONTextField(
        null=True
    )  # Array of message objects: [{"role": "...", "content": "...", ...}, ...]
    reference = JSONTextField(null=True, default=[])
    user_id = peewee.CharField(max_length=255, null=True, index=True)

    class Meta:
        table_name = "conversation"

    @classmethod
    def create_conversation(
        cls,
        dialog_id: str,
        name: Optional[str] = None,
        messages: Optional[list[dict]] = None,
        reference: Optional[list] = None,
        user_id: Optional[str] = None,
    ) -> "Conversation":
        """Create a new conversation."""
        now = datetime.utcnow()
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            dialog_id=dialog_id,
            name=name or "New conversation",
            message=messages or [],
            reference=reference or [],
            user_id=user_id,
            create_date=now,
            create_time=int(now.timestamp()),
            update_date=now,
            update_time=int(now.timestamp()),
        )

    def add_message(self, role: str, content: str, **extra_fields):
        """Append a message to the conversation.

        Args:
            role: "user", "assistant", or "system"
            content: Message content
            **extra_fields: Additional fields to include in message object (e.g., sources, token_count)
        Returns:
            The appended message dict with a generated message_id.
        """
        if not self.message:
            self.message = []
        msg = {"role": role, "content": content, **extra_fields}
        # Generate a unique message ID for this message
        msg_id = f"msg_{uuid.uuid4().hex[:16]}"
        msg["message_id"] = msg_id
        self.message.append(msg)
        # Update timestamps
        now = datetime.utcnow()
        self.update_date = now
        self.update_time = int(now.timestamp())
        self.save()
        return msg

    def get_messages(self, max_turns: Optional[int] = None) -> list[dict]:
        """Get messages from conversation.

        Args:
            max_turns: If set, return only the last N turns (1 turn = user+assistant pair).
                      Does not truncate if max_turns is None.
        Returns:
            List of message dictionaries.
        """
        msgs = self.message or []
        if max_turns and len(msgs) > max_turns * 2:
            msgs = msgs[-(max_turns * 2) :]
        return msgs
