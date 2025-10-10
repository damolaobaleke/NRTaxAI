# Models package - Export all models

from .user import (
    User, UserCreate, UserUpdate, UserInDB,
    UserProfile, UserProfileCreate, UserProfileUpdate, UserProfileInDB, UserProfileWithITIN,
    Token, TokenData
)

from .chat import (
    ChatSession, ChatSessionCreate, ChatSessionUpdate, ChatSessionInDB,
    ChatMessage, ChatMessageCreate, ChatMessageInDB,
    ChatHistory, ChatMessageRequest, ChatMessageResponse
)

from .tax_return import (
    TaxReturn, TaxReturnCreate, TaxReturnUpdate, TaxReturnInDB,
    Document, DocumentCreate, DocumentUpdate, DocumentInDB,
    Validation, ValidationCreate, ValidationInDB,
    Computation, ComputationCreate, ComputationInDB,
    TaxReturnSummary
)

from .operator import (
    Operator, OperatorCreate, OperatorUpdate, OperatorInDB,
    Review, ReviewCreate, ReviewUpdate, ReviewInDB, ReviewWithDetails,
    OperatorWithStats, ReviewQueueItem
)

from .authorization import (
    Authorization, AuthorizationCreate, AuthorizationUpdate, AuthorizationInDB,
    AuthorizationRequest, AuthorizationConfirmation, AuthorizationSummary,
    Form8879Equivalent, AuthorizationMethod, AuthorizationStatus
)

from .audit import (
    AuditLog, AuditLogCreate, AuditLogInDB, AuditLogWithActor,
    AuditTrail, AuditBundle, HashChainValidation, AuditSearch, AuditStats,
    ActorType, AuditAction
)

from .forms import (
    Form, FormCreate, FormUpdate, FormInDB,
    FormGenerationRequest, FormGenerationResult, FormDownloadRequest,
    FormValidation, FormMetadata, FormTemplate, FormFieldMapping,
    FormGenerationStatus, FormType, FormStatus
)

from .api_keys import (
    ApiKey, ApiKeyCreate, ApiKeyUpdate, ApiKeyInDB, ApiKeyWithSecret,
    ApiKeyUsage, ApiKeyValidation, ApiKeyRequest, ApiKeyStats,
    ApiKeyScope, ApiKeyStatus
)

from .feature_flags import (
    FeatureFlag, FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagInDB,
    BooleanFeatureFlag, StringFeatureFlag, NumberFeatureFlag, JsonFeatureFlag, ListFeatureFlag,
    FeatureFlagEvaluation, FeatureFlagOverride, FeatureFlagAudit, FeatureFlagUsage,
    FeatureFlagBatch, FeatureFlagImport, FeatureFlagType
)

__all__ = [
    # User models
    "User", "UserCreate", "UserUpdate", "UserInDB",
    "UserProfile", "UserProfileCreate", "UserProfileUpdate", "UserProfileInDB", "UserProfileWithITIN",
    "Token", "TokenData",
    
    # Chat models
    "ChatSession", "ChatSessionCreate", "ChatSessionUpdate", "ChatSessionInDB",
    "ChatMessage", "ChatMessageCreate", "ChatMessageInDB",
    "ChatHistory", "ChatMessageRequest", "ChatMessageResponse",
    
    # Tax return models
    "TaxReturn", "TaxReturnCreate", "TaxReturnUpdate", "TaxReturnInDB",
    "Document", "DocumentCreate", "DocumentUpdate", "DocumentInDB",
    "Validation", "ValidationCreate", "ValidationInDB",
    "Computation", "ComputationCreate", "ComputationInDB",
    "TaxReturnSummary",
    
    # Operator models
    "Operator", "OperatorCreate", "OperatorUpdate", "OperatorInDB",
    "Review", "ReviewCreate", "ReviewUpdate", "ReviewInDB", "ReviewWithDetails",
    "OperatorWithStats", "ReviewQueueItem",
    
    # Authorization models
    "Authorization", "AuthorizationCreate", "AuthorizationUpdate", "AuthorizationInDB",
    "AuthorizationRequest", "AuthorizationConfirmation", "AuthorizationSummary",
    "Form8879Equivalent", "AuthorizationMethod", "AuthorizationStatus",
    
    # Audit models
    "AuditLog", "AuditLogCreate", "AuditLogInDB", "AuditLogWithActor",
    "AuditTrail", "AuditBundle", "HashChainValidation", "AuditSearch", "AuditStats",
    "ActorType", "AuditAction",
    
    # Forms models
    "Form", "FormCreate", "FormUpdate", "FormInDB",
    "FormGenerationRequest", "FormGenerationResult", "FormDownloadRequest",
    "FormValidation", "FormMetadata", "FormTemplate", "FormFieldMapping",
    "FormGenerationStatus", "FormType", "FormStatus",
    
    # API keys models
    "ApiKey", "ApiKeyCreate", "ApiKeyUpdate", "ApiKeyInDB", "ApiKeyWithSecret",
    "ApiKeyUsage", "ApiKeyValidation", "ApiKeyRequest", "ApiKeyStats",
    "ApiKeyScope", "ApiKeyStatus",
    
    # Feature flags models
    "FeatureFlag", "FeatureFlagCreate", "FeatureFlagUpdate", "FeatureFlagInDB",
    "BooleanFeatureFlag", "StringFeatureFlag", "NumberFeatureFlag", "JsonFeatureFlag", "ListFeatureFlag",
    "FeatureFlagEvaluation", "FeatureFlagOverride", "FeatureFlagAudit", "FeatureFlagUsage",
    "FeatureFlagBatch", "FeatureFlagImport", "FeatureFlagType"
]