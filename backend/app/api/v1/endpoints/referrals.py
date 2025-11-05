"""
Referrals Endpoints - Attribution tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from uuid import UUID

from app.core.database import get_database
from app.services.auth_service import get_current_active_user
from app.models.user import UserInDB
from app.models.referral import Referral, ReferralTrackRequest, ReferralTrackResponse, ReferralStatus
from app.models.university import PartnershipModelType, PartnershipStatus
from app.services import attribution_service, partnership_service

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.post("/track", response_model=ReferralTrackResponse)
async def track_referral(
    track_data: ReferralTrackRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Track referral link click (sets cookie/session)"""
    # Find partnership by referral code
    university = await partnership_service.get_university_by_slug(db, track_data.referral_code)
    if not university:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid referral code")
    
    # Get active partnership for this university
    partnerships = await partnership_service.list_partnerships(
        db,
        university_id=university.id,
        model_type=PartnershipModelType.REVENUE_SHARE,
        status_filter=PartnershipStatus.ACTIVE
    )
    
    if not partnerships:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active partnership found")
    
    partnership = partnerships[0]
    
    # Create or update referral
    referral = await attribution_service.create_referral(
        db,
        user_id=current_user.id,
        partnership_id=partnership.id,
        referral_code=track_data.referral_code,
        source=track_data.source,
        campaign_id=track_data.campaign_id
    )
    
    return ReferralTrackResponse(
        referral_id=referral.id,
        partnership_id=referral.partnership_id,
        status=referral.status,
        expiry_date=referral.expiry_date
    )


@router.get("/user/{user_id}", response_model=Optional[Referral])
async def get_user_referral(
    user_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_database)
):
    """Get user's referral attribution"""
    # Check if user can access this referral
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    return await attribution_service.get_referral_by_user(db, user_id)


@router.put("/{referral_id}/lock", response_model=Referral)
async def lock_referral(
    referral_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),  # TODO: Add system/webhook check
    db = Depends(get_database)
):
    """Lock attribution on payment (immutable)"""
    return await attribution_service.lock_referral(db, referral_id)

