# NRTaxAI Document Upload System

## Overview

The NRTaxAI document upload system provides secure, scalable document processing for tax preparation. It includes pre-signed URL uploads, antivirus scanning, and document management capabilities.

## Features

### ✅ **Secure Upload Process**
- Pre-signed S3 URLs for direct client-to-S3 uploads
- File type validation (PDF, PNG, JPEG)
- File size limits (10MB max)
- Automatic expiration of upload URLs

### ✅ **Antivirus Scanning**
- AWS Lambda-based AV scanning
- Real-time threat detection
- Automatic quarantine of infected files
- Batch scanning capabilities

### ✅ **Document Management**
- Document type categorization (W-2, 1099-INT, etc.)
- Status tracking (uploading, clean, quarantined)
- Secure download URLs
- Document deletion and cleanup

### ✅ **Security & Compliance**
- KMS envelope encryption for sensitive data
- Row-level security in database
- Audit logging for all operations
- PII protection and data retention policies

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI        │    │   AWS S3        │
│                 │    │                  │    │                 │
│ DocumentUploader│───▶│ DocumentService  │───▶│ Upload Bucket   │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   PostgreSQL     │    │   Lambda AV     │
                       │                  │    │                 │
                       │ Document Records │    │ Scanner         │
                       │                  │    │                 │
                       └──────────────────┘    └─────────────────┘
```

## API Endpoints

### Document Upload

#### `POST /api/v1/documents/upload`
Request pre-signed upload URL

**Request:**
```json
{
  "doc_type": "W2",
  "return_id": "uuid-optional"
}
```

**Response:**
```json
{
  "document_id": "uuid",
  "upload_url": "https://s3.amazonaws.com/...",
  "fields": {
    "key": "uploads/user-id/W2_timestamp.pdf",
    "Content-Type": "application/pdf",
    "policy": "...",
    "signature": "..."
  },
  "file_key": "uploads/user-id/W2_timestamp.pdf",
  "expires_at": "2024-01-01T12:00:00Z"
}
```

#### `POST /api/v1/documents/{document_id}/confirm`
Confirm upload and initiate processing

**Response:**
```json
{
  "document_id": "uuid",
  "status": "clean",
  "file_size_bytes": 1024000,
  "av_scan_result": {
    "scan_status": "completed",
    "clean": true,
    "threats_detected": 0,
    "scan_engine": "NRTaxAI-AV-Engine"
  },
  "ready_for_processing": true
}
```

### Document Management

#### `GET /api/v1/documents`
List documents for user

**Query Parameters:**
- `return_id` (optional): Filter by tax return
- `status` (optional): Filter by status

**Response:**
```json
[
  {
    "document_id": "uuid",
    "doc_type": "W2",
    "status": "clean",
    "file_size": 1024000,
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

#### `GET /api/v1/documents/{document_id}`
Get document details

**Response:**
```json
{
  "document_id": "uuid",
  "doc_type": "W2",
  "status": "clean",
  "s3_key": "uploads/user-id/W2_timestamp.pdf",
  "file_metadata": {
    "size_bytes": 1024000,
    "content_type": "application/pdf",
    "last_modified": "2024-01-01T12:00:00Z"
  },
  "validation_data": {
    "av_scan": {
      "clean": true,
      "threats_detected": 0
    }
  }
}
```

#### `GET /api/v1/documents/{document_id}/download`
Get secure download URL

**Query Parameters:**
- `expires_in` (optional): URL expiration in seconds (default: 3600)

**Response:**
```json
{
  "download_url": "https://s3.amazonaws.com/...",
  "document_id": "uuid",
  "expires_in": 3600,
  "expires_at": "2024-01-01T13:00:00Z"
}
```

#### `DELETE /api/v1/documents/{document_id}`
Delete document

**Response:**
```json
{
  "deleted": true,
  "document_id": "uuid",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Frontend Integration

### DocumentUploader Component

```jsx
import DocumentUploader from './components/DocumentUploader';

function MyComponent() {
  const handleUploadComplete = (document) => {
    console.log('Document uploaded:', document);
    // Refresh document list or navigate
  };

  return (
    <DocumentUploader 
      returnId="tax-return-uuid"
      onUploadComplete={handleUploadComplete}
    />
  );
}
```

### Document Types Supported

- **W2**: Wage and Tax Statement
- **1099INT**: Interest Income
- **1099NEC**: Nonemployee Compensation
- **1098T**: Tuition Statement
- **1042S**: Foreign Person's U.S. Source Income
- **1099DIV**: Dividends and Distributions
- **1099B**: Broker Transactions
- **1099MISC**: Miscellaneous Income

## Security Features

### File Validation
- File type restrictions (PDF, PNG, JPEG only)
- File size limits (10MB maximum)
- Content type validation
- Malware scanning

### Access Control
- JWT-based authentication
- User-scoped document access
- Row-level security in database
- Secure pre-signed URLs

### Data Protection
- KMS envelope encryption for PII
- Secure file storage in S3
- Automatic cleanup of temporary files
- Audit logging for compliance

## Deployment

### Prerequisites
- AWS S3 buckets configured
- AWS Lambda function deployed
- PostgreSQL database with document tables
- Redis for caching (optional)

### Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# S3 Buckets
S3_BUCKET_UPLOADS=nrtaxai-uploads
S3_BUCKET_PDFS=nrtaxai-pdfs
S3_BUCKET_EXTRACTS=nrtaxai-extracts

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Security
SECRET_KEY=your-secret-key
KMS_KEY_ID=arn:aws:kms:region:account:key/key-id

# Limits
MAX_FILE_SIZE=10485760  # 10MB in bytes
ALLOWED_FILE_TYPES=pdf,png,jpg,jpeg
```

### Lambda Deployment

```bash
# Deploy AV scanner Lambda
cd backend
python deploy_lambda.py
```

### Database Setup

```bash
# Initialize database tables
cd backend
python init_db.py
```

## Testing

### Run Test Suite

```bash
# Test document upload pipeline
cd backend
python test_document_upload.py
```

### Test Coverage

- ✅ Upload URL generation
- ✅ File upload to S3
- ✅ Upload confirmation
- ✅ AV scanning
- ✅ Document retrieval
- ✅ Document listing
- ✅ Download URL generation
- ✅ Document deletion
- ✅ Batch operations
- ✅ Error scenarios
- ✅ Security validations

## Monitoring

### Metrics to Track

- Upload success rate
- AV scan results
- File processing time
- Storage usage
- Error rates by type

### Logging

All operations are logged with structured logging:
- Upload requests and confirmations
- AV scan results
- File access patterns
- Error conditions
- Security events

## Troubleshooting

### Common Issues

1. **Upload URL Expired**
   - Check system time synchronization
   - Verify AWS credentials
   - Check S3 bucket permissions

2. **AV Scan Failures**
   - Verify Lambda function deployment
   - Check IAM permissions
   - Review CloudWatch logs

3. **File Access Denied**
   - Verify user authentication
   - Check document ownership
   - Review database permissions

### Debug Mode

Enable debug logging:

```python
import structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

## Performance Optimization

### Caching
- Redis caching for frequently accessed documents
- S3 CloudFront for global file distribution
- Database query optimization

### Scaling
- S3 auto-scaling for storage
- Lambda concurrency limits
- Database connection pooling
- CDN for file delivery

## Compliance

### Data Retention
- Configurable retention policies
- Automatic cleanup of expired files
- Audit trail preservation

### Privacy
- PII encryption at rest
- Secure file transmission
- User consent tracking
- Right to deletion support

## Future Enhancements

- [ ] OCR integration for document text extraction
- [ ] Document classification using AI
- [ ] Automated form field detection
- [ ] Document versioning
- [ ] Collaborative document review
- [ ] Integration with tax preparation software
