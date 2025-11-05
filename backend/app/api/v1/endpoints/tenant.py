"""
Tenant Resolution Endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from app.core.database import get_database
from app.models.university import University
from app.services import partnership_service

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/resolve/{slug}", response_model=University)
async def resolve_tenant(
    slug: str,
    db = Depends(get_database)
):
    """Resolve university by slug, return branding config"""
    university = await partnership_service.get_university_by_slug(db, slug)
    if not university:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")
    return university

