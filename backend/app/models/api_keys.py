"""
API Keys Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class ApiKeyScope(str, Enum):
    """API key scopes"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    AUDIT = "audit"


class ApiKeyStatus(str, Enum):
    """API key status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ApiKeyBase(BaseModel):
    """Base API key model"""
    scopes: List[ApiKeyScope] = Field(default_factory=list)
    description: Optional[str] = Field(None, max_length=500)


class ApiKeyCreate(ApiKeyBase):
    """API key creation model"""
    owner_id: UUID
    expires_at: Optional[datetime] = None


class ApiKeyUpdate(BaseModel):
    """API key update model"""
    scopes: Optional[List[ApiKeyScope]] = None
    description: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None
    status: Optional[ApiKeyStatus] = None


class ApiKeyInDB(ApiKeyBase):
    """API key in database model"""
    id: UUID
    owner_id: UUID
    key_hash: str = Field(..., max_length=255)  # Hashed API key
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class ApiKey(ApiKeyBase):
    """API key response model (without hash)"""
    id: UUID
    owner_id: UUID
    status: ApiKeyStatus
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class ApiKeyWithSecret(ApiKey):
    """API key with secret (only returned on creation)"""
    key_secret: str  # Only returned when creating a new key
    expires_in_days: Optional[int] = None


class ApiKeyUsage(BaseModel):
    """API key usage statistics"""
    key_id: UUID
    date: datetime
    request_count: int = 0
    error_count: int = 0
    bandwidth_bytes: int = 0
    endpoint_usage: Dict[str, int] = Field(default_factory=dict)


class ApiKeyValidation(BaseModel):
    """API key validation result"""
    is_valid: bool
    key_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    scopes: List[ApiKeyScope] = []
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ApiKeyRequest(BaseModel):
    """API key request"""
    api_key: str = Field(..., min_length=32, max_length=128)


class ApiKeyStats(BaseModel):
    """API key statistics"""
    total_keys: int
    active_keys: int
    expired_keys: int
    revoked_keys: int
    total_requests: int
    total_errors: int
    top_used_endpoints: List[Dict[str, Any]]
    usage_by_date: Dict[str, int]  # YYYY-MM-DD format
