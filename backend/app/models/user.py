"""
User and User Profile Models
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8, max_length=100)
    mfa_enabled: bool = False


class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """User update model"""
    mfa_enabled: Optional[bool] = None


class UserInDB(UserBase):
    """User in database model"""
    id: UUID
    password_hash: str
    mfa_enabled: bool
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class User(UserBase):
    """User response model"""
    id: UUID
    mfa_enabled: bool
    is_active: bool
    email_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileBase(BaseModel):
    """Base user profile model"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    dob: Optional[datetime] = None
    residency_country: Optional[str] = Field(None, max_length=3)
    visa_class: Optional[str] = Field(None, max_length=20)
    ssn_last4: Optional[str] = Field(None, max_length=4)
    address_json: Optional[Dict[str, Any]] = None
    phone: Optional[str] = Field(None, max_length=20)


class UserProfileCreate(UserProfileBase):
    """User profile creation model"""
    itin: Optional[str] = None


class UserProfileUpdate(UserProfileBase):
    """User profile update model"""
    itin: Optional[str] = None


class UserProfileInDB(UserProfileBase):
    """User profile in database model"""
    user_id: UUID
    itin: Optional[str] = None  # Encrypted
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserProfile(UserProfileBase):
    """User profile response model"""
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# UserProfileWithITIN is used to return the user profile 
# with the decrypted ITIN for the API response. 
class UserProfileWithITIN(UserProfile):
    """User profile with decrypted ITIN"""
    itin: Optional[str] = None


class Token(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data model"""
    user_id: Optional[UUID] = None
    email: Optional[str] = None
