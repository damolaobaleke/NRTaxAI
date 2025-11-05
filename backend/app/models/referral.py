"""
Referral and Attribution Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class ReferralStatus(str, Enum):
    """Referral status"""
    PENDING = "pending"
    LOCKED = "locked"
    EXPIRED = "expired"


class ReferralBase(BaseModel):
    """Base referral model"""
    user_id: UUID
    partnership_id: UUID
    referral_code: str = Field(..., max_length=100)
    source: Optional[str] = Field(None, max_length=50)
    first_touch_ts: datetime
    last_touch_ts: datetime
    expiry_date: datetime
    status: ReferralStatus = ReferralStatus.PENDING
    campaign_id: Optional[str] = Field(None, max_length=100)


class ReferralCreate(BaseModel):
    """Referral creation model"""
    partnership_id: UUID
    referral_code: str = Field(..., max_length=100)
    source: Optional[str] = Field(None, max_length=50)
    campaign_id: Optional[str] = Field(None, max_length=100)
    expiry_days: int = Field(90, ge=1, le=365)  # Default 90 days


class ReferralUpdate(BaseModel):
    """Referral update model"""
    last_touch_ts: Optional[datetime] = None
    status: Optional[ReferralStatus] = None


class ReferralInDB(ReferralBase):
    """Referral in database model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Referral(ReferralBase):
    """Referral response model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ReferralTrackRequest(BaseModel):
    """Referral tracking request"""
    referral_code: str = Field(..., max_length=100)
    source: Optional[str] = Field(None, max_length=50)
    campaign_id: Optional[str] = Field(None, max_length=100)


class ReferralTrackResponse(BaseModel):
    """Referral tracking response"""
    referral_id: UUID
    partnership_id: UUID
    status: ReferralStatus
    expiry_date: datetime

