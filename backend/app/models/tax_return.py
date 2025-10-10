"""
Tax Return Models
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class TaxReturnBase(BaseModel):
    """Base tax return model"""
    tax_year: int = Field(..., ge=2020, le=2030)
    status: str = Field("draft", max_length=30)


class TaxReturnCreate(TaxReturnBase):
    """Tax return creation model"""
    pass


class TaxReturnUpdate(BaseModel):
    """Tax return update model"""
    status: Optional[str] = Field(None, max_length=30)
    ruleset_version: Optional[str] = None
    residency_result_json: Optional[Dict[str, Any]] = None
    treaty_json: Optional[Dict[str, Any]] = None
    totals_json: Optional[Dict[str, Any]] = None


class TaxReturnInDB(TaxReturnBase):
    """Tax return in database model"""
    id: UUID
    user_id: UUID
    ruleset_version: Optional[str] = None
    residency_result_json: Optional[Dict[str, Any]] = None
    treaty_json: Optional[Dict[str, Any]] = None
    totals_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaxReturn(TaxReturnBase):
    """Tax return response model"""
    id: UUID
    user_id: UUID
    ruleset_version: Optional[str] = None
    residency_result_json: Optional[Dict[str, Any]] = None
    treaty_json: Optional[Dict[str, Any]] = None
    totals_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    """Base document model"""
    s3_key: str = Field(..., max_length=500)
    doc_type: str = Field(..., max_length=20)  # W2, 1099INT, 1099NEC, 1098T
    source: Optional[str] = Field(None, max_length=50)


class DocumentCreate(DocumentBase):
    """Document creation model"""
    return_id: Optional[UUID] = None


class DocumentUpdate(BaseModel):
    """Document update model"""
    status: Optional[str] = Field(None, max_length=20)
    textract_job_id: Optional[str] = Field(None, max_length=100)
    extracted_json: Optional[Dict[str, Any]] = None
    validation_json: Optional[Dict[str, Any]] = None


class DocumentInDB(DocumentBase):
    """Document in database model"""
    id: UUID
    user_id: UUID
    return_id: Optional[UUID] = None
    status: str = Field("uploaded", max_length=20)
    textract_job_id: Optional[str] = Field(None, max_length=100)
    extracted_json: Optional[Dict[str, Any]] = None
    validation_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Document(DocumentBase):
    """Document response model"""
    id: UUID
    user_id: UUID
    return_id: Optional[UUID] = None
    status: str
    extracted_json: Optional[Dict[str, Any]] = None
    validation_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ValidationBase(BaseModel):
    """Base validation model"""
    severity: str = Field(..., max_length=20)  # error, warning, info
    field: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    message: str = Field(..., max_length=500)
    data_path: Optional[str] = Field(None, max_length=200)


class ValidationCreate(ValidationBase):
    """Validation creation model"""
    return_id: UUID


class ValidationInDB(ValidationBase):
    """Validation in database model"""
    id: UUID
    return_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class Validation(ValidationBase):
    """Validation response model"""
    id: UUID
    return_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ComputationBase(BaseModel):
    """Base computation model"""
    line_code: str = Field(..., max_length=20)
    description: str = Field(..., max_length=200)
    amount: float
    source: Optional[str] = Field(None, max_length=100)


class ComputationCreate(ComputationBase):
    """Computation creation model"""
    return_id: UUID


class ComputationInDB(ComputationBase):
    """Computation in database model"""
    id: UUID
    return_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class Computation(ComputationBase):
    """Computation response model"""
    id: UUID
    return_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class TaxReturnSummary(BaseModel):
    """Tax return summary model"""
    return_info: TaxReturn
    documents: List[Document]
    validations: List[Validation]
    computations: List[Computation]
    total_income: Optional[float] = None
    total_tax: Optional[float] = None
    total_withholding: Optional[float] = None
    refund_or_balance_due: Optional[float] = None
