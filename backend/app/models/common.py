"""
Common Models and Utilities
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from uuid import UUID
from enum import Enum


class HealthStatus(BaseModel):
    """Health check status"""
    status: str = "healthy"
    timestamp: datetime
    version: str
    database: str = "connected"
    redis: str = "connected"
    s3: str = "connected"
    textract: str = "connected"
    openai: str = "connected"


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response"""
    message: str
    data: Optional[Any] = None
    timestamp: datetime


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool


class FileUpload(BaseModel):
    """File upload metadata"""
    filename: str
    content_type: str
    size_bytes: int
    upload_url: str
    expires_at: datetime
    fields: Optional[Dict[str, str]] = None


class DocumentType(str, Enum):
    """Supported document types"""
    W2 = "W2"
    FORM_1099_INT = "1099INT"
    FORM_1099_NEC = "1099NEC"
    FORM_1099_DIV = "1099DIV"
    FORM_1099_G = "1099G"
    FORM_1099_MISC = "1099MISC"
    FORM_1099_B = "1099B"
    FORM_1099_R = "1099R"
    FORM_1098_T = "1098T"
    FORM_1042_S = "1042S"


class VisaClass(str, Enum):
    """Supported visa classes"""
    H1B = "H1B"
    F1 = "F-1"
    O1 = "O-1"
    OPT = "OPT"
    J1 = "J-1"
    TN = "TN"
    E2 = "E-2"
    L1 = "L-1"
    B1 = "B-1"
    B2 = "B-2"


class TaxYear(BaseModel):
    """Tax year information"""
    year: int = Field(..., ge=2020, le=2030)
    is_current: bool
    filing_deadline: datetime
    extension_deadline: datetime


class NotificationType(str, Enum):
    """Notification types"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Notification(BaseModel):
    """System notification"""
    id: UUID
    type: NotificationType
    title: str
    message: str
    user_id: Optional[UUID] = None
    operator_id: Optional[UUID] = None
    return_id: Optional[UUID] = None
    is_read: bool = False
    created_at: datetime
    expires_at: Optional[datetime] = None


class SystemSettings(BaseModel):
    """System configuration settings"""
    maintenance_mode: bool = False
    registration_enabled: bool = True
    file_upload_enabled: bool = True
    chat_enabled: bool = True
    max_file_size_mb: int = 10
    max_files_per_upload: int = 10
    session_timeout_minutes: int = 30
    password_min_length: int = 8
    require_mfa: bool = False


class Metrics(BaseModel):
    """System metrics"""
    total_users: int
    total_returns: int
    total_documents: int
    total_chat_sessions: int
    active_operators: int
    pending_reviews: int
    system_uptime_hours: float
    avg_response_time_ms: float
    error_rate_percent: float
    last_updated: datetime


class CountryCode(BaseModel):
    """Country code information"""
    code: str = Field(..., min_length=2, max_length=3)  # ISO country code
    name: str
    has_tax_treaty: bool
    treaty_articles: List[str] = Field(default_factory=list)


class Address(BaseModel):
    """Address information"""
    street: str
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    is_foreign: bool = False


class ContactInfo(BaseModel):
    """Contact information"""
    email: str
    phone: Optional[str] = None
    address: Optional[Address] = None


class ValidationRule(BaseModel):
    """Validation rule definition"""
    field: str
    rule_type: str  # "required", "format", "range", "custom"
    parameters: Dict[str, Any]
    error_message: str
    severity: str = "error"  # "error", "warning", "info"


class ProcessingStatus(BaseModel):
    """Processing status tracking"""
    status: str  # "pending", "processing", "completed", "failed"
    progress_percent: int = Field(..., ge=0, le=100)
    current_step: str
    total_steps: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
