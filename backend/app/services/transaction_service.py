"""
Transaction Service - Payment processing and revenue splits
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.transaction import (
    Transaction, TransactionCreate, TransactionUpdate, TransactionInDB,
    TransactionType, TransactionStatus
)
from app.services.attribution_service import lock_referral_by_user
from app.services.partnership_service import get_partnership_by_id


# Revenue split percentages (from business model)
PLATFORM_SHARE = Decimal("0.70")  # 70%
CPA_SHARE = Decimal("0.30")  # 30%
PARTNER_SHARE = Decimal("0.10")  # 10% (of total, so 10% of 70% = 7% of total)


async def calculate_revenue_split(
    amount: Decimal,
    partnership_id: Optional[UUID],
    db
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Calculate revenue split:
    - Platform: 70% (or 90% if no partner)
    - CPA: 30%
    - Partner: 10% (only if partnership exists)
    """
    cpa_share = amount * CPA_SHARE
    
    if partnership_id:
        # With partner: Partner gets 10% of total (10% commission)
        # Platform gets 70% - 10% = 60% of total
        partner_share = amount * PARTNER_SHARE
        platform_share = amount * PLATFORM_SHARE - partner_share
    else:
        # No partner: Platform keeps 70%
        partner_share = Decimal("0")
        platform_share = amount * PLATFORM_SHARE
    
    return platform_share, cpa_share, partner_share


async def create_transaction(db, transaction_data: TransactionCreate) -> TransactionInDB:
    """Create a new transaction and calculate revenue splits"""
    # Calculate revenue splits
    amount = Decimal(str(transaction_data.amount))
    platform_share, cpa_share, partner_share = await calculate_revenue_split(
        amount, transaction_data.partnership_id, db
    )
    net_to_platform = platform_share
    
    # If referral exists and payment succeeded, lock the referral
    if transaction_data.referral_id:
        referral = await lock_referral_by_user(db, transaction_data.user_id)
    elif transaction_data.user_id:
        # Try to find and lock referral by user
        referral = await lock_referral_by_user(db, transaction_data.user_id)
        if referral:
            transaction_data.referral_id = referral.id
            transaction_data.partnership_id = referral.partnership_id
    
    try:
        result = await db.execute(
            text("""
                INSERT INTO transactions (
                    user_id, tax_return_id, partnership_id, referral_id,
                    transaction_type, amount, currency, stripe_payment_intent_id,
                    status, platform_share, cpa_share, partner_share, net_to_platform
                )
                VALUES (
                    :user_id, :tax_return_id, :partnership_id, :referral_id,
                    :transaction_type, :amount, :currency, :stripe_payment_intent_id,
                    :status, :platform_share, :cpa_share, :partner_share, :net_to_platform
                )
                RETURNING id, user_id, tax_return_id, partnership_id, referral_id,
                          transaction_type, amount, currency, stripe_payment_intent_id, stripe_charge_id,
                          status, platform_share, cpa_share, partner_share, net_to_platform,
                          created_at, updated_at
            """),
            {
                "user_id": transaction_data.user_id,
                "tax_return_id": transaction_data.tax_return_id,
                "partnership_id": transaction_data.partnership_id,
                "referral_id": transaction_data.referral_id,
                "transaction_type": transaction_data.transaction_type.value,
                "amount": amount,
                "currency": transaction_data.currency,
                "stripe_payment_intent_id": transaction_data.stripe_payment_intent_id,
                "status": TransactionStatus.PENDING.value,
                "platform_share": platform_share,
                "cpa_share": cpa_share,
                "partner_share": partner_share,
                "net_to_platform": net_to_platform
            }
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create transaction")
        
        row_dict = dict(row)
        row_dict["transaction_type"] = TransactionType(row_dict["transaction_type"])
        row_dict["status"] = TransactionStatus(row_dict["status"])
        return TransactionInDB(**row_dict)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_transaction_by_id(db, transaction_id: UUID) -> Optional[TransactionInDB]:
    """Get transaction by ID"""
    result = await db.execute(
        text("""
            SELECT id, user_id, tax_return_id, partnership_id, referral_id,
                   transaction_type, amount, currency, stripe_payment_intent_id, stripe_charge_id,
                   status, platform_share, cpa_share, partner_share, net_to_platform,
                   created_at, updated_at
            FROM transactions WHERE id = :id
        """),
        {"id": transaction_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    row_dict = dict(row)
    row_dict["transaction_type"] = TransactionType(row_dict["transaction_type"])
    row_dict["status"] = TransactionStatus(row_dict["status"])
    return TransactionInDB(**row_dict)


async def get_transaction_by_stripe_payment_intent(db, payment_intent_id: str) -> Optional[TransactionInDB]:
    """Get transaction by Stripe payment intent ID"""
    result = await db.execute(
        text("""
            SELECT id, user_id, tax_return_id, partnership_id, referral_id,
                   transaction_type, amount, currency, stripe_payment_intent_id, stripe_charge_id,
                   status, platform_share, cpa_share, partner_share, net_to_platform,
                   created_at, updated_at
            FROM transactions WHERE stripe_payment_intent_id = :payment_intent_id
        """),
        {"payment_intent_id": payment_intent_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    row_dict = dict(row)
    row_dict["transaction_type"] = TransactionType(row_dict["transaction_type"])
    row_dict["status"] = TransactionStatus(row_dict["status"])
    return TransactionInDB(**row_dict)


async def update_transaction(db, transaction_id: UUID, transaction_data: TransactionUpdate) -> TransactionInDB:
    """Update transaction (e.g., on Stripe webhook)"""
    updates = []
    params = {"id": transaction_id}
    
    if transaction_data.stripe_charge_id is not None:
        updates.append("stripe_charge_id = :stripe_charge_id")
        params["stripe_charge_id"] = transaction_data.stripe_charge_id
    if transaction_data.status is not None:
        updates.append("status = :status")
        params["status"] = transaction_data.status.value
    if transaction_data.platform_share is not None:
        updates.append("platform_share = :platform_share")
        params["platform_share"] = transaction_data.platform_share
    if transaction_data.cpa_share is not None:
        updates.append("cpa_share = :cpa_share")
        params["cpa_share"] = transaction_data.cpa_share
    if transaction_data.partner_share is not None:
        updates.append("partner_share = :partner_share")
        params["partner_share"] = transaction_data.partner_share
    if transaction_data.net_to_platform is not None:
        updates.append("net_to_platform = :net_to_platform")
        params["net_to_platform"] = transaction_data.net_to_platform
    
    if not updates:
        return await get_transaction_by_id(db, transaction_id)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    result = await db.execute(
        text(f"""
            UPDATE transactions
            SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id, user_id, tax_return_id, partnership_id, referral_id,
                      transaction_type, amount, currency, stripe_payment_intent_id, stripe_charge_id,
                      status, platform_share, cpa_share, partner_share, net_to_platform,
                      created_at, updated_at
        """),
        params
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    
    row_dict = dict(row)
    row_dict["transaction_type"] = TransactionType(row_dict["transaction_type"])
    row_dict["status"] = TransactionStatus(row_dict["status"])
    return TransactionInDB(**row_dict)


async def update_transaction_status(
    db,
    transaction_id: UUID,
    new_status: TransactionStatus,
    stripe_charge_id: Optional[str] = None
) -> TransactionInDB:
    """Update transaction status (used by webhooks)"""
    update_data = TransactionUpdate(status=new_status, stripe_charge_id=stripe_charge_id)
    return await update_transaction(db, transaction_id, update_data)


async def list_transactions(
    db,
    user_id: Optional[UUID] = None,
    partnership_id: Optional[UUID] = None,
    status_filter: Optional[TransactionStatus] = None,
    limit: int = 100,
    offset: int = 0
):
    """List transactions with filters"""
    conditions = []
    params = {"limit": limit, "offset": offset}
    
    if user_id:
        conditions.append("user_id = :user_id")
        params["user_id"] = user_id
    if partnership_id:
        conditions.append("partnership_id = :partnership_id")
        params["partnership_id"] = partnership_id
    if status_filter:
        conditions.append("status = :status")
        params["status"] = status_filter.value
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    result = await db.execute(
        text(f"""
            SELECT id, user_id, tax_return_id, partnership_id, referral_id,
                   transaction_type, amount, currency, stripe_payment_intent_id, stripe_charge_id,
                   status, platform_share, cpa_share, partner_share, net_to_platform,
                   created_at, updated_at
            FROM transactions
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params
    )
    
    rows = result.fetchall()
    transactions = []
    for row in rows:
        row_dict = dict(row)
        row_dict["transaction_type"] = TransactionType(row_dict["transaction_type"])
        row_dict["status"] = TransactionStatus(row_dict["status"])
        transactions.append(TransactionInDB(**row_dict))
    
    return transactions

