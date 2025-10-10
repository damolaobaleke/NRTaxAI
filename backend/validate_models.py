"""
Model Validation Script
Tests all Pydantic models to ensure they work correctly
"""

import sys
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any

# Add the app directory to the path
sys.path.append('.')

from app.models import (
    # User models
    User, UserCreate, UserUpdate, UserInDB,
    UserProfile, UserProfileCreate, UserProfileUpdate, UserProfileInDB, UserProfileWithITIN,
    Token, TokenData,
    
    # Chat models
    ChatSession, ChatSessionCreate, ChatSessionUpdate, ChatSessionInDB,
    ChatMessage, ChatMessageCreate, ChatMessageInDB,
    ChatHistory, ChatMessageRequest, ChatMessageResponse,
    
    # Tax return models
    TaxReturn, TaxReturnCreate, TaxReturnUpdate, TaxReturnInDB,
    Document, DocumentCreate, DocumentUpdate, DocumentInDB,
    Validation, ValidationCreate, ValidationInDB,
    Computation, ComputationCreate, ComputationInDB,
    TaxReturnSummary,
    
    # Operator models
    Operator, OperatorCreate, OperatorUpdate, OperatorInDB,
    Review, ReviewCreate, ReviewUpdate, ReviewInDB, ReviewWithDetails,
    OperatorWithStats, ReviewQueueItem,
    
    # Authorization models
    Authorization, AuthorizationCreate, AuthorizationUpdate, AuthorizationInDB,
    AuthorizationRequest, AuthorizationConfirmation, AuthorizationSummary,
    Form8879Equivalent, AuthorizationMethod, AuthorizationStatus,
    
    # Audit models
    AuditLog, AuditLogCreate, AuditLogInDB, AuditLogWithActor,
    AuditTrail, AuditBundle, HashChainValidation, AuditSearch, AuditStats,
    ActorType, AuditAction,
    
    # Forms models
    Form, FormCreate, FormUpdate, FormInDB,
    FormGenerationRequest, FormGenerationResult, FormDownloadRequest,
    FormValidation, FormMetadata, FormTemplate, FormFieldMapping,
    FormGenerationStatus, FormType, FormStatus,
    
    # API keys models
    ApiKey, ApiKeyCreate, ApiKeyUpdate, ApiKeyInDB, ApiKeyWithSecret,
    ApiKeyUsage, ApiKeyValidation, ApiKeyRequest, ApiKeyStats,
    ApiKeyScope, ApiKeyStatus,
    
    # Feature flags models
    FeatureFlag, FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagInDB,
    BooleanFeatureFlag, StringFeatureFlag, NumberFeatureFlag, JsonFeatureFlag, ListFeatureFlag,
    FeatureFlagEvaluation, FeatureFlagOverride, FeatureFlagAudit, FeatureFlagUsage,
    FeatureFlagBatch, FeatureFlagImport, FeatureFlagType
)

from app.models.common import (
    HealthStatus, ErrorResponse, SuccessResponse, PaginationParams, PaginatedResponse,
    FileUpload, DocumentType, VisaClass, TaxYear, NotificationType, Notification,
    SystemSettings, Metrics, CountryCode, Address, ContactInfo, ValidationRule, ProcessingStatus
)


def test_user_models():
    """Test user-related models"""
    print("Testing User Models...")
    
    # Test user creation
    user_create = UserCreate(
        email="test@example.com",
        password="password123",
        mfa_enabled=False
    )
    print(f"✓ UserCreate: {user_create.email}")
    
    # Test user profile creation
    profile_create = UserProfileCreate(
        first_name="John",
        last_name="Doe",
        residency_country="US",
        visa_class="H1B",
        ssn_last4="1234"
    )
    print(f"✓ UserProfileCreate: {profile_create.first_name} {profile_create.last_name}")
    
    # Test token
    token = Token(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="bearer"
    )
    print(f"✓ Token: {token.token_type}")


def test_chat_models():
    """Test chat-related models"""
    print("Testing Chat Models...")
    
    session_id = uuid4()
    user_id = uuid4()
    
    # Test chat session creation
    session_create = ChatSessionCreate(
        tax_return_id=None,
        status="active"
    )
    print(f"✓ ChatSessionCreate: {session_create.status}")
    
    # Test chat message creation
    message_create = ChatMessageCreate(
        session_id=session_id,
        role="user",
        content="Hello, I need help with my taxes"
    )
    print(f"✓ ChatMessageCreate: {message_create.role}")
    
    # Test chat message request
    message_request = ChatMessageRequest(
        session_id=session_id,
        message="What documents do I need?"
    )
    print(f"✓ ChatMessageRequest: {message_request.message[:20]}...")


def test_tax_return_models():
    """Test tax return-related models"""
    print("Testing Tax Return Models...")
    
    user_id = uuid4()
    return_id = uuid4()
    
    # Test tax return creation
    return_create = TaxReturnCreate(
        tax_year=2024,
        status="draft"
    )
    print(f"✓ TaxReturnCreate: {return_create.tax_year}")
    
    # Test document creation
    document_create = DocumentCreate(
        s3_key="documents/test-doc.pdf",
        doc_type="W2",
        return_id=return_id
    )
    print(f"✓ DocumentCreate: {document_create.doc_type}")
    
    # Test validation creation
    validation_create = ValidationCreate(
        return_id=return_id,
        severity="error",
        field="ssn",
        message="SSN format is invalid"
    )
    print(f"✓ ValidationCreate: {validation_create.severity}")
    
    # Test computation creation
    computation_create = ComputationCreate(
        return_id=return_id,
        line_code="1",
        description="Wages, salaries, tips, etc.",
        amount=50000.00
    )
    print(f"✓ ComputationCreate: {computation_create.amount}")


def test_operator_models():
    """Test operator-related models"""
    print("Testing Operator Models...")
    
    operator_id = uuid4()
    return_id = uuid4()
    
    # Test operator creation
    operator_create = OperatorCreate(
        email="operator@example.com",
        ptin="123456789",
        roles=["reviewer", "admin"]
    )
    print(f"✓ OperatorCreate: {operator_create.ptin}")
    
    # Test review creation
    review_create = ReviewCreate(
        return_id=return_id,
        operator_id=operator_id,
        decision="approved",
        comments="All information looks correct"
    )
    print(f"✓ ReviewCreate: {review_create.decision}")


def test_authorization_models():
    """Test authorization-related models"""
    print("Testing Authorization Models...")
    
    return_id = uuid4()
    
    # Test authorization creation
    auth_create = AuthorizationCreate(
        return_id=return_id,
        method=AuthorizationMethod.ESIGN,
        status=AuthorizationStatus.PENDING
    )
    print(f"✓ AuthorizationCreate: {auth_create.method}")
    
    # Test authorization request
    auth_request = AuthorizationRequest(
        return_id=return_id,
        method=AuthorizationMethod.ESIGN,
        expires_hours=72
    )
    print(f"✓ AuthorizationRequest: {auth_request.expires_hours} hours")


def test_audit_models():
    """Test audit-related models"""
    print("Testing Audit Models...")
    
    return_id = uuid4()
    user_id = uuid4()
    
    # Test audit log creation
    audit_create = AuditLogCreate(
        actor_type=ActorType.USER,
        actor_id=user_id,
        return_id=return_id,
        action=AuditAction.USER_LOGIN,
        payload_json={"ip_address": "192.168.1.1"}
    )
    print(f"✓ AuditLogCreate: {audit_create.action}")
    
    # Test audit search
    audit_search = AuditSearch(
        return_id=return_id,
        actor_type=ActorType.USER,
        limit=50
    )
    print(f"✓ AuditSearch: {audit_search.limit} results")


def test_forms_models():
    """Test forms-related models"""
    print("Testing Forms Models...")
    
    return_id = uuid4()
    
    # Test form creation
    form_create = FormCreate(
        return_id=return_id,
        form_type=FormType.FORM_1040NR,
        s3_key_pdf="forms/1040nr-2024.pdf"
    )
    print(f"✓ FormCreate: {form_create.form_type}")
    
    # Test form generation request
    gen_request = FormGenerationRequest(
        return_id=return_id,
        form_types=[FormType.FORM_1040NR, FormType.FORM_8843]
    )
    print(f"✓ FormGenerationRequest: {len(gen_request.form_types)} forms")


def test_api_keys_models():
    """Test API keys-related models"""
    print("Testing API Keys Models...")
    
    owner_id = uuid4()
    
    # Test API key creation
    api_key_create = ApiKeyCreate(
        owner_id=owner_id,
        scopes=[ApiKeyScope.READ, ApiKeyScope.WRITE],
        description="Test API key"
    )
    print(f"✓ ApiKeyCreate: {len(api_key_create.scopes)} scopes")
    
    # Test API key request
    api_key_request = ApiKeyRequest(
        api_key="sk_test_1234567890abcdef"
    )
    print(f"✓ ApiKeyRequest: {api_key_request.api_key[:10]}...")


def test_feature_flags_models():
    """Test feature flags-related models"""
    print("Testing Feature Flags Models...")
    
    # Test feature flag creation
    flag_create = FeatureFlagCreate(
        key="enable_chat_ai",
        value_json={"enabled": True, "model": "gpt-4"},
        description="Enable AI chat functionality"
    )
    print(f"✓ FeatureFlagCreate: {flag_create.key}")
    
    # Test boolean feature flag
    bool_flag = BooleanFeatureFlag(
        key="maintenance_mode",
        enabled=False,
        updated_at=datetime.now()
    )
    print(f"✓ BooleanFeatureFlag: {bool_flag.enabled}")


def test_common_models():
    """Test common utility models"""
    print("Testing Common Models...")
    
    # Test health status
    health = HealthStatus(
        timestamp=datetime.now(),
        version="1.0.0"
    )
    print(f"✓ HealthStatus: {health.status}")
    
    # Test pagination
    pagination = PaginationParams(
        page=1,
        size=20,
        sort_by="created_at",
        sort_order="desc"
    )
    print(f"✓ PaginationParams: page {pagination.page}")
    
    # Test address
    address = Address(
        street="123 Main St",
        city="New York",
        state="NY",
        postal_code="10001",
        country="US"
    )
    print(f"✓ Address: {address.city}, {address.state}")
    
    # Test visa class enum
    visa = VisaClass.H1B
    print(f"✓ VisaClass: {visa}")
    
    # Test document type enum
    doc_type = DocumentType.W2
    print(f"✓ DocumentType: {doc_type}")


def main():
    """Run all model validation tests"""
    print("🧪 NRTaxAI Model Validation Tests")
    print("=" * 50)
    
    try:
        test_user_models()
        test_chat_models()
        test_tax_return_models()
        test_operator_models()
        test_authorization_models()
        test_audit_models()
        test_forms_models()
        test_api_keys_models()
        test_feature_flags_models()
        test_common_models()
        
        print("\n" + "=" * 50)
        print("✅ All model validation tests passed!")
        print("🎉 All Pydantic models are working correctly.")
        
    except Exception as e:
        print(f"\n❌ Model validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
