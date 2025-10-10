# NRTaxAI Models Summary

## Overview

This document provides a comprehensive overview of all Pydantic models created for the NRTaxAI system. These models define the data structures, validation rules, and API contracts for the entire application.

## Model Categories

### 1. User Models (`user.py`)
**Purpose**: Handle user authentication, profiles, and personal information

#### Core Models:
- **User**: Basic user information (email, MFA status)
- **UserCreate**: User registration data
- **UserUpdate**: User modification data
- **UserInDB**: Internal user representation with password hash
- **UserProfile**: Extended user profile with PII
- **UserProfileCreate**: Profile creation data
- **UserProfileUpdate**: Profile modification data
- **UserProfileWithITIN**: Profile with decrypted ITIN for API responses
- **Token**: JWT authentication tokens
- **TokenData**: Token payload information

#### Key Features:
- Email validation with EmailStr
- Password strength requirements
- MFA support
- PII handling with encryption support
- Visa class and residency tracking

### 2. Chat Models (`chat.py`)
**Purpose**: Manage conversational AI sessions and message history

#### Core Models:
- **ChatSession**: Conversation thread container
- **ChatSessionCreate**: New session creation
- **ChatSessionUpdate**: Session modification
- **ChatMessage**: Individual messages
- **ChatMessageCreate**: New message creation
- **ChatHistory**: Complete conversation history
- **ChatMessageRequest**: User message input
- **ChatMessageResponse**: AI assistant response

#### Key Features:
- Session linking to tax returns
- Message role tracking (user, assistant, system, tool)
- Tool calls support for function calling
- Conversation persistence and retrieval

### 3. Tax Return Models (`tax_return.py`)
**Purpose**: Manage tax returns, documents, validations, and computations

#### Core Models:
- **TaxReturn**: Tax return record
- **TaxReturnCreate**: New return creation
- **TaxReturnUpdate**: Return modification
- **Document**: Uploaded tax documents
- **DocumentCreate**: Document upload metadata
- **DocumentUpdate**: Document processing updates
- **Validation**: Data validation results
- **ValidationCreate**: Validation rule creation
- **Computation**: Tax calculations
- **ComputationCreate**: Calculation input
- **TaxReturnSummary**: Comprehensive return overview

#### Key Features:
- Document type validation (W2, 1099INT, 1099NEC, 1098T)
- Validation severity levels (error, warning, info)
- Computation tracking with source attribution
- JSON metadata for complex data structures

### 4. Operator Models (`operator.py`)
**Purpose**: Manage PTIN holders and human review workflow

#### Core Models:
- **Operator**: PTIN holder information
- **OperatorCreate**: New operator registration
- **OperatorUpdate**: Operator modification
- **Review**: Human review decisions
- **ReviewCreate**: Review submission
- **ReviewUpdate**: Review modification
- **ReviewWithDetails**: Review with context
- **OperatorWithStats**: Operator performance metrics
- **ReviewQueueItem**: Pending review items

#### Key Features:
- PTIN validation and tracking
- Role-based access control (reviewer, admin)
- Review decision tracking (approved, rejected, needs_revision)
- Performance statistics and metrics

### 5. Authorization Models (`authorization.py`)
**Purpose**: Handle user authorization and electronic signatures

#### Core Models:
- **Authorization**: Authorization record
- **AuthorizationCreate**: New authorization request
- **AuthorizationUpdate**: Authorization modification
- **AuthorizationRequest**: User authorization request
- **AuthorizationConfirmation**: Signature confirmation
- **AuthorizationSummary**: Authorization status overview
- **Form8879Equivalent**: Electronic signature equivalent
- **AuthorizationMethod**: Signature methods (esign, wet_sign, phone, email)
- **AuthorizationStatus**: Status tracking (pending, signed, expired, cancelled)

#### Key Features:
- Multiple authorization methods
- Expiration handling
- Evidence collection for compliance
- Form 8879 equivalent for IRS compliance

### 6. Audit Models (`audit.py`)
**Purpose**: Maintain immutable audit trails for compliance

#### Core Models:
- **AuditLog**: Individual audit entry
- **AuditLogCreate**: New audit log creation
- **AuditLogWithActor**: Audit log with actor details
- **AuditTrail**: Complete audit trail for a return
- **AuditBundle**: Exportable audit package
- **HashChainValidation**: Integrity verification
- **AuditSearch**: Audit log search parameters
- **AuditStats**: Audit statistics
- **ActorType**: Actor categories (user, operator, system, api)
- **AuditAction**: Predefined audit actions

#### Key Features:
- Immutable audit trail with hash chaining
- Comprehensive action tracking
- Integrity verification
- Export capabilities for compliance
- Search and filtering functionality

### 7. Forms Models (`forms.py`)
**Purpose**: Handle tax form generation and management

#### Core Models:
- **Form**: Generated tax form
- **FormCreate**: Form generation request
- **FormUpdate**: Form modification
- **FormGenerationRequest**: Bulk form generation
- **FormGenerationResult**: Generation results
- **FormDownloadRequest**: Form download request
- **FormValidation**: Form validation results
- **FormMetadata**: Form file metadata
- **FormTemplate**: Form template configuration
- **FormFieldMapping**: Field mapping rules
- **FormGenerationStatus**: Generation progress tracking
- **FormType**: Supported forms (1040NR, 8843, W-8BEN, 1040-V)
- **FormStatus**: Form lifecycle status

#### Key Features:
- Support for all required tax forms
- Template-based generation
- Field mapping and validation
- Download tracking and security
- Generation status monitoring

### 8. API Keys Models (`api_keys.py`)
**Purpose**: Manage API access and authentication

#### Core Models:
- **ApiKey**: API key information
- **ApiKeyCreate**: New API key creation
- **ApiKeyUpdate**: API key modification
- **ApiKeyWithSecret**: API key with secret (creation only)
- **ApiKeyUsage**: Usage statistics
- **ApiKeyValidation**: Key validation results
- **ApiKeyRequest**: API key authentication request
- **ApiKeyStats**: Usage analytics
- **ApiKeyScope**: Permission scopes (read, write, admin, upload, download, audit)
- **ApiKeyStatus**: Key status (active, inactive, revoked, expired)

#### Key Features:
- Scope-based permissions
- Usage tracking and analytics
- Expiration handling
- Security with hashed storage
- Comprehensive validation

### 9. Feature Flags Models (`feature_flags.py`)
**Purpose**: Manage feature toggles and system configuration

#### Core Models:
- **FeatureFlag**: Generic feature flag
- **FeatureFlagCreate**: New flag creation
- **FeatureFlagUpdate**: Flag modification
- **BooleanFeatureFlag**: Boolean toggle
- **StringFeatureFlag**: String value flag
- **NumberFeatureFlag**: Numeric value flag
- **JsonFeatureFlag**: Complex data flag
- **ListFeatureFlag**: List value flag
- **FeatureFlagEvaluation**: Flag evaluation result
- **FeatureFlagOverride**: User-specific overrides
- **FeatureFlagAudit**: Flag change tracking
- **FeatureFlagUsage**: Usage statistics
- **FeatureFlagBatch**: Bulk operations
- **FeatureFlagImport**: Import/export functionality
- **FeatureFlagType**: Flag type enumeration

#### Key Features:
- Multiple data types supported
- User-specific overrides
- Change auditing
- Usage analytics
- Bulk operations and import/export

### 10. Common Models (`common.py`)
**Purpose**: Shared utilities and common data structures

#### Core Models:
- **HealthStatus**: System health information
- **ErrorResponse**: Standardized error responses
- **SuccessResponse**: Standardized success responses
- **PaginationParams**: Pagination parameters
- **PaginatedResponse**: Paginated data wrapper
- **FileUpload**: File upload metadata
- **DocumentType**: Supported document types
- **VisaClass**: Supported visa classes
- **TaxYear**: Tax year information
- **Notification**: System notifications
- **SystemSettings**: Global configuration
- **Metrics**: System metrics
- **CountryCode**: Country information
- **Address**: Address data structure
- **ContactInfo**: Contact information
- **ValidationRule**: Validation rule definition
- **ProcessingStatus**: Processing progress tracking

#### Key Features:
- Standardized API responses
- Comprehensive enums for tax-specific data
- System monitoring and health checks
- Flexible validation rules
- Progress tracking capabilities

## Database Schema Alignment

All models are designed to align with the PostgreSQL database schema defined in `init_db.py`:

- **Primary Keys**: UUID with auto-generation
- **Foreign Keys**: Proper relationships with cascade options
- **Indexes**: Optimized for common query patterns
- **Constraints**: Data integrity enforcement
- **JSONB Fields**: Flexible metadata storage
- **Timestamps**: Creation and update tracking

## Validation Features

### Data Validation:
- Email format validation
- Password strength requirements
- UUID format validation
- Enum value validation
- Range constraints for numeric fields
- Length limits for string fields

### Security Features:
- PII field separation
- Encrypted field support
- Hash chain integrity
- Audit trail immutability
- Access control integration

### Business Logic:
- Tax-specific validations
- Document type restrictions
- Visa class validation
- Form type constraints
- Status transition rules

## API Integration

All models are designed for seamless FastAPI integration:

- **Request Models**: Input validation and parsing
- **Response Models**: Output serialization
- **Database Models**: ORM integration
- **Update Models**: Partial update support
- **Search Models**: Query parameter validation

## Compliance Features

### IRS Requirements:
- Form 8879 equivalent support
- Audit trail requirements
- Data retention policies
- Security controls alignment

### Data Protection:
- PII handling
- Encryption support
- Right to deletion
- Data portability

## Usage Examples

### Creating a User:
```python
user_create = UserCreate(
    email="user@example.com",
    password="securepassword123",
    mfa_enabled=True
)
```

### Creating a Tax Return:
```python
return_create = TaxReturnCreate(
    tax_year=2024,
    status="draft"
)
```

### Creating an Audit Log:
```python
audit_log = AuditLogCreate(
    actor_type=ActorType.USER,
    actor_id=user_id,
    action=AuditAction.USER_LOGIN,
    payload_json={"ip_address": "192.168.1.1"}
)
```

## Testing

All models have been validated for:
- ✅ Python syntax correctness
- ✅ Pydantic model structure
- ✅ Type annotations
- ✅ Validation rules
- ✅ Enum definitions
- ✅ Import/export functionality

## Next Steps

The models are ready for:
1. API endpoint implementation
2. Database integration
3. Service layer development
4. Frontend integration
5. Testing and validation

This comprehensive model structure provides a solid foundation for the NRTaxAI system's data layer, ensuring type safety, validation, and compliance with tax preparation requirements.
