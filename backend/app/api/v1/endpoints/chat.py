"""
Chat Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text
from pydantic import BaseModel
import json

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.services.chat_service import ChatService
from app.models.user import UserInDB
from app.models.chat import (
    ChatSession, ChatSessionCreate, ChatMessage, ChatMessageRequest,
    ChatMessageResponse, ChatHistory
)

router = APIRouter()


@router.post("/session", response_model=ChatSession)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Create new chat session"""
    
    result = await db.execute(
        text("""
                INSERT INTO chat_sessions (user_id, tax_return_id, status)
                VALUES (:user_id, :tax_return_id, :status)
                RETURNING id, user_id, tax_return_id, status, created_at
                """),
        {
            "user_id": current_user.id,
            "tax_return_id": session_data.tax_return_id,
            "status": session_data.status
        }
    )
    session = result.fetchone()
    
    return ChatSession(**session._asdict()) if session else None


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    message_request: ChatMessageRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Send chat message and get AI response"""
    
    # Verify session ownership
    result = await db.execute(
        text("""
            SELECT * FROM chat_sessions 
            WHERE id = :session_id AND user_id = :user_id
            """),
            {   
            "session_id": message_request.session_id,
            "user_id": current_user.id
            }
    )
    session = result.fetchone()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get chat service and send message
    chat_service = ChatService(db)
    
    context = {}
    if hasattr(message_request, 'return_id') and message_request.return_id:
        context["return_id"] = str(message_request.return_id)
    
    response = await chat_service.send_message(
        session_id=str(message_request.session_id),
        user_id=str(current_user.id),
        message=message_request.message,
        context=context
    )
    print(f"{message_request.session_id}\n==message response==\n")
    print(response)
    
    return ChatMessageResponse(
        message=response["message"],
        session_id=message_request.session_id,
        message_id=None  # The service stores messages internally
    )


@router.get("/history", response_model=ChatHistory)
async def get_chat_history(
    session_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get chat history for a session"""
    
    # Verify session ownership
    result = await db.execute(
    text("""
            SELECT * FROM chat_sessions 
            WHERE id = :session_id AND user_id = :user_id
            """),
            {
                "session_id": session_id,
                "user_id": current_user.id
            }
    )
    session = result.fetchone()
        
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get all messages for the session
    result = await db.execute(
        text("""
        SELECT id, session_id, role, content, tool_calls_json, created_at
        FROM chat_messages 
        WHERE session_id = :session_id
        ORDER BY created_at ASC
        """),
        {"session_id": session_id}
    )
    messages = result.fetchall()
    
    # Process messages to handle tool_calls_json properly
    processed_messages = []
    for msg in messages:
        msg_dict = msg._asdict()
        # Parse tool_calls_json if it exists
        if msg_dict.get("tool_calls_json"):
            try:
                msg_dict["tool_calls_json"] = json.loads(msg_dict["tool_calls_json"])
            except (json.JSONDecodeError, TypeError):
                msg_dict["tool_calls_json"] = None
        processed_messages.append(ChatMessage(**msg_dict))
    
    return ChatHistory(
        session=ChatSession(**session._asdict()),
        messages=processed_messages
    )


@router.get("/sessions", response_model=List[ChatSession])
async def get_user_sessions(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get all chat sessions for current user"""
    
    result = await db.execute(
        text("""
        SELECT id, user_id, tax_return_id, status, created_at
        FROM chat_sessions 
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        """),
        {"user_id": current_user.id}
    )
    sessions = result.fetchall()
    
    return [ChatSession(**session._asdict()) for session in sessions]


class StoreMessageRequest(BaseModel):
    """Request model for storing a message"""
    session_id: UUID
    role: str
    content: str
    tool_calls: Optional[List[dict]] = None


@router.post("/message/store")
async def store_message(
    message_data: StoreMessageRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Store a message in the database without triggering AI response"""
    
    # Validate role
    if message_data.role not in ["user", "assistant", "system", "tool"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {message_data.role}. Must be one of: user, assistant, system, tool"
        )
    
    # Verify session ownership
    result = await db.execute(
        text("""
            SELECT * FROM chat_sessions 
            WHERE id = :session_id AND user_id = :user_id
            """),
        {
            "session_id": message_data.session_id,
            "user_id": current_user.id
        }
    )
    session = result.fetchone()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Use ChatService to store the message (it has the _store_message method)
    chat_service = ChatService(db)
    await chat_service._store_message(
        session_id=str(message_data.session_id),
        role=message_data.role,
        content=message_data.content,
        tool_calls=message_data.tool_calls
    )
    
    return {
        "message": "Message stored successfully",
        "session_id": str(message_data.session_id),
        "role": message_data.role
    }
