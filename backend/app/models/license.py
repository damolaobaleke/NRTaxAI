"""
License Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from enum import Enum


class SeatType(str, Enum):
    """Seat types"""
    PRE_PURCHASE = "pre_purchase"
    POST_USAGE = "post_usage"


class LicenseStatus(str, Enum):
    """License status"""
    ACTIVE = "active"
    CONSUMED = "consumed"
    EXPIRED = "expired"


class LicenseBase(BaseModel):
    """Base license model"""
    partnership_id: UUID
    user_id: Optional[UUID] = None
    seat_type: SeatType
    status: LicenseStatus = LicenseStatus.ACTIVE
    allocated_at: datetime
    consumed_at: Optional[datetime] = None
    expiry_date: Optional[date] = None


class LicenseCreate(BaseModel):
    """License creation model"""
    partnership_id: UUID
    user_id: Optional[UUID] = None
    seat_type: SeatType
    expiry_date: Optional[date] = None


class LicenseAllocateRequest(BaseModel):
    """License allocation request"""
    partnership_id: UUID
    seat_count: int = Field(..., gt=0, le=10000)
    seat_type: SeatType = SeatType.PRE_PURCHASE
    expiry_date: Optional[date] = None


class LicenseConsumeRequest(BaseModel):
    """License consumption request"""
    user_id: UUID
    partnership_id: UUID


class LicenseUpdate(BaseModel):
    """License update model"""
    user_id: Optional[UUID] = None
    status: Optional[LicenseStatus] = None
    consumed_at: Optional[datetime] = None


class LicenseInDB(LicenseBase):
    """License in database model"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class License(LicenseBase):
    """License response model"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class LicenseUsageStats(BaseModel):
    """License usage statistics"""
    partnership_id: UUID
    total_allocated: int
    total_consumed: int
    total_active: int
    total_expired: int
    utilization_rate: float  # Percentage
    seats_by_type: dict[str, int]

