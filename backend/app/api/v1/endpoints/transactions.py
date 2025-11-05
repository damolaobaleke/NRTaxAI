"""
Transactions Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
from app.models.transaction import (
    Transaction, TransactionCreate, TransactionUpdate,
    TransactionStatus
)
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Create transaction record"""
    # Verify user owns the transaction
    if transaction_data.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    return await transaction_service.create_transaction(db, transaction_data)


@router.get("", response_model=List[Transaction])
async def list_transactions(
    user_id: Optional[UUID] = Query(None),
    partnership_id: Optional[UUID] = Query(None),
    status_filter: Optional[TransactionStatus] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """List transactions with filters"""
    # Users can only see their own transactions unless admin
    if user_id and user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    if not user_id:
        user_id = current_user.id
    
    return await transaction_service.list_transactions(
        db, user_id, partnership_id, status_filter, limit, offset
    )


@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get transaction details"""
    transaction = await transaction_service.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    
    # Verify user owns the transaction
    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    return transaction


@router.get("/partnerships/{partnership_id}/transactions", response_model=List[Transaction])
async def get_partnership_transactions(
    partnership_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Get transactions for a partnership"""
    return await transaction_service.list_transactions(
        db, partnership_id=partnership_id, limit=limit, offset=offset
    )

