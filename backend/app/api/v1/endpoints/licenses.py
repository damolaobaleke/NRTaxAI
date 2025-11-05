"""
Licenses Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
from app.models.license import (
    License, LicenseAllocateRequest, LicenseConsumeRequest,
    LicenseUsageStats, SeatType, LicenseStatus
)
from app.services import license_service

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.post("/partnerships/{partnership_id}/allocate", response_model=List[License], status_code=status.HTTP_201_CREATED)
async def allocate_licenses(
    partnership_id: UUID,
    allocation_data: LicenseAllocateRequest,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Allocate license seats"""
    allocation_data.partnership_id = partnership_id
    return await license_service.allocate_licenses(db, allocation_data)


@router.get("/partnerships/{partnership_id}/licenses", response_model=List[License])
async def list_partnership_licenses(
    partnership_id: UUID,
    status_filter: Optional[LicenseStatus] = Query(None),
    seat_type: Optional[SeatType] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin/university admin check
    db = Depends(get_database)
):
    """List licenses for a partnership"""
    return await license_service.list_licenses(db, partnership_id, status_filter, seat_type, limit)


@router.post("/consume", response_model=License, status_code=status.HTTP_200_OK)
async def consume_license(
    consume_data: LicenseConsumeRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Consume a license seat"""
    # Verify user owns the request
    if consume_data.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    return await license_service.consume_license(db, consume_data)


@router.get("/usage", response_model=LicenseUsageStats)
async def get_license_usage(
    partnership_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin/university admin check
    db = Depends(get_database)
):
    """Get license usage statistics"""
    return await license_service.get_license_usage_stats(db, partnership_id)

