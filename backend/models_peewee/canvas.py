"""
Agent workflow canvas models.

Tables:
- UserCanvas: User-created agent workflows
- CanvasTemplate: Pre-built workflow templates
"""

from __future__ import annotations

import uuid
from typing import Optional

import peewee
from .base import BaseModel, JSONTextField


class UserCanvas(BaseModel):
    """Agent workflow canvas created by users."""
    id = peewee.CharField(max_length=32, primary_key=True)
    user_id = peewee.CharField(max_length=255, null=False, index=True)
    title = peewee.CharField(max_length=255, null=True)
    permission = peewee.CharField(max_length=16, null=False, default="me", index=True)
    description = peewee.TextField(null=True)
    canvas_type = peewee.CharField(max_length=32, null=True, index=True)
    canvas_category = peewee.CharField(max_length=32, null=False, default="agent_canvas", index=True)
    dsl = JSONTextField(null=True, default={})  # Workflow definition

    class Meta:
        table_name = "user_canvas"

    @classmethod
    def create_canvas(
        cls,
        user_id: str,
        title: Optional[str] = None,
        permission: str = "me",
        description: Optional[str] = None,
        canvas_type: Optional[str] = None,
        canvas_category: str = "agent_canvas",
        dsl: Optional[dict] = None,
    ) -> "UserCanvas":
        """Create a new user canvas."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            user_id=user_id,
            title=title,
            permission=permission,
            description=description,
            canvas_type=canvas_type,
            canvas_category=canvas_category,
            dsl=dsl or {},
        )


class CanvasTemplate(BaseModel):
    """Pre-built workflow templates."""
    id = peewee.CharField(max_length=32, primary_key=True)
    title = JSONTextField(null=True, default=dict)
    description = JSONTextField(null=True, default=dict)
    canvas_type = peewee.CharField(max_length=32, null=True, index=True)
    canvas_category = peewee.CharField(max_length=32, null=False, default="agent_canvas", index=True)
    dsl = JSONTextField(null=True, default={})

    class Meta:
        table_name = "canvas_template"

    @classmethod
    def create_template(
        cls,
        title: Optional[dict] = None,
        description: Optional[dict] = None,
        canvas_type: Optional[str] = None,
        canvas_category: str = "agent_canvas",
        dsl: Optional[dict] = None,
    ) -> "CanvasTemplate":
        """Create a new canvas template."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            title=title or {},
            description=description or {},
            canvas_type=canvas_type,
            canvas_category=canvas_category,
            dsl=dsl or {},
        )
