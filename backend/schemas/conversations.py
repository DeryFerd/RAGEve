from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


class MessageBase(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    # Additional optional fields that can be stored in the message object
    token_count: Optional[int] = Field(default=None, description="Token count for this message")
    sources: Optional[List[Dict[str, Any]]] = Field(default=None, description="Retrieved sources for assistant messages")


class ConversationCreate(BaseModel):
    dialog_id: str = Field(..., min_length=32, max_length=32)
    name: Optional[str] = Field(default="New conversation", max_length=255)
    user_id: Optional[str] = Field(default=None, max_length=255)
    messages: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Initial messages")
    reference: Optional[List[Any]] = Field(default_factory=list, description="Reference data")


class ConversationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    reference: Optional[List[Any]] = None
    # Note: messages are updated via separate append endpoint, not bulk replace


class ConversationResponse(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    dialog_id: str = Field(..., min_length=32, max_length=32)
    name: Optional[str] = None
    message: List[Dict[str, Any]] = Field(default_factory=list, description="Array of message objects")
    reference: List[Any] = Field(default_factory=list)
    user_id: Optional[str] = None
    create_time: Optional[int] = None
    create_date: Optional[str] = None
    update_time: Optional[int] = None
    update_date: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse] = Field(default_factory=list)
    total: int = 0
    limit: int = 0
    offset: int = 0


class AppendMessageRequest(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    # Optional additional fields
    token_count: Optional[int] = None
    sources: Optional[List[Dict[str, Any]]] = None


class MessageResponse(BaseModel):
    """Response for a single appended message."""
    role: str
    content: str
    token_count: Optional[int] = None
    sources: Optional[List[Dict[str, Any]]] = None
    # Include any extra fields that were stored
    extra: Optional[Dict[str, Any]] = None


class ConversationContextResponse(BaseModel):
    """Formatted conversation context for LLM consumption."""
    messages: List[Dict[str, str]] = Field(..., description="List of {role, content} for LLM")
    truncated: bool = Field(default=False, description="True if history was truncated")
