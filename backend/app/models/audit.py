"""
Audit Log Models (Immutable Audit Trail)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ActorType(str, Enum):
    """Actor types for audit logs"""
    USER = "user"
    OPERATOR = "operator"
    SYSTEM = "system"
    API = "api"


class AuditAction(str, Enum):
    """Common audit actions"""
    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    USER_UPDATE_PROFILE = "user_update_profile"
    
    # Document actions
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_EXTRACT = "document_extract"
    DOCUMENT_VALIDATE = "document_validate"
    DOCUMENT_DELETE = "document_delete"
    
    # Tax return actions
    RETURN_CREATE = "return_create"
    RETURN_UPDATE = "return_update"
    RETURN_COMPUTE = "return_compute"
    RETURN_SUBMIT = "return_submit"
    
    # Review actions
    REVIEW_ASSIGN = "review_assign"
    REVIEW_APPROVE = "review_approve"
    REVIEW_REJECT = "review_reject"
    REVIEW_COMMENT = "review_comment"
    
    # Authorization actions
    AUTH_REQUEST = "auth_request"
    AUTH_SIGN = "auth_sign"
    AUTH_EXPIRE = "auth_expire"
    
    # Form actions
    FORM_GENERATE = "form_generate"
    FORM_DOWNLOAD = "form_download"
    FORM_EFILE = "form_efile"
    
    # System actions
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_ERROR = "system_error"


class AuditLogBase(BaseModel):
    """Base audit log model"""
    actor_type: ActorType
    actor_id: Optional[UUID] = None
    return_id: Optional[UUID] = None
    action: AuditAction
    payload_json: Optional[Dict[str, Any]] = None


class AuditLogCreate(AuditLogBase):
    """Audit log creation model"""
    hash: Optional[str] = None  # Will be computed if not provided


class AuditLogInDB(AuditLogBase):
    """Audit log in database model"""
    id: UUID
    hash: str = Field(..., max_length=64)  # SHA-256 hash
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLog(AuditLogBase):
    """Audit log response model"""
    id: UUID
    hash: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogWithActor(AuditLog):
    """Audit log with actor information"""
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None


class AuditTrail(BaseModel):
    """Complete audit trail for a tax return"""
    return_id: UUID
    logs: List[AuditLogWithActor]
    total_actions: int
    first_action: datetime
    last_action: datetime
    hash_chain_valid: bool
    integrity_verified: bool


class AuditBundle(BaseModel):
    """Exportable audit bundle"""
    return_id: UUID
    user_id: UUID
    tax_year: int
    created_at: datetime
    exported_at: datetime
    exported_by: UUID
    logs: List[AuditLogWithActor]
    documents: List[Dict[str, Any]]
    computations: List[Dict[str, Any]]
    reviews: List[Dict[str, Any]]
    authorizations: List[Dict[str, Any]]
    bundle_hash: str
    bundle_signature: Optional[str] = None


class HashChainValidation(BaseModel):
    """Hash chain validation result"""
    is_valid: bool
    invalid_entries: List[UUID]
    chain_breaks: List[int]  # Index positions where chain breaks
    computed_hash: str
    expected_hash: str


class AuditSearch(BaseModel):
    """Audit log search parameters"""
    return_id: Optional[UUID] = None
    actor_type: Optional[ActorType] = None
    actor_id: Optional[UUID] = None
    action: Optional[AuditAction] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditStats(BaseModel):
    """Audit statistics"""
    total_logs: int
    logs_by_actor_type: Dict[str, int]
    logs_by_action: Dict[str, int]
    logs_by_date: Dict[str, int]  # YYYY-MM-DD format
    hash_chain_status: HashChainValidation
    last_audit_check: datetime
