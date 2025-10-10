"""
Feature Flags Models
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from enum import Enum


class FeatureFlagType(str, Enum):
    """Feature flag types"""
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"
    LIST = "list"


class FeatureFlagBase(BaseModel):
    """Base feature flag model"""
    key: str = Field(..., min_length=1, max_length=100)
    value_json: Dict[str, Any]
    description: Optional[str] = Field(None, max_length=500)


class FeatureFlagCreate(FeatureFlagBase):
    """Feature flag creation model"""
    pass


class FeatureFlagUpdate(BaseModel):
    """Feature flag update model"""
    value_json: Optional[Dict[str, Any]] = None
    description: Optional[str] = Field(None, max_length=500)


class FeatureFlagInDB(FeatureFlagBase):
    """Feature flag in database model"""
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FeatureFlag(FeatureFlagBase):
    """Feature flag response model"""
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BooleanFeatureFlag(BaseModel):
    """Boolean feature flag"""
    key: str
    enabled: bool
    description: Optional[str] = None
    updated_at: datetime


class StringFeatureFlag(BaseModel):
    """String feature flag"""
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime


class NumberFeatureFlag(BaseModel):
    """Number feature flag"""
    key: str
    value: Union[int, float]
    description: Optional[str] = None
    updated_at: datetime


class JsonFeatureFlag(BaseModel):
    """JSON feature flag"""
    key: str
    value: Dict[str, Any]
    description: Optional[str] = None
    updated_at: datetime


class ListFeatureFlag(BaseModel):
    """List feature flag"""
    key: str
    value: List[Any]
    description: Optional[str] = None
    updated_at: datetime


class FeatureFlagEvaluation(BaseModel):
    """Feature flag evaluation result"""
    key: str
    value: Any
    type: FeatureFlagType
    is_enabled: bool
    evaluated_at: datetime


class FeatureFlagOverride(BaseModel):
    """Feature flag override for specific users"""
    flag_key: str
    user_id: Optional[str] = None  # Override for specific user
    operator_id: Optional[str] = None  # Override for specific operator
    override_value: Any
    expires_at: Optional[datetime] = None
    created_at: datetime


class FeatureFlagAudit(BaseModel):
    """Feature flag audit log"""
    flag_key: str
    old_value: Any
    new_value: Any
    changed_by: str  # User/operator ID
    change_reason: Optional[str] = None
    changed_at: datetime


class FeatureFlagUsage(BaseModel):
    """Feature flag usage statistics"""
    flag_key: str
    evaluation_count: int
    user_evaluations: int
    operator_evaluations: int
    system_evaluations: int
    last_evaluated: datetime


class FeatureFlagBatch(BaseModel):
    """Batch feature flag operations"""
    flags: List[FeatureFlag]
    batch_operation: str  # "create", "update", "delete"
    affected_keys: List[str]
    processed_at: datetime


class FeatureFlagImport(BaseModel):
    """Feature flag import/export"""
    flags: List[FeatureFlag]
    export_version: str
    export_date: datetime
    exported_by: str
    environment: str  # "development", "staging", "production"
