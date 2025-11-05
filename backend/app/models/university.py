"""
University and Partnership Models
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime, date
from uuid import UUID
from enum import Enum


class UniversityStatus(str, Enum):
    """University status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UniversityBase(BaseModel):
    """Base university model"""
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100)
    domain: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    colors_json: Optional[Dict[str, Any]] = None
    contact_email: Optional[EmailStr] = None
    status: UniversityStatus = UniversityStatus.ACTIVE


class UniversityCreate(UniversityBase):
    """University creation model"""
    pass


class UniversityUpdate(BaseModel):
    """University update model"""
    name: Optional[str] = Field(None, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    colors_json: Optional[Dict[str, Any]] = None
    contact_email: Optional[EmailStr] = None
    status: Optional[UniversityStatus] = None


class UniversityInDB(UniversityBase):
    """University in database model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class University(UniversityBase):
    """University response model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PartnershipModelType(str, Enum):
    """Partnership model types"""
    SAAS_LICENSE = "saas_license"
    REVENUE_SHARE = "revenue_share"
    AFFILIATE = "affiliate"


class PartnershipStatus(str, Enum):
    """Partnership status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PartnershipBase(BaseModel):
    """Base partnership model"""
    university_id: UUID
    model_type: PartnershipModelType
    pricing_tier: Optional[int] = None  # 1, 2, 3 (based on enrollment size)
    price_per_seat: Optional[float] = None  # For SaaS license model
    commission_percent: Optional[float] = None  # For revenue-share model (e.g., 10.00)
    contract_start: date
    contract_end: Optional[date] = None
    status: PartnershipStatus = PartnershipStatus.ACTIVE
    metadata_json: Optional[Dict[str, Any]] = None


class PartnershipCreate(PartnershipBase):
    """Partnership creation model"""
    pass


class PartnershipUpdate(BaseModel):
    """Partnership update model"""
    pricing_tier: Optional[int] = None
    price_per_seat: Optional[float] = None
    commission_percent: Optional[float] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    status: Optional[PartnershipStatus] = None
    metadata_json: Optional[Dict[str, Any]] = None


class PartnershipInDB(PartnershipBase):
    """Partnership in database model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Partnership(PartnershipBase):
    """Partnership response model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PartnershipWithUniversity(Partnership):
    """Partnership with university details"""
    university: University
    
    class Config:
        from_attributes = True


class UniversityAdminRole(str, Enum):
    """University admin roles"""
    ADMIN = "admin"
    VIEWER = "viewer"


class UniversityAdminBase(BaseModel):
    """Base university admin model"""
    user_id: UUID
    partnership_id: UUID
    role: UniversityAdminRole = UniversityAdminRole.VIEWER


class UniversityAdminCreate(UniversityAdminBase):
    """University admin creation model"""
    pass


class UniversityAdminInDB(UniversityAdminBase):
    """University admin in database model"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class UniversityAdmin(UniversityAdminBase):
    """University admin response model"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

