"""
Universities Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
from app.models.university import (
    University, UniversityCreate, UniversityUpdate, UniversityStatus
)
from app.services import partnership_service

router = APIRouter(prefix="/universities", tags=["universities"])


@router.post("", response_model=University, status_code=status.HTTP_201_CREATED)
async def create_university(
    university_data: UniversityCreate,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Create a new university partner"""
    return await partnership_service.create_university(db, university_data)


@router.get("", response_model=List[University])
async def list_universities(
    status_filter: Optional[UniversityStatus] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """List all universities"""
    return await partnership_service.list_universities(db, status_filter)


@router.get("/{university_id}", response_model=University)
async def get_university(
    university_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get university by ID"""
    university = await partnership_service.get_university_by_id(db, university_id)
    if not university:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")
    return university


@router.get("/slug/{slug}", response_model=University)
async def get_university_by_slug(
    slug: str,
    db = Depends(get_database)
):
    """Get university by slug (for tenant resolution)"""
    university = await partnership_service.get_university_by_slug(db, slug)
    if not university:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")
    return university


@router.patch("/{university_id}", response_model=University)
async def update_university(
    university_id: UUID,
    university_data: UniversityUpdate,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add admin check
    db = Depends(get_database)
):
    """Update university information"""
    return await partnership_service.update_university(db, university_id, university_data)

