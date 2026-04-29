from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KnowledgebaseCreate(BaseModel):
    tenant_id: str = Field(..., min_length=32, max_length=32)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    avatar: Optional[str] = Field(default=None)
    parser_ids: str = Field(
        default="", description="Comma-separated parser IDs, e.g., 'pdf,docx'"
    )
    language: str = Field(default="English", max_length=32)
    created_by: str = Field(..., min_length=32, max_length=32)
    pagerank: int = Field(default=0, ge=0)
    pipeline_id: Optional[str] = Field(default=None, max_length=32)


class KnowledgebaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    avatar: Optional[str] = None
    parser_ids: Optional[str] = None
    language: Optional[str] = Field(default=None, max_length=32)
    pagerank: Optional[int] = Field(default=None, ge=0)
    pipeline_id: Optional[str] = Field(default=None, max_length=32)


class KnowledgebaseResponse(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    tenant_id: str = Field(..., min_length=32, max_length=32)
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    parser_ids: str
    language: Optional[str] = None
    created_by: str = Field(..., min_length=32, max_length=32)
    pagerank: int
    pipeline_id: Optional[str] = None
    graphrag_task_id: Optional[str] = None
    raptor_task_id: Optional[str] = None
    mindmap_task_id: Optional[str] = None
    create_time: Optional[int] = None
    create_date: Optional[str] = None
    update_time: Optional[int] = None
    update_date: Optional[str] = None

    class Config:
        from_attributes = True


class KnowledgebaseListResponse(BaseModel):
    knowledgebases: List[KnowledgebaseResponse] = Field(default_factory=list)
    total: int = 0


# Document schemas
class DocumentCreate(BaseModel):
    kb_id: str = Field(..., min_length=32, max_length=32)
    name: str = Field(..., min_length=1, max_length=255)
    parser_id: str = Field(..., min_length=1, max_length=32)
    created_by: str = Field(..., min_length=32, max_length=32)
    doc_type: Optional[str] = Field(default=None, max_length=32)
    pipeline_id: Optional[str] = Field(default=None, max_length=32)


class DocumentResponse(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    kb_id: str = Field(..., min_length=32, max_length=32)
    name: str
    parser_id: str
    created_by: str = Field(..., min_length=32, max_length=32)
    progress: float
    progress_msg: str
    process_duation: float
    doc_type: Optional[str] = None
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)
    meta_fields: Dict[str, Any] = Field(default_factory=dict)
    thumbnail: Optional[str] = None
    pipeline_id: Optional[str] = None
    create_time: Optional[int] = None
    create_date: Optional[str] = None
    update_time: Optional[int] = None
    update_date: Optional[str] = None

    class Config:
        from_attributes = True


# File schemas
class FileUploadResponse(BaseModel):
    filename: str
    file_id: str = Field(..., min_length=32, max_length=32)
    doc_id: str = Field(..., min_length=32, max_length=32)
    task_id: str = Field(..., min_length=32, max_length=32)
    size: int
    file_type: str
    status: str = "queued"


class FileResponse(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    name: str
    size: int
    type: str
    source_type: str
    created_by: str = Field(..., min_length=32, max_length=32)
    create_time: Optional[int] = None
    create_date: Optional[str] = None

    class Config:
        from_attributes = True


# Task schemas
class TaskResponse(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    doc_id: str = Field(..., min_length=32, max_length=32)
    task_type: str
    from_page: int
    to_page: int
    priority: int
    begin_at: Optional[str] = None
    process_duation: float
    progress: float
    progress_msg: str
    retry_count: int
    digest: Optional[str] = None
    chunk_ids: Optional[str] = None
    create_time: Optional[int] = None
    create_date: Optional[str] = None

    class Config:
        from_attributes = True
