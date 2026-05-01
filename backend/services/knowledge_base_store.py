"""
Knowledge base and document management service.

Manages the lifecycle of knowledgebases, documents, files, and processing tasks.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.models_peewee import (
    Document,
    File,
    File2Document,
    Knowledgebase,
    Task,
    get_database,
)

_log = logging.getLogger(__name__)


class KnowledgeBaseStore:
    """CRUD operations for knowledgebases and related entities."""

    # ==================== Knowledgebases ====================

    def create_knowledgebase(
        self,
        tenant_id: str,
        name: str,
        created_by: str,
        description: str | None = None,
        avatar: str | None = None,
        parser_ids: str = "",
        language: str = "English",
        pagerank: int = 0,
        pipeline_id: str | None = None,
        kb_id: str | None = None,
    ) -> Knowledgebase:
        """Create a new knowledge base."""
        with get_database().connection_context():
            kb = Knowledgebase.create_kb(
                tenant_id=tenant_id,
                name=name,
                created_by=created_by,
                description=description,
                avatar=avatar,
                parser_ids=parser_ids,
                language=language,
                pagerank=pagerank,
                pipeline_id=pipeline_id,
                id=kb_id,
            )
            _log.info("Created knowledgebase %s (tenant %s)", kb.id, tenant_id)
            return kb

    def get_knowledgebase(self, kb_id: str) -> Knowledgebase | None:
        """Get a knowledgebase by ID."""
        with get_database().connection_context():
            try:
                return Knowledgebase.get(Knowledgebase.id == kb_id)
            except Knowledgebase.DoesNotExist:
                return None

    def list_knowledgebases(
        self,
        tenant_id: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List knowledgebases with optional filters."""
        with get_database().connection_context():
            query = Knowledgebase.select()
            if tenant_id:
                query = query.where(Knowledgebase.tenant_id == tenant_id)
            if created_by:
                query = query.where(Knowledgebase.created_by == created_by)

            total = query.count()
            results = (
                query.order_by(Knowledgebase.create_time.desc())
                .limit(limit)
                .offset(offset)
            )
            return [kb.to_dict() for kb in results], total

    def update_knowledgebase(
        self,
        kb_id: str,
        **updates: Any,
    ) -> Knowledgebase | None:
        """Update knowledgebase fields."""
        with get_database().connection_context():
            try:
                kb = Knowledgebase.get(Knowledgebase.id == kb_id)
                for key, value in updates.items():
                    if hasattr(kb, key):
                        setattr(kb, key, value)
                # Update timestamp
                from datetime import datetime

                now = datetime.utcnow()
                kb.update_date = now
                kb.update_time = int(now.timestamp())
                kb.save()
                _log.info("Updated knowledgebase %s", kb_id)
                return kb
            except Knowledgebase.DoesNotExist:
                return None

    def delete_knowledgebase(self, kb_id: str) -> bool:
        """Delete a knowledgebase and cascade to documents, files, and tasks."""
        with get_database().connection_context():
            try:
                kb = Knowledgebase.get(Knowledgebase.id == kb_id)
            except Knowledgebase.DoesNotExist:
                return False

        # Delete in transaction
        with get_database().atomic():
            # Get all documents for this KB
            docs = Document.select().where(Document.kb_id == kb_id)
            doc_ids = [d.id for d in docs]
            if doc_ids:
                # Delete tasks for these documents
                Task.delete().where(Task.doc_id.in_(doc_ids)).execute()
                # Delete file-document links for these documents
                File2Document.delete().where(
                    File2Document.doc_id.in_(doc_ids)
                ).execute()
                # Delete documents
                Document.delete().where(Document.id.in_(doc_ids)).execute()
            # Delete the knowledgebase
            kb.delete_instance()

        _log.info(
            "Deleted knowledgebase %s (including %d documents)", kb_id, len(doc_ids)
        )
        return True

    # ==================== Documents ====================

    def create_document(
        self,
        kb_id: str,
        name: str,
        parser_id: str,
        created_by: str,
        doc_type: str | None = None,
        pipeline_id: str | None = None,
        doc_id: str | None = None,
    ) -> Document:
        """Create a new document record within a knowledgebase."""
        with get_database().connection_context():
            doc = Document.create_document(
                kb_id=kb_id,
                name=name,
                parser_id=parser_id,
                created_by=created_by,
                doc_type=doc_type,
                pipeline_id=pipeline_id,
                id=doc_id,
            )
            _log.info("Created document %s in knowledgebase %s", doc.id, kb_id)
            return doc

    def get_document(self, doc_id: str) -> Document | None:
        """Get a document by ID."""
        with get_database().connection_context():
            try:
                return Document.get(Document.id == doc_id)
            except Document.DoesNotExist:
                return None

    def list_documents(
        self,
        kb_id: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List documents with optional filters."""
        with get_database().connection_context():
            query = Document.select()
            if kb_id:
                query = query.where(Document.kb_id == kb_id)
            if created_by:
                query = query.where(Document.created_by == created_by)

            total = query.count()
            results = (
                query.order_by(Document.create_time.desc()).limit(limit).offset(offset)
            )
            return [doc.to_dict() for doc in results], total

    def update_document_progress(
        self,
        doc_id: str,
        progress: float,
        progress_msg: str | None = None,
        doc_metadata: dict | None = None,
    ) -> Document | None:
        """Update document processing progress."""
        with get_database().connection_context():
            try:
                doc = Document.get(Document.id == doc_id)
                doc.progress = progress
                if progress_msg is not None:
                    doc.progress_msg = progress_msg
                if doc_metadata is not None:
                    doc.doc_metadata = doc_metadata
                # Update timestamp
                from datetime import datetime

                now = datetime.utcnow()
                doc.update_date = now
                doc.update_time = int(now.timestamp())
                doc.save()
                _log.debug("Updated document %s progress to %.1f%%", doc_id, progress)
                return doc
            except Document.DoesNotExist:
                return None

    def complete_document(
        self,
        doc_id: str,
        duration: float,
        doc_metadata: dict | None = None,
    ) -> Document | None:
        """Mark document processing as complete."""
        with get_database().connection_context():
            try:
                doc = Document.get(Document.id == doc_id)
                doc.process_duration = duration
                doc.progress = 100.0
                if doc_metadata:
                    doc.doc_metadata = doc_metadata
                # Update timestamp
                from datetime import datetime

                now = datetime.utcnow()
                doc.update_date = now
                doc.update_time = int(now.timestamp())
                doc.save()
                _log.info("Completed document %s (duration: %.2fs)", doc_id, duration)
                return doc
            except Document.DoesNotExist:
                return None

    # ==================== Files ====================

    def create_file(
        self,
        name: str,
        size: int,
        file_type: str,
        created_by: str,
        source_type: str = "upload",
    ) -> File:
        """Create a new file record."""
        with get_database().connection_context():
            file = File.create_file(
                name=name,
                size=size,
                file_type=file_type,
                created_by=created_by,
                source_type=source_type,
            )
            _log.info("Created file %s (type: %s, size: %d)", file.id, file_type, size)
            return file

    def get_file(self, file_id: str) -> File | None:
        """Get a file by ID."""
        with get_database().connection_context():
            try:
                return File.get(File.id == file_id)
            except File.DoesNotExist:
                return None

    # ==================== File-Document Links ====================

    def link_file_to_document(self, file_id: str, doc_id: str) -> File2Document:
        """Create a link between a file and a document."""
        with get_database().connection_context():
            link = File2Document.create_link(file_id=file_id, doc_id=doc_id)
            _log.debug("Linked file %s to document %s", file_id, doc_id)
            return link

    def get_documents_for_file(self, file_id: str) -> list[Document]:
        """Get all documents linked to a file."""
        with get_database().connection_context():
            query = (
                Document.select()
                .join(File2Document, on=(Document.id == File2Document.doc_id))
                .where(File2Document.file_id == file_id)
            )
            return list(query)

    # ==================== Tasks ====================

    def create_task(
        self,
        doc_id: str,
        task_type: str,
        from_page: int = 0,
        to_page: int = 100000000,
        priority: int = 0,
    ) -> Task:
        """Create a new processing task for a document."""
        with get_database().connection_context():
            task = Task.create_task(
                doc_id=doc_id,
                task_type=task_type,
                from_page=from_page,
                to_page=to_page,
                priority=priority,
            )
            _log.info(
                "Created task %s (type: %s) for document %s", task.id, task_type, doc_id
            )
            return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        with get_database().connection_context():
            try:
                return Task.get(Task.id == task_id)
            except Task.DoesNotExist:
                return None

    def update_task_progress(
        self,
        task_id: str,
        progress: float,
        msg: str | None = None,
    ) -> Task | None:
        """Update task progress."""
        with get_database().connection_context():
            try:
                task = Task.get(Task.id == task_id)
                task.update_progress(progress, msg)
                return task
            except Task.DoesNotExist:
                return None

    def start_task(self, task_id: str) -> Task | None:
        """Mark task as started."""
        with get_database().connection_context():
            try:
                task = Task.get(Task.id == task_id)
                task.start()
                return task
            except Task.DoesNotExist:
                return None

    def complete_task(self, task_id: str, duration: float) -> Task | None:
        """Mark task as completed."""
        with get_database().connection_context():
            try:
                task = Task.get(Task.id == task_id)
                task.complete(duration)
                return task
            except Task.DoesNotExist:
                return None

    def get_document_tasks(self, doc_id: str) -> list[Task]:
        """Get all tasks for a document."""
        with get_database().connection_context():
            query = (
                Task.select()
                .where(Task.doc_id == doc_id)
                .order_by(Task.create_time.asc())
            )
            return list(query)


# Singleton
_kb_store: KnowledgeBaseStore | None = None


def get_knowledge_base_store() -> KnowledgeBaseStore:
    global _kb_store
    if _kb_store is None:
        _kb_store = KnowledgeBaseStore()
    return _kb_store
