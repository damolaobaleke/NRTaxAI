"""
Operator Models (PTIN Holders)
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class OperatorBase(BaseModel):
    """Base operator model"""
    email: EmailStr
    ptin: str = Field(..., min_length=9, max_length=20)  # PTIN format validation
    roles: List[str] = Field(default_factory=list)  # ['reviewer', 'admin']


class OperatorCreate(OperatorBase):
    """Operator creation model"""
    pass


class OperatorUpdate(BaseModel):
    """Operator update model"""
    email: Optional[EmailStr] = None
    ptin: Optional[str] = Field(None, min_length=9, max_length=20)
    roles: Optional[List[str]] = None
    status: Optional[str] = Field(None, max_length=20)


class OperatorInDB(OperatorBase):
    """Operator in database model"""
    id: UUID
    status: str = Field("active", max_length=20)
    created_at: datetime
    
    class Config:
        from_attributes = True


class Operator(OperatorBase):
    """Operator response model"""
    id: UUID
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class OperatorWithStats(Operator):
    """Operator with review statistics"""
    total_reviews: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    needs_revision_count: int = 0
    avg_review_time_hours: Optional[float] = None
    last_review_at: Optional[datetime] = None


class ReviewBase(BaseModel):
    """Base review model"""
    decision: str = Field(..., max_length=20)  # approved, rejected, needs_revision
    comments: Optional[str] = None
    diffs_json: Optional[Dict[str, Any]] = None


class ReviewCreate(ReviewBase):
    """Review creation model"""
    return_id: UUID
    operator_id: UUID


class ReviewUpdate(BaseModel):
    """Review update model"""
    decision: Optional[str] = Field(None, max_length=20)
    comments: Optional[str] = None
    diffs_json: Optional[Dict[str, Any]] = None


class ReviewInDB(ReviewBase):
    """Review in database model"""
    id: UUID
    return_id: UUID
    operator_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class Review(ReviewBase):
    """Review response model"""
    id: UUID
    return_id: UUID
    operator_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReviewWithDetails(Review):
    """Review with operator and return details"""
    operator: Optional[Operator] = None
    return_info: Optional[Dict[str, Any]] = None


class ReviewQueueItem(BaseModel):
    """Review queue item for operators"""
    return_id: UUID
    tax_year: int
    user_email: str
    user_name: str
    visa_class: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    has_issues: bool = False
    validation_count: int = 0
    document_count: int = 0
