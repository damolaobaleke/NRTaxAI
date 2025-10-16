"""
Chat Session and Message Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ChatSessionBase(BaseModel):
    """Base chat session model"""
    tax_return_id: Optional[UUID] = None
    status: str = Field("active", max_length=20)


class ChatSessionCreate(ChatSessionBase):
    """Chat session creation model"""
    pass


class ChatSessionUpdate(BaseModel):
    """Chat session update model"""
    status: Optional[str] = Field(None, max_length=20)
    tax_return_id: Optional[UUID] = None


class ChatSessionInDB(ChatSessionBase):
    """Chat session in database model"""
    id: UUID
    user_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatSession(ChatSessionBase):
    """Chat session response model"""
    id: UUID
    user_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessageBase(BaseModel):
    """Base chat message model"""
    role: str = Field(..., max_length=20)  # user, assistant, system, tool
    content: Optional[str] = None
    tool_calls_json: Optional[Dict[str, Any]] = None


class ChatMessageCreate(ChatMessageBase):
    """Chat message creation model"""
    session_id: UUID


class ChatMessageInDB(ChatMessageBase):
    """Chat message in database model"""
    id: UUID
    session_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessage(ChatMessageBase):
    """Chat message response model"""
    id: UUID
    session_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatHistory(BaseModel):
    """Chat history response model"""
    session: ChatSession
    messages: List[ChatMessage]


class ChatMessageRequest(BaseModel):
    """Chat message request model"""
    session_id: UUID
    message: str


class ChatMessageResponse(BaseModel):
    """Chat message response model"""
    message: str
    session_id: UUID
    message_id: Optional[UUID] = None
