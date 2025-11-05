"""
Payout Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from enum import Enum
from decimal import Decimal


class PayoutMethod(str, Enum):
    """Payout methods"""
    STRIPE_CONNECT = "stripe_connect"
    ACH = "ach"


class PayoutStatus(str, Enum):
    """Payout status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PayoutBase(BaseModel):
    """Base payout model"""
    partnership_id: UUID
    period_start: date
    period_end: date
    total_transactions: int = Field(0, ge=0)
    gross_amount: Decimal = Field(..., ge=0)
    commission_percent: Decimal = Field(..., ge=0, le=100)
    commission_amount: Decimal = Field(..., ge=0)
    payout_method: Optional[PayoutMethod] = None
    payout_status: PayoutStatus = PayoutStatus.PENDING
    stripe_transfer_id: Optional[str] = Field(None, max_length=255)
    ach_reference: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class PayoutCreate(BaseModel):
    """Payout creation model"""
    partnership_id: UUID
    period_start: date
    period_end: date
    payout_method: Optional[PayoutMethod] = None
    notes: Optional[str] = None


class PayoutUpdate(BaseModel):
    """Payout update model"""
    payout_status: Optional[PayoutStatus] = None
    stripe_transfer_id: Optional[str] = Field(None, max_length=255)
    ach_reference: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    paid_at: Optional[datetime] = None


class PayoutInDB(PayoutBase):
    """Payout in database model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Payout(PayoutBase):
    """Payout response model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PayoutCalculation(BaseModel):
    """Payout calculation result"""
    partnership_id: UUID
    period_start: date
    period_end: date
    total_transactions: int
    gross_amount: Decimal
    commission_percent: Decimal
    commission_amount: Decimal
    transaction_ids: list[UUID]


class PayoutWithPartnership(Payout):
    """Payout with partnership details"""
    partnership_name: Optional[str] = None
    university_name: Optional[str] = None

