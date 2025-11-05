"""
License Service - Per-seat license management
"""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.license import (
    License, LicenseCreate, LicenseAllocateRequest, LicenseConsumeRequest,
    LicenseInDB, LicenseUsageStats,
    SeatType, LicenseStatus
)
from app.services.partnership_service import get_partnership_by_id


async def allocate_licenses(db, allocation_data: LicenseAllocateRequest) -> List[LicenseInDB]:
    """Allocate license seats for a partnership"""
    # Verify partnership exists
    partnership = await get_partnership_by_id(db, allocation_data.partnership_id)
    if not partnership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership not found")
    
    licenses = []
    for _ in range(allocation_data.seat_count):
        result = await db.execute(
            text("""
                INSERT INTO licenses (
                    partnership_id, user_id, seat_type, status, expiry_date
                )
                VALUES (
                    :partnership_id, :user_id, :seat_type, :status, :expiry_date
                )
                RETURNING id, partnership_id, user_id, seat_type, status,
                          allocated_at, consumed_at, expiry_date, created_at
            """),
            {
                "partnership_id": allocation_data.partnership_id,
                "user_id": None,  # Will be assigned when consumed
                "seat_type": allocation_data.seat_type.value,
                "status": LicenseStatus.ACTIVE.value,
                "expiry_date": allocation_data.expiry_date
            }
        )
        row = result.fetchone()
        if row:
            row_dict = dict(row)
            row_dict["seat_type"] = SeatType(row_dict["seat_type"])
            row_dict["status"] = LicenseStatus(row_dict["status"])
            licenses.append(LicenseInDB(**row_dict))
    
    return licenses


async def consume_license(db, consume_data: LicenseConsumeRequest) -> LicenseInDB:
    """Consume a license seat for a user"""
    # Find available license
    result = await db.execute(
        text("""
            SELECT id, partnership_id, user_id, seat_type, status,
                   allocated_at, consumed_at, expiry_date, created_at
            FROM licenses
            WHERE partnership_id = :partnership_id
            AND status = :status
            AND (user_id IS NULL OR user_id = :user_id)
            AND (expiry_date IS NULL OR expiry_date >= CURRENT_DATE)
            ORDER BY allocated_at ASC
            LIMIT 1
            FOR UPDATE
        """),
        {
            "partnership_id": consume_data.partnership_id,
            "user_id": consume_data.user_id,
            "status": LicenseStatus.ACTIVE.value
        }
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No available license seats found for this partnership"
        )
    
    # Consume the license
    result = await db.execute(
        text("""
            UPDATE licenses
            SET user_id = :user_id,
                status = :status,
                consumed_at = CURRENT_TIMESTAMP
            WHERE id = :id
            RETURNING id, partnership_id, user_id, seat_type, status,
                      allocated_at, consumed_at, expiry_date, created_at
        """),
        {
            "id": row["id"],
            "user_id": consume_data.user_id,
            "status": LicenseStatus.CONSUMED.value
        }
    )
    updated_row = result.fetchone()
    if not updated_row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to consume license")
    
    row_dict = dict(updated_row)
    row_dict["seat_type"] = SeatType(row_dict["seat_type"])
    row_dict["status"] = LicenseStatus(row_dict["status"])
    return LicenseInDB(**row_dict)


async def get_license_by_id(db, license_id: UUID) -> Optional[LicenseInDB]:
    """Get license by ID"""
    result = await db.execute(
        text("""
            SELECT id, partnership_id, user_id, seat_type, status,
                   allocated_at, consumed_at, expiry_date, created_at
            FROM licenses WHERE id = :id
        """),
        {"id": license_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    row_dict = dict(row)
    row_dict["seat_type"] = SeatType(row_dict["seat_type"])
    row_dict["status"] = LicenseStatus(row_dict["status"])
    return LicenseInDB(**row_dict)


async def list_licenses(
    db,
    partnership_id: UUID,
    status_filter: Optional[LicenseStatus] = None,
    seat_type: Optional[SeatType] = None,
    limit: int = 100
) -> List[LicenseInDB]:
    """List licenses for a partnership"""
    conditions = ["partnership_id = :partnership_id"]
    params = {"partnership_id": partnership_id, "limit": limit}
    
    if status_filter:
        conditions.append("status = :status")
        params["status"] = status_filter.value
    if seat_type:
        conditions.append("seat_type = :seat_type")
        params["seat_type"] = seat_type.value
    
    where_clause = "WHERE " + " AND ".join(conditions)
    
    result = await db.execute(
        text(f"""
            SELECT id, partnership_id, user_id, seat_type, status,
                   allocated_at, consumed_at, expiry_date, created_at
            FROM licenses
            {where_clause}
            ORDER BY allocated_at DESC
            LIMIT :limit
        """),
        params
    )
    
    rows = result.fetchall()
    licenses = []
    for row in rows:
        row_dict = dict(row)
        row_dict["seat_type"] = SeatType(row_dict["seat_type"])
        row_dict["status"] = LicenseStatus(row_dict["status"])
        licenses.append(LicenseInDB(**row_dict))
    
    return licenses


async def get_license_usage_stats(db, partnership_id: UUID) -> LicenseUsageStats:
    """Get license usage statistics for a partnership"""
    result = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total_allocated,
                COUNT(*) FILTER (WHERE status = 'consumed') as total_consumed,
                COUNT(*) FILTER (WHERE status = 'active') as total_active,
                COUNT(*) FILTER (WHERE status = 'expired') as total_expired,
                jsonb_object_agg(seat_type, COUNT(*)) FILTER (WHERE seat_type IS NOT NULL) as seats_by_type
            FROM licenses
            WHERE partnership_id = :partnership_id
        """),
        {"partnership_id": partnership_id}
    )
    row = result.fetchone()
    
    total_allocated = row["total_allocated"] or 0
    total_consumed = row["total_consumed"] or 0
    total_active = row["total_active"] or 0
    total_expired = row["total_expired"] or 0
    
    utilization_rate = (total_consumed / total_allocated * 100) if total_allocated > 0 else 0.0
    
    # Get seats by type
    seats_by_type_result = await db.execute(
        text("""
            SELECT seat_type, COUNT(*) as count
            FROM licenses
            WHERE partnership_id = :partnership_id
            GROUP BY seat_type
        """),
        {"partnership_id": partnership_id}
    )
    seats_by_type = {}
    for type_row in seats_by_type_result:
        seats_by_type[type_row["seat_type"]] = type_row["count"]
    
    return LicenseUsageStats(
        partnership_id=partnership_id,
        total_allocated=total_allocated,
        total_consumed=total_consumed,
        total_active=total_active,
        total_expired=total_expired,
        utilization_rate=utilization_rate,
        seats_by_type=seats_by_type
    )


async def expire_licenses(db):
    """Expire licenses past their expiry date"""
    result = await db.execute(
        text("""
            UPDATE licenses
            SET status = :expired_status
            WHERE status = :active_status
            AND expiry_date IS NOT NULL
            AND expiry_date < CURRENT_DATE
        """),
        {
            "expired_status": LicenseStatus.EXPIRED.value,
            "active_status": LicenseStatus.ACTIVE.value
        }
    )
    return result.rowcount

