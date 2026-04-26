"""
Knowledge base and document management models.

Tables:
- Knowledgebase: Collection of documents (dataset)
- Document: Document metadata and processing state
- File: Uploaded file metadata
- File2Document: Many-to-many link between files and documents
- Task: Asynchronous processing task for document chunking/embedding
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import peewee
from .base import BaseModel, JSONTextField, ListField


class Knowledgebase(BaseModel):
    """Knowledge base - a collection of documents."""
    id = peewee.CharField(max_length=32, primary_key=True)
    tenant_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=255, null=False, index=True)
    description = peewee.TextField(null=True)
    avatar = peewee.TextField(null=True, help_text="Base64 encoded avatar")
    parser_ids = peewee.TextField(null=False, help_text="Comma-separated parser IDs")
    language = peewee.CharField(max_length=32, null=True, default="English", index=True)
    created_by = peewee.CharField(max_length=32, null=False, index=True)
    pagerank = peewee.IntegerField(null=False, default=0)
    pipeline_id = peewee.CharField(max_length=32, null=True, index=True, help_text="Pipeline configuration ID")
    graphrag_task_id = peewee.CharField(max_length=32, null=True, index=True)
    raptor_task_id = peewee.CharField(max_length=32, null=True, index=True)
    mindmap_task_id = peewee.CharField(max_length=32, null=True, index=True)

    class Meta:
        table_name = "knowledgebase"

    @classmethod
    def create_kb(
        cls,
        tenant_id: str,
        name: str,
        created_by: str,
        description: Optional[str] = None,
        avatar: Optional[str] = None,
        parser_ids: str = "",  # e.g., "pdf,docx"
        language: str = "English",
        pagerank: int = 0,
        pipeline_id: Optional[str] = None,
        id: Optional[str] = None,
    ) -> "Knowledgebase":
        """Create a new knowledge base."""
        if id is None:
            id = str(uuid.uuid4()).replace("-", "")[:32]
        now = datetime.utcnow()
        return cls.create(
            id=id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            avatar=avatar,
            parser_ids=parser_ids,
            language=language,
            created_by=created_by,
            pagerank=pagerank,
            pipeline_id=pipeline_id,
            graphrag_task_id=None,
            raptor_task_id=None,
            mindmap_task_id=None,
            create_date=now,
            create_time=int(now.timestamp()),
            update_date=now,
            update_time=int(now.timestamp()),
        )


class Document(BaseModel):
    """Document metadata - represents a processed document within a knowledge base."""
    id = peewee.CharField(max_length=32, primary_key=True)
    kb_id = peewee.CharField(max_length=32, null=False, index=True)
    name = peewee.CharField(max_length=255, null=False)
    parser_id = peewee.CharField(max_length=32, null=False)
    created_by = peewee.CharField(max_length=32, null=False, index=True)
    progress = peewee.FloatField(null=False, default=0, index=True)
    progress_msg = peewee.TextField(null=True, default="")
    process_duation = peewee.FloatField(null=False, default=0, help_text="Processing time in seconds")
    doc_type = peewee.CharField(max_length=32, null=True, help_text="Document type")
    doc_metadata = JSONTextField(null=True, default={}, help_text="Document metadata")
    meta_fields = JSONTextField(null=True, default={})
    thumbnail = peewee.TextField(null=True, help_text="Thumbnail base64")
    pipeline_id = peewee.CharField(max_length=32, null=True, index=True)

    class Meta:
        table_name = "document"

    @classmethod
    def create_document(
        cls,
        kb_id: str,
        name: str,
        parser_id: str,
        created_by: str,
        doc_type: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        id: Optional[str] = None,
    ) -> "Document":
        """Create a new document record."""
        if id is None:
            id = str(uuid.uuid4()).replace("-", "")[:32]
        now = datetime.utcnow()
        return cls.create(
            id=id,
            kb_id=kb_id,
            name=name,
            parser_id=parser_id,
            created_by=created_by,
            progress=0,
            progress_msg="",
            process_duation=0,
            doc_type=doc_type,
            doc_metadata={},
            meta_fields={},
            thumbnail=None,
            pipeline_id=pipeline_id,
            create_date=now,
            create_time=int(now.timestamp()),
            update_date=now,
            update_time=int(now.timestamp()),
        )


class File(BaseModel):
    """Uploaded file metadata."""
    id = peewee.CharField(max_length=32, primary_key=True)
    name = peewee.CharField(max_length=255, null=False)
    size = peewee.BigIntegerField(null=False, default=0)
    type = peewee.CharField(max_length=32, null=False, help_text="File type: pdf, doc, visual, etc.")
    source_type = peewee.CharField(max_length=128, null=False, default="", index=True, help_text="Source: upload, connector, etc.")
    created_by = peewee.CharField(max_length=32, null=False, index=True)

    class Meta:
        table_name = "file"

    @classmethod
    def create_file(
        cls,
        name: str,
        size: int,
        file_type: str,
        created_by: str,
        source_type: str = "upload",
    ) -> "File":
        """Create a new file record."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            name=name,
            size=size,
            type=file_type,
            source_type=source_type,
            created_by=created_by,
        )


class File2Document(BaseModel):
    """Many-to-many mapping between files and documents."""
    id = peewee.CharField(max_length=32, primary_key=True)
    file_id = peewee.CharField(max_length=32, null=False, index=True)
    doc_id = peewee.CharField(max_length=32, null=False, index=True)

    class Meta:
        table_name = "file2document"

    @classmethod
    def create_link(cls, file_id: str, doc_id: str) -> "File2Document":
        """Create a link between a file and a document."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            file_id=file_id,
            doc_id=doc_id,
        )


class Task(BaseModel):
    """Asynchronous processing task for document ingestion."""
    id = peewee.CharField(max_length=32, primary_key=True)
    doc_id = peewee.CharField(max_length=32, null=False, index=True)
    from_page = peewee.IntegerField(null=False, default=0)
    to_page = peewee.IntegerField(null=False, default=100000000)
    task_type = peewee.CharField(max_length=32, null=False, default="")
    priority = peewee.IntegerField(null=False, default=0)
    begin_at = peewee.DateTimeField(null=True, index=True)
    process_duation = peewee.FloatField(null=False, default=0)
    progress = peewee.FloatField(null=False, default=0, index=True)
    progress_msg = peewee.TextField(null=True, default="")
    retry_count = peewee.IntegerField(null=False, default=0)
    digest = peewee.TextField(null=True, default="")
    chunk_ids = peewee.TextField(null=True, default="")

    class Meta:
        table_name = "task"

    @classmethod
    def create_task(
        cls,
        doc_id: str,
        task_type: str,
        from_page: int = 0,
        to_page: int = 100000000,
        priority: int = 0,
    ) -> "Task":
        """Create a new processing task."""
        return cls.create(
            id=str(uuid.uuid4()).replace("-", "")[:32],
            doc_id=doc_id,
            from_page=from_page,
            to_page=to_page,
            task_type=task_type,
            priority=priority,
            begin_at=None,
            process_duation=0,
            progress=0,
            progress_msg="",
            retry_count=0,
            digest="",
            chunk_ids="",
        )

    def start(self):
        """Mark task as started."""
        from datetime import datetime
        self.begin_at = datetime.now()
        self.save()

    def complete(self, duration: float):
        """Mark task as completed."""
        self.process_duation = duration
        self.progress = 100
        self.save()

    def update_progress(self, progress: float, msg: str = ""):
        """Update task progress."""
        self.progress = progress
        if msg:
            self.progress_msg = msg
        self.save()
