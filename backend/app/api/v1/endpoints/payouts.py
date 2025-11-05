"""
Payouts Endpoints
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
from app.models.payout import (
    Payout, PayoutCreate, PayoutCalculation, PayoutMethod, PayoutStatus
)
from app.services import payout_service

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.get("/partnerships/{partnership_id}/payouts", response_model=List[Payout])
async def list_partnership_payouts(
    partnership_id: UUID,
    status_filter: Optional[PayoutStatus] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin/university admin check
    db = Depends(get_database)
):
    """List payouts for a partnership"""
    return await payout_service.list_payouts(db, partnership_id, status_filter)


@router.post("/partnerships/{partnership_id}/calculate", response_model=PayoutCalculation)
async def calculate_payout(
    partnership_id: UUID,
    period_start: date,
    period_end: date,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Calculate payout for a period"""
    return await payout_service.calculate_payout(db, partnership_id, period_start, period_end)


@router.post("/partnerships/{partnership_id}/payouts", response_model=Payout, status_code=status.HTTP_201_CREATED)
async def create_payout(
    partnership_id: UUID,
    payout_data: PayoutCreate,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Create payout record"""
    payout_data.partnership_id = partnership_id
    return await payout_service.create_payout(db, payout_data)


@router.post("/{payout_id}/process", response_model=Payout)
async def process_payout(
    payout_id: UUID,
    stripe_transfer_id: Optional[str] = None,
    ach_reference: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Process payout (Stripe/ACH)"""
    return await payout_service.process_payout(db, payout_id, stripe_transfer_id, ach_reference)


@router.get("/{payout_id}", response_model=Payout)
async def get_payout(
    payout_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get payout details"""
    payout = await payout_service.get_payout_by_id(db, payout_id)
    if not payout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found")
    return payout

