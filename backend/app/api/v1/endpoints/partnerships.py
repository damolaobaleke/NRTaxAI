"""
Partnerships Endpoints
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
from app.models.university import (
    Partnership, PartnershipCreate, PartnershipUpdate,
    PartnershipModelType, PartnershipStatus
)
from app.services import partnership_service

router = APIRouter(prefix="/partnerships", tags=["partnerships"])


@router.post("", response_model=Partnership, status_code=status.HTTP_201_CREATED)
async def create_partnership(
    partnership_data: PartnershipCreate,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Create a new partnership contract"""
    return await partnership_service.create_partnership(db, partnership_data)


@router.get("", response_model=List[Partnership])
async def list_partnerships(
    university_id: Optional[UUID] = Query(None),
    model_type: Optional[PartnershipModelType] = Query(None),
    status_filter: Optional[PartnershipStatus] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """List partnerships with optional filters"""
    return await partnership_service.list_partnerships(db, university_id, model_type, status_filter)


@router.get("/{partnership_id}", response_model=Partnership)
async def get_partnership(
    partnership_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get partnership details"""
    partnership = await partnership_service.get_partnership_by_id(db, partnership_id)
    if not partnership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership not found")
    return partnership


@router.patch("/{partnership_id}", response_model=Partnership)
async def update_partnership(
    partnership_id: UUID,
    partnership_data: PartnershipUpdate,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Update partnership contract"""
    return await partnership_service.update_partnership(db, partnership_id, partnership_data)


@router.post("/{partnership_id}/renew", response_model=Partnership)
async def renew_partnership(
    partnership_id: UUID,
    new_end_date: date,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Renew partnership contract"""
    return await partnership_service.renew_partnership(db, partnership_id, new_end_date)

