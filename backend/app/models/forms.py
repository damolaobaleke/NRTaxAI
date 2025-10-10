"""
Forms Models (Tax Form Generation)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class FormType(str, Enum):
    """Tax form types"""
    FORM_1040NR = "1040NR"
    FORM_8843 = "8843"
    FORM_W8BEN = "W-8BEN"
    FORM_1040V = "1040-V"


class FormStatus(str, Enum):
    """Form status types"""
    GENERATED = "generated"
    SIGNED = "signed"
    FILED = "filed"
    REJECTED = "rejected"
    AMENDED = "amended"


class FormBase(BaseModel):
    """Base form model"""
    form_type: FormType
    status: FormStatus = FormStatus.GENERATED


class FormCreate(FormBase):
    """Form creation model"""
    return_id: UUID
    s3_key_pdf: str = Field(..., max_length=500)


class FormUpdate(BaseModel):
    """Form update model"""
    status: Optional[FormStatus] = None
    s3_key_pdf: Optional[str] = Field(None, max_length=500)
    checksum: Optional[str] = Field(None, max_length=64)


class FormInDB(FormBase):
    """Form in database model"""
    id: UUID
    return_id: UUID
    s3_key_pdf: str
    checksum: Optional[str] = Field(None, max_length=64)
    created_at: datetime
    
    class Config:
        from_attributes = True


class Form(FormBase):
    """Form response model"""
    id: UUID
    return_id: UUID
    s3_key_pdf: str
    checksum: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FormGenerationRequest(BaseModel):
    """Form generation request"""
    return_id: UUID
    form_types: List[FormType]
    include_signature_fields: bool = True
    watermark: Optional[str] = None


class FormGenerationResult(BaseModel):
    """Form generation result"""
    return_id: UUID
    forms_generated: List[Form]
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    total_processing_time_ms: int


class FormDownloadRequest(BaseModel):
    """Form download request"""
    return_id: UUID
    form_type: FormType
    include_signature: bool = False
    format: str = Field(default="pdf", regex="^(pdf|json)$")


class FormValidation(BaseModel):
    """Form validation result"""
    form_id: UUID
    form_type: FormType
    is_valid: bool
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    validation_rules_version: str
    validated_at: datetime


class FormMetadata(BaseModel):
    """Form metadata"""
    form_id: UUID
    form_type: FormType
    tax_year: int
    user_id: UUID
    return_id: UUID
    file_size_bytes: int
    page_count: int
    generation_version: str
    template_version: str
    checksum: str
    created_at: datetime
    updated_at: datetime


class FormTemplate(BaseModel):
    """Form template configuration"""
    form_type: FormType
    version: str
    template_path: str
    field_mappings: Dict[str, Any]
    validation_rules: Dict[str, Any]
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class FormFieldMapping(BaseModel):
    """Form field mapping configuration"""
    form_type: FormType
    field_name: str
    source_field: str
    transformation: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None
    required: bool = False
    default_value: Optional[Any] = None


class FormGenerationStatus(BaseModel):
    """Form generation status tracking"""
    return_id: UUID
    requested_forms: List[FormType]
    generated_forms: List[Form]
    failed_forms: List[Dict[str, Any]]
    status: str  # pending, processing, completed, failed
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
