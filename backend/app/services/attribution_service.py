"""
Attribution Service - Referral tracking and attribution management
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.referral import Referral, ReferralCreate, ReferralInDB, ReferralStatus
from app.services.partnership_service import get_partnership_by_id


async def create_referral(
    db,
    user_id: UUID,
    partnership_id: UUID,
    referral_code: str,
    source: Optional[str] = None,
    campaign_id: Optional[str] = None,
    expiry_days: int = 90
) -> ReferralInDB:
    """Create or update referral attribution"""
    # Get partnership to verify it exists
    partnership = await get_partnership_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership not found")
    
    # Check for existing pending referral for this user
    existing = await get_referral_by_user(db, user_id)
    
    now = datetime.utcnow()
    expiry_date = now + timedelta(days=expiry_days)
    
    if existing and existing.status == ReferralStatus.PENDING:
        # Update existing referral (last-click attribution)
        result = await db.execute(
            text("""
                UPDATE referrals
                SET partnership_id = :partnership_id,
                    referral_code = :referral_code,
                    source = :source,
                    last_touch_ts = :last_touch_ts,
                    expiry_date = :expiry_date,
                    campaign_id = :campaign_id,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING id, user_id, partnership_id, referral_code, source,
                          first_touch_ts, last_touch_ts, expiry_date, status, campaign_id,
                          created_at, updated_at
            """),
            {
                "id": existing.id,
                "partnership_id": partnership_id,
                "referral_code": referral_code,
                "source": source,
                "last_touch_ts": now,
                "expiry_date": expiry_date,
                "campaign_id": campaign_id
            }
        )
    else:
        # Create new referral
        result = await db.execute(
            text("""
                INSERT INTO referrals (
                    user_id, partnership_id, referral_code, source,
                    first_touch_ts, last_touch_ts, expiry_date, status, campaign_id
                )
                VALUES (
                    :user_id, :partnership_id, :referral_code, :source,
                    :first_touch_ts, :last_touch_ts, :expiry_date, :status, :campaign_id
                )
                RETURNING id, user_id, partnership_id, referral_code, source,
                          first_touch_ts, last_touch_ts, expiry_date, status, campaign_id,
                          created_at, updated_at
            """),
            {
                "user_id": user_id,
                "partnership_id": partnership_id,
                "referral_code": referral_code,
                "source": source,
                "first_touch_ts": now,
                "last_touch_ts": now,
                "expiry_date": expiry_date,
                "status": ReferralStatus.PENDING.value,
                "campaign_id": campaign_id
            }
        )
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create referral")
    
    row_dict = dict(row)
    row_dict["status"] = ReferralStatus(row_dict["status"])
    return ReferralInDB(**row_dict)


async def get_referral_by_id(db, referral_id: UUID) -> Optional[ReferralInDB]:
    """Get referral by ID"""
    result = await db.execute(
        text("""
            SELECT id, user_id, partnership_id, referral_code, source,
                   first_touch_ts, last_touch_ts, expiry_date, status, campaign_id,
                   created_at, updated_at
            FROM referrals WHERE id = :id
        """),
        {"id": referral_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    row_dict = dict(row)
    row_dict["status"] = ReferralStatus(row_dict["status"])
    return ReferralInDB(**row_dict)


async def get_referral_by_user(db, user_id: UUID) -> Optional[ReferralInDB]:
    """Get user's referral attribution"""
    result = await db.execute(
        text("""
            SELECT id, user_id, partnership_id, referral_code, source,
                   first_touch_ts, last_touch_ts, expiry_date, status, campaign_id,
                   created_at, updated_at
            FROM referrals
            WHERE user_id = :user_id
            ORDER BY last_touch_ts DESC
            LIMIT 1
        """),
        {"user_id": user_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    row_dict = dict(row)
    row_dict["status"] = ReferralStatus(row_dict["status"])
    return ReferralInDB(**row_dict)


async def lock_referral(db, referral_id: UUID) -> ReferralInDB:
    """Lock referral attribution (immutable after payment)"""
    result = await db.execute(
        text("""
            UPDATE referrals
            SET status = :status,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND status = :pending_status
            RETURNING id, user_id, partnership_id, referral_code, source,
                      first_touch_ts, last_touch_ts, expiry_date, status, campaign_id,
                      created_at, updated_at
        """),
        {
            "id": referral_id,
            "status": ReferralStatus.LOCKED.value,
            "pending_status": ReferralStatus.PENDING.value
        }
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found or already locked")
    
    row_dict = dict(row)
    row_dict["status"] = ReferralStatus(row_dict["status"])
    return ReferralInDB(**row_dict)


async def lock_referral_by_user(db, user_id: UUID) -> Optional[ReferralInDB]:
    """Lock referral for user (called on payment)"""
    referral = await get_referral_by_user(db, user_id)
    if not referral:
        return None
    
    if referral.status == ReferralStatus.LOCKED:
        return referral
    
    return await lock_referral(db, referral.id)


async def expire_referrals(db):
    """Expire referrals past their expiry date"""
    result = await db.execute(
        text("""
            UPDATE referrals
            SET status = :expired_status,
                updated_at = CURRENT_TIMESTAMP
            WHERE status = :pending_status
            AND expiry_date < CURRENT_TIMESTAMP
        """),
        {
            "expired_status": ReferralStatus.EXPIRED.value,
            "pending_status": ReferralStatus.PENDING.value
        }
    )
    return result.rowcount

