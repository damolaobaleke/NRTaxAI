"""
Authorization Models (User Sign-off for Tax Returns)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class AuthorizationMethod(str, Enum):
    """Authorization method types"""
    ESIGN = "esign"
    WET_SIGN = "wet_sign"
    PHONE = "phone"
    EMAIL = "email"


class AuthorizationStatus(str, Enum):
    """Authorization status types"""
    PENDING = "pending"
    SENT = "sent"
    SIGNED = "signed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AuthorizationBase(BaseModel):
    """Base authorization model"""
    method: AuthorizationMethod
    status: AuthorizationStatus = AuthorizationStatus.PENDING


class AuthorizationCreate(AuthorizationBase):
    """Authorization creation model"""
    return_id: UUID
    evidence_json: Optional[Dict[str, Any]] = None


class AuthorizationUpdate(BaseModel):
    """Authorization update model"""
    status: Optional[AuthorizationStatus] = None
    evidence_json: Optional[Dict[str, Any]] = None
    signed_at: Optional[datetime] = None


class AuthorizationInDB(AuthorizationBase):
    """Authorization in database model"""
    id: UUID
    return_id: UUID
    signed_at: Optional[datetime] = None
    evidence_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Authorization(AuthorizationBase):
    """Authorization response model"""
    id: UUID
    return_id: UUID
    signed_at: Optional[datetime] = None
    evidence_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuthorizationRequest(BaseModel):
    """Authorization request model for users"""
    return_id: UUID
    method: AuthorizationMethod
    message: Optional[str] = None
    expires_hours: int = Field(default=72, ge=1, le=168)  # 1 hour to 1 week


class AuthorizationConfirmation(BaseModel):
    """Authorization confirmation model"""
    return_id: UUID
    authorization_id: UUID
    confirmation_code: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


class Form8879Equivalent(BaseModel):
    """Form 8879 equivalent for electronic signature"""
    return_id: UUID
    authorization_id: UUID
    taxpayer_signature: str  # Encrypted signature data
    preparer_signature: Optional[str] = None  # If self-prepared
    signature_date: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    evidence_json: Dict[str, Any]
    
    class Config:
        from_attributes = True


class AuthorizationSummary(BaseModel):
    """Authorization summary for return"""
    return_id: UUID
    current_status: AuthorizationStatus
    method: AuthorizationMethod
    created_at: datetime
    signed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_expired: bool = False
    days_remaining: Optional[int] = None
