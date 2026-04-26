"""
Canvas store for agent workflow management.

Manages user canvases and canvas templates.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.models_peewee import (
    UserCanvas,
    CanvasTemplate,
    get_database,
)

_log = logging.getLogger(__name__)


class CanvasStore:
    """CRUD operations for canvases and templates."""

    # ==================== User Canvases ====================

    def create_canvas(
        self,
        user_id: str,
        title: str | None = None,
        permission: str = "me",
        description: str | None = None,
        canvas_type: str | None = None,
        canvas_category: str = "agent_canvas",
        dsl: dict | None = None,
    ) -> UserCanvas:
        """Create a new user canvas."""
        with get_database().connection_context():
            canvas = UserCanvas.create_canvas(
                user_id=user_id,
                title=title,
                permission=permission,
                description=description,
                canvas_type=canvas_type,
                canvas_category=canvas_category,
                dsl=dsl or {},
            )
            _log.info("Created canvas %s for user %s", canvas.id, user_id)
            return canvas

    def get_canvas(self, canvas_id: str) -> UserCanvas | None:
        """Get a canvas by ID."""
        with get_database().connection_context():
            try:
                return UserCanvas.get(UserCanvas.id == canvas_id)
            except UserCanvas.DoesNotExist:
                return None

    def list_user_canvases(
        self,
        user_id: str | None = None,
        canvas_category: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List canvases, optionally filtered by user or category."""
        with get_database().connection_context():
            query = UserCanvas.select()
            if user_id:
                query = query.where(UserCanvas.user_id == user_id)
            if canvas_category:
                query = query.where(UserCanvas.canvas_category == canvas_category)
            query = query.order_by(UserCanvas.create_time.desc()).limit(limit)
            return [c.to_dict() for c in query]

    def update_canvas(self, canvas_id: str, **updates: Any) -> UserCanvas | None:
        """Update a canvas."""
        with get_database().connection_context():
            try:
                canvas = UserCanvas.get(UserCanvas.id == canvas_id)
                for key, value in updates.items():
                    if hasattr(canvas, key):
                        setattr(canvas, key, value)
                canvas.save()
                _log.info("Updated canvas %s", canvas_id)
                return canvas
            except UserCanvas.DoesNotExist:
                return None

    def delete_canvas(self, canvas_id: str) -> bool:
        """Delete a canvas."""
        with get_database().connection_context():
            try:
                canvas = UserCanvas.get(UserCanvas.id == canvas_id)
                canvas.delete_instance()
                _log.info("Deleted canvas %s", canvas_id)
                return True
            except UserCanvas.DoesNotExist:
                return False

    # ==================== Canvas Templates ====================

    def create_template(
        self,
        title: dict | None = None,
        description: dict | None = None,
        canvas_type: str | None = None,
        canvas_category: str = "agent_canvas",
        dsl: dict | None = None,
    ) -> CanvasTemplate:
        """Create a new canvas template."""
        with get_database().connection_context():
            template = CanvasTemplate.create_template(
                title=title or {},
                description=description or {},
                canvas_type=canvas_type,
                canvas_category=canvas_category,
                dsl=dsl or {},
            )
            _log.info("Created canvas template %s", template.id)
            return template

    def get_template(self, template_id: str) -> CanvasTemplate | None:
        """Get a template by ID."""
        with get_database().connection_context():
            try:
                return CanvasTemplate.get(CanvasTemplate.id == template_id)
            except CanvasTemplate.DoesNotExist:
                return None

    def list_templates(
        self,
        canvas_category: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List canvas templates with optional filter."""
        with get_database().connection_context():
            query = CanvasTemplate.select()
            if canvas_category:
                query = query.where(CanvasTemplate.canvas_category == canvas_category)
            query = query.order_by(CanvasTemplate.create_time.desc()).limit(limit)
            return [t.to_dict() for t in query]

    def update_template(self, template_id: str, **updates: Any) -> CanvasTemplate | None:
        """Update a template."""
        with get_database().connection_context():
            try:
                template = CanvasTemplate.get(CanvasTemplate.id == template_id)
                for key, value in updates.items():
                    if hasattr(template, key):
                        setattr(template, key, value)
                template.save()
                _log.info("Updated canvas template %s", template_id)
                return template
            except CanvasTemplate.DoesNotExist:
                return None

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        with get_database().connection_context():
            try:
                template = CanvasTemplate.get(CanvasTemplate.id == template_id)
                template.delete_instance()
                _log.info("Deleted canvas template %s", template_id)
                return True
            except CanvasTemplate.DoesNotExist:
                return False


# Singleton
_canvas_store: CanvasStore | None = None


def get_canvas_store() -> CanvasStore:
    global _canvas_store
    if _canvas_store is None:
        _canvas_store = CanvasStore()
    return _canvas_store
