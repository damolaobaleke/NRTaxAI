"""
Transaction Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum
from decimal import Decimal


class TransactionType(str, Enum):
    """Transaction types"""
    FILING_FEE = "filing_fee"
    LICENSE_PAYMENT = "license_payment"
    STATE_ADDON = "state_addon"


class TransactionStatus(str, Enum):
    """Transaction status"""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class TransactionBase(BaseModel):
    """Base transaction model"""
    user_id: UUID
    tax_return_id: Optional[UUID] = None
    partnership_id: Optional[UUID] = None
    referral_id: Optional[UUID] = None
    transaction_type: TransactionType
    amount: Decimal = Field(..., ge=0)
    currency: str = Field("USD", max_length=3)
    stripe_payment_intent_id: Optional[str] = Field(None, max_length=255)
    stripe_charge_id: Optional[str] = Field(None, max_length=255)
    status: TransactionStatus = TransactionStatus.PENDING
    platform_share: Optional[Decimal] = None
    cpa_share: Optional[Decimal] = None
    partner_share: Optional[Decimal] = None
    net_to_platform: Optional[Decimal] = None


class TransactionCreate(BaseModel):
    """Transaction creation model"""
    user_id: UUID
    tax_return_id: Optional[UUID] = None
    partnership_id: Optional[UUID] = None
    referral_id: Optional[UUID] = None
    transaction_type: TransactionType
    amount: float = Field(..., ge=0)
    currency: str = Field("USD", max_length=3)
    stripe_payment_intent_id: Optional[str] = Field(None, max_length=255)


class TransactionUpdate(BaseModel):
    """Transaction update model"""
    stripe_charge_id: Optional[str] = Field(None, max_length=255)
    status: Optional[TransactionStatus] = None
    platform_share: Optional[float] = None
    cpa_share: Optional[float] = None
    partner_share: Optional[float] = None
    net_to_platform: Optional[float] = None


class TransactionInDB(TransactionBase):
    """Transaction in database model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Transaction(TransactionBase):
    """Transaction response model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TransactionWithDetails(Transaction):
    """Transaction with additional details"""
    partnership_name: Optional[str] = None
    referral_code: Optional[str] = None

