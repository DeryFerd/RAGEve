from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


class DialogCreate(BaseModel):
    tenant_id: str = Field(..., min_length=32, max_length=32)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    language: str = Field(default="English", max_length=32)
    llm_id: str = Field(..., max_length=128)
    llm_setting: Optional[Dict[str, Any]] = Field(default_factory=lambda: {
        "temperature": 0.1,
        "top_p": 0.3,
        "frequency_penalty": 0.7,
        "presence_penalty": 0.4,
        "max_tokens": 512
    })
    prompt_type: str = Field(default="simple", max_length=16)
    prompt_config: Optional[Dict[str, Any]] = Field(default_factory=lambda: {
        "system": "",
        "prologue": "Hi! I'm your assistant. What can I do for you?",
        "parameters": [],
        "empty_response": "Sorry! No relevant content was found in the knowledge base!"
    })
    meta_data_filter: Optional[Dict[str, Any]] = Field(default_factory=dict)
    similarity_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    vector_similarity_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    top_n: int = Field(default=6, ge=1)
    top_k: int = Field(default=1024, ge=1)
    do_refer: str = Field(default="1", max_length=1)
    rerank_id: str = Field(default="")
    kb_ids: Optional[List[str]] = Field(default_factory=list)
    status: str = Field(default="1", max_length=1)


class DialogUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    language: Optional[str] = Field(default=None, max_length=32)
    llm_id: Optional[str] = Field(default=None, max_length=128)
    llm_setting: Optional[Dict[str, Any]] = None
    prompt_type: Optional[str] = Field(default=None, max_length=16)
    prompt_config: Optional[Dict[str, Any]] = None
    meta_data_filter: Optional[Dict[str, Any]] = None
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    vector_similarity_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_n: Optional[int] = Field(default=None, ge=1)
    top_k: Optional[int] = Field(default=None, ge=1)
    do_refer: Optional[str] = Field(default=None, max_length=1)
    rerank_id: Optional[str] = Field(default=None, max_length=128)
    kb_ids: Optional[List[str]] = None
    status: Optional[str] = Field(default=None, max_length=1)


class DialogResponse(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    tenant_id: str = Field(..., min_length=32, max_length=32)
    name: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    llm_id: str
    llm_setting: Dict[str, Any]
    prompt_type: str
    prompt_config: Dict[str, Any]
    meta_data_filter: Dict[str, Any]
    similarity_threshold: float
    vector_similarity_weight: float
    top_n: int
    top_k: int
    do_refer: str
    rerank_id: str
    kb_ids: List[str]
    status: str
    create_time: Optional[int] = None
    create_date: Optional[str] = None
    update_time: Optional[int] = None
    update_date: Optional[str] = None

    class Config:
        from_attributes = True


class DialogListResponse(BaseModel):
    dialogs: List[DialogResponse] = Field(default_factory=list)
    total: int = 0
