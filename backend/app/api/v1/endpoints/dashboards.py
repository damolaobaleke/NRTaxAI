"""
University Dashboard Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
from app.services import payout_service, transaction_service, partnership_service
from app.models.transaction import TransactionStatus

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


class DashboardSummary(BaseModel):
    """Dashboard summary model"""
    partnership_id: UUID
    total_filings: int
    completed_filings: int
    compliance_percentage: float
    accrued_payout: float
    total_revenue: float


class DashboardStatistics(BaseModel):
    """Detailed statistics"""
    partnership_id: UUID
    total_students: int
    total_filings: int
    completed_filings: int
    in_progress_filings: int
    compliance_percentage: float
    total_revenue: float
    accrued_commission: float
    pending_payouts: int


@router.get("/university/{partnership_id}", response_model=DashboardSummary)
async def get_university_dashboard(
    partnership_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add university admin check
    db = Depends(get_database)
):
    """Dashboard summary (filings, compliance %, accrued payout)"""
    # Get partnership
    partnership = await partnership_service.get_partnership_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership not found")
    
    # Get transactions (succeeded = completed filings)
    transactions = await transaction_service.list_transactions(
        db, partnership_id=partnership_id, status_filter=TransactionStatus.SUCCEEDED
    )
    
    total_filings = len(transactions)
    completed_filings = len([t for t in transactions if t.status == TransactionStatus.SUCCEEDED])
    
    # Calculate total revenue and accrued payout
    total_revenue = sum(float(t.amount) for t in transactions)
    accrued_payout = sum(float(t.partner_share or 0) for t in transactions)
    
    # TODO: Get total eligible students to calculate compliance
    # For now, using completed/total as placeholder
    compliance_percentage = (completed_filings / total_filings * 100) if total_filings > 0 else 0.0
    
    return DashboardSummary(
        partnership_id=partnership_id,
        total_filings=total_filings,
        completed_filings=completed_filings,
        compliance_percentage=compliance_percentage,
        accrued_payout=accrued_payout,
        total_revenue=total_revenue
    )


@router.get("/university/{partnership_id}/statistics", response_model=DashboardStatistics)
async def get_dashboard_statistics(
    partnership_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add university admin check
    db = Depends(get_database)
):
    """Detailed statistics (adoption, revenue, etc.)"""
    # Get partnership
    partnership = await partnership_service.get_partnership_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership not found")
    
    # Get all transactions
    all_transactions = await transaction_service.list_transactions(db, partnership_id=partnership_id)
    
    total_filings = len(all_transactions)
    completed_filings = len([t for t in all_transactions if t.status == TransactionStatus.SUCCEEDED])
    in_progress_filings = len([t for t in all_transactions if t.status == TransactionStatus.PENDING])
    
    # Get unique users (total students)
    unique_users = len(set(t.user_id for t in all_transactions))
    
    # Calculate revenue
    total_revenue = sum(float(t.amount) for t in all_transactions if t.status == TransactionStatus.SUCCEEDED)
    accrued_commission = sum(float(t.partner_share or 0) for t in all_transactions if t.status == TransactionStatus.SUCCEEDED)
    
    # Get pending payouts
    payouts = await payout_service.list_payouts(db, partnership_id, status_filter=None)
    pending_payouts = len([p for p in payouts if p.payout_status.value == "pending"])
    
    compliance_percentage = (completed_filings / total_filings * 100) if total_filings > 0 else 0.0
    
    return DashboardStatistics(
        partnership_id=partnership_id,
        total_students=unique_users,
        total_filings=total_filings,
        completed_filings=completed_filings,
        in_progress_filings=in_progress_filings,
        compliance_percentage=compliance_percentage,
        total_revenue=total_revenue,
        accrued_commission=accrued_commission,
        pending_payouts=pending_payouts
    )

