"""
Chat Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth import get_current_active_user
from app.services.chat_service import get_chat_service
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
    
    session = await db.fetch_one(
        """
        INSERT INTO chat_sessions (user_id, tax_return_id, status)
        VALUES (:user_id, :tax_return_id, :status)
        RETURNING id, user_id, tax_return_id, status, created_at
        """,
        {
            "user_id": current_user.id,
            "tax_return_id": session_data.tax_return_id,
            "status": session_data.status
        }
    )
    
    return ChatSession(**session)


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    message_request: ChatMessageRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Send chat message and get AI response"""
    
    # Verify session ownership
    session = await db.fetch_one(
        """
        SELECT * FROM chat_sessions 
        WHERE id = :session_id AND user_id = :user_id
        """,
        {
            "session_id": message_request.session_id,
            "user_id": current_user.id
        }
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get chat service and send message
    chat_service = await get_chat_service()
    
    context = {}
    if hasattr(message_request, 'return_id') and message_request.return_id:
        context["return_id"] = str(message_request.return_id)
    
    response = await chat_service.send_message(
        session_id=str(message_request.session_id),
        user_id=str(current_user.id),
        message=message_request.message,
        context=context
    )
    
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
    session = await db.fetch_one(
        """
        SELECT * FROM chat_sessions 
        WHERE id = :session_id AND user_id = :user_id
        """,
        {
            "session_id": session_id,
            "user_id": current_user.id
        }
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get all messages for the session
    messages = await db.fetch_all(
        """
        SELECT id, session_id, role, content, tool_calls_json, created_at
        FROM chat_messages 
        WHERE session_id = :session_id
        ORDER BY created_at ASC
        """,
        {"session_id": session_id}
    )
    
    return ChatHistory(
        session=ChatSession(**session),
        messages=[ChatMessage(**msg) for msg in messages]
    )


@router.get("/sessions", response_model=List[ChatSession])
async def get_user_sessions(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get all chat sessions for current user"""
    
    sessions = await db.fetch_all(
        """
        SELECT id, user_id, tax_return_id, status, created_at
        FROM chat_sessions 
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        """,
        {"user_id": current_user.id}
    )
    
    return [ChatSession(**session) for session in sessions]
