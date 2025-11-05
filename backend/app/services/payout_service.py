"""
Payout Service - Revenue share payout calculations and processing
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.payout import (
    Payout, PayoutCreate, PayoutCalculation, PayoutInDB,
    PayoutMethod, PayoutStatus
)
from app.models.transaction import TransactionStatus
from app.services.partnership_service import get_partnership_by_id


async def calculate_payout(
    db,
    partnership_id: UUID,
    period_start: date,
    period_end: date
) -> PayoutCalculation:
    """Calculate payout for a partnership over a period"""
    # Get partnership to get commission percent
    partnership = await get_partnership_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership not found")
    
    if not partnership.commission_percent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Partnership does not have commission configured")
    
    commission_percent = Decimal(str(partnership.commission_percent))
    
    # Get all succeeded transactions for this partnership in the period
    result = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(amount), 0) as gross_amount,
                ARRAY_AGG(id) as transaction_ids
            FROM transactions
            WHERE partnership_id = :partnership_id
            AND status = :status
            AND DATE(created_at) >= :period_start
            AND DATE(created_at) <= :period_end
        """),
        {
            "partnership_id": partnership_id,
            "status": TransactionStatus.SUCCEEDED.value,
            "period_start": period_start,
            "period_end": period_end
        }
    )
    row = result.fetchone()
    
    total_transactions = row["total_transactions"] or 0
    gross_amount = Decimal(str(row["gross_amount"] or 0))
    transaction_ids = row["transaction_ids"] or []
    
    # Calculate commission (10% of total revenue)
    commission_amount = gross_amount * (commission_percent / Decimal("100"))
    
    return PayoutCalculation(
        partnership_id=partnership_id,
        period_start=period_start,
        period_end=period_end,
        total_transactions=total_transactions,
        gross_amount=gross_amount,
        commission_percent=commission_percent,
        commission_amount=commission_amount,
        transaction_ids=transaction_ids
    )


async def create_payout(db, payout_data: PayoutCreate) -> PayoutInDB:
    """Create payout record from calculation"""
    calculation = await calculate_payout(
        db, payout_data.partnership_id, payout_data.period_start, payout_data.period_end
    )
    
    # Check for existing payout for this period
    result = await db.execute(
        text("""
            SELECT id FROM payouts
            WHERE partnership_id = :partnership_id
            AND period_start = :period_start
            AND period_end = :period_end
        """),
        {
            "partnership_id": payout_data.partnership_id,
            "period_start": payout_data.period_start,
            "period_end": payout_data.period_end
        }
    )
    existing = result.fetchone()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payout for this period already exists")
    
    try:
        result = await db.execute(
            text("""
                INSERT INTO payouts (
                    partnership_id, period_start, period_end,
                    total_transactions, gross_amount, commission_percent, commission_amount,
                    payout_method, payout_status, notes
                )
                VALUES (
                    :partnership_id, :period_start, :period_end,
                    :total_transactions, :gross_amount, :commission_percent, :commission_amount,
                    :payout_method, :payout_status, :notes
                )
                RETURNING id, partnership_id, period_start, period_end,
                          total_transactions, gross_amount, commission_percent, commission_amount,
                          payout_method, payout_status, stripe_transfer_id, ach_reference, notes,
                          created_at, updated_at, paid_at
            """),
            {
                "partnership_id": payout_data.partnership_id,
                "period_start": payout_data.period_start,
                "period_end": payout_data.period_end,
                "total_transactions": calculation.total_transactions,
                "gross_amount": calculation.gross_amount,
                "commission_percent": calculation.commission_percent,
                "commission_amount": calculation.commission_amount,
                "payout_method": payout_data.payout_method.value if payout_data.payout_method else None,
                "payout_status": PayoutStatus.PENDING.value,
                "notes": payout_data.notes
            }
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create payout")
        
        row_dict = dict(row)
        row_dict["payout_method"] = PayoutMethod(row_dict["payout_method"]) if row_dict["payout_method"] else None
        row_dict["payout_status"] = PayoutStatus(row_dict["payout_status"])
        return PayoutInDB(**row_dict)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_payout_by_id(db, payout_id: UUID) -> Optional[PayoutInDB]:
    """Get payout by ID"""
    result = await db.execute(
        text("""
            SELECT id, partnership_id, period_start, period_end,
                   total_transactions, gross_amount, commission_percent, commission_amount,
                   payout_method, payout_status, stripe_transfer_id, ach_reference, notes,
                   created_at, updated_at, paid_at
            FROM payouts WHERE id = :id
        """),
        {"id": payout_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    row_dict = dict(row)
    row_dict["payout_method"] = PayoutMethod(row_dict["payout_method"]) if row_dict["payout_method"] else None
    row_dict["payout_status"] = PayoutStatus(row_dict["payout_status"])
    return PayoutInDB(**row_dict)


async def list_payouts(
    db,
    partnership_id: Optional[UUID] = None,
    status_filter: Optional[PayoutStatus] = None,
    limit: int = 100
) -> List[PayoutInDB]:
    """List payouts with filters"""
    conditions = []
    params = {"limit": limit}
    
    if partnership_id:
        conditions.append("partnership_id = :partnership_id")
        params["partnership_id"] = partnership_id
    if status_filter:
        conditions.append("payout_status = :payout_status")
        params["payout_status"] = status_filter.value
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    result = await db.execute(
        text(f"""
            SELECT id, partnership_id, period_start, period_end,
                   total_transactions, gross_amount, commission_percent, commission_amount,
                   payout_method, payout_status, stripe_transfer_id, ach_reference, notes,
                   created_at, updated_at, paid_at
            FROM payouts
            {where_clause}
            ORDER BY period_end DESC, created_at DESC
            LIMIT :limit
        """),
        params
    )
    
    rows = result.fetchall()
    payouts = []
    for row in rows:
        row_dict = dict(row)
        row_dict["payout_method"] = PayoutMethod(row_dict["payout_method"]) if row_dict["payout_method"] else None
        row_dict["payout_status"] = PayoutStatus(row_dict["payout_status"])
        payouts.append(PayoutInDB(**row_dict))
    
    return payouts


async def update_payout(
    db,
    payout_id: UUID,
    payout_status: Optional[PayoutStatus] = None,
    stripe_transfer_id: Optional[str] = None,
    ach_reference: Optional[str] = None,
    paid_at: Optional[datetime] = None
) -> PayoutInDB:
    """Update payout (e.g., after processing)"""
    updates = []
    params = {"id": payout_id}
    
    if payout_status:
        updates.append("payout_status = :payout_status")
        params["payout_status"] = payout_status.value
    if stripe_transfer_id is not None:
        updates.append("stripe_transfer_id = :stripe_transfer_id")
        params["stripe_transfer_id"] = stripe_transfer_id
    if ach_reference is not None:
        updates.append("ach_reference = :ach_reference")
        params["ach_reference"] = ach_reference
    if paid_at:
        updates.append("paid_at = :paid_at")
        params["paid_at"] = paid_at
    
    if not updates:
        return await get_payout_by_id(db, payout_id)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    result = await db.execute(
        text(f"""
            UPDATE payouts
            SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id, partnership_id, period_start, period_end,
                      total_transactions, gross_amount, commission_percent, commission_amount,
                      payout_method, payout_status, stripe_transfer_id, ach_reference, notes,
                      created_at, updated_at, paid_at
        """),
        params
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found")
    
    row_dict = dict(row)
    row_dict["payout_method"] = PayoutMethod(row_dict["payout_method"]) if row_dict["payout_method"] else None
    row_dict["payout_status"] = PayoutStatus(row_dict["payout_status"])
    return PayoutInDB(**row_dict)


async def process_payout(
    db,
    payout_id: UUID,
    stripe_transfer_id: Optional[str] = None,
    ach_reference: Optional[str] = None
) -> PayoutInDB:
    """Process payout (mark as processing, then completed)"""
    payout = await get_payout_by_id(db, payout_id)
    if not payout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found")
    
    if payout.payout_status != PayoutStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payout is not in pending status")
    
    # Mark as processing
    payout = await update_payout(
        db, payout_id,
        payout_status=PayoutStatus.PROCESSING,
        stripe_transfer_id=stripe_transfer_id,
        ach_reference=ach_reference
    )
    
    # Note: Actual payment processing (Stripe Connect/ACH) would happen here
    # Then mark as completed
    payout = await update_payout(
        db, payout_id,
        payout_status=PayoutStatus.COMPLETED,
        paid_at=datetime.utcnow()
    )
    
    return payout

