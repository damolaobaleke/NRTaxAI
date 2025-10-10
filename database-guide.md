# NRTaxAI Database Guide - SQL Patterns & Explanations

## Table of Contents
1. [Database Schema Overview](#database-schema-overview)
2. [Table Separation Rationale](#table-separation-rationale)
3. [Common Query Patterns](#common-query-patterns)
4. [Performance Optimization](#performance-optimization)
5. [Security & Encryption](#security--encryption)

---

## Database Schema Overview

### Core Tables

```sql
-- Authentication & Core User Data
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Extended User Profile (PII & Tax Data)
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    dob DATE,
    residency_country VARCHAR(3),  -- ISO country code
    visa_class VARCHAR(20),  -- H1B, F-1, O-1, etc.
    itin VARCHAR(255),  -- encrypted
    ssn_last4 VARCHAR(4),
    address_json JSONB,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat Sessions (Conversation Threads)
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_return_id UUID REFERENCES tax_returns(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'active',  -- active, completed, abandoned
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat Messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- user, assistant, system, tool
    content TEXT,
    tool_calls_json JSONB,  -- stores tool calls if role is assistant
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tax Returns
CREATE TABLE tax_returns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year INTEGER NOT NULL,
    status VARCHAR(30) DEFAULT 'draft',  -- draft, computing, review, approved, filed
    ruleset_version VARCHAR(20),
    residency_result_json JSONB,
    treaty_json JSONB,
    totals_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_tax_year UNIQUE (user_id, tax_year)
);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    return_id UUID REFERENCES tax_returns(id) ON DELETE SET NULL,
    s3_key VARCHAR(500) NOT NULL,
    doc_type VARCHAR(20) NOT NULL,  -- W2, 1099INT, 1099NEC, 1098T
    source VARCHAR(50),
    status VARCHAR(20) DEFAULT 'uploaded',  -- uploaded, processing, extracted, failed
    textract_job_id VARCHAR(100),
    extracted_json JSONB,
    validation_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Operators (PTIN Holders)
CREATE TABLE operators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    ptin VARCHAR(20) NOT NULL,
    roles JSONB,  -- ['reviewer', 'admin']
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reviews (HITL)
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_id UUID NOT NULL REFERENCES tax_returns(id) ON DELETE CASCADE,
    operator_id UUID NOT NULL REFERENCES operators(id),
    decision VARCHAR(20),  -- approved, rejected, needs_revision
    comments TEXT,
    diffs_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs (Immutable)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type VARCHAR(20),  -- user, operator, system
    actor_id UUID,
    return_id UUID REFERENCES tax_returns(id),
    action VARCHAR(100) NOT NULL,
    payload_json JSONB,
    hash VARCHAR(64),  -- SHA-256 hash for chain integrity
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_tax_returns_user_year ON tax_returns(user_id, tax_year);
CREATE INDEX idx_documents_return_type ON documents(return_id, doc_type);
CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_time ON chat_messages(session_id, created_at);
CREATE INDEX idx_audit_logs_return_time ON audit_logs(return_id, created_at DESC);
```

---

## Table Separation Rationale

### Why Separate `users` and `user_profiles`?

#### 1. **Security & Access Control Separation**
- `users` table: Contains only authentication/authorization data (email, password_hash, mfa_enabled)
- `user_profiles` table: Contains PII and tax-specific data (SSN, ITIN, DOB, visa status)
- This allows different encryption strategies, access patterns, and audit controls for each

#### 2. **Performance Optimization**
- Authentication queries are extremely frequent and need to be fast
- Keeping the `users` table small (fewer columns) means better index performance
- Profile data is only loaded when actually needed (after login, during tax prep)

#### 3. **Data Sensitivity & Compliance (IRS Pub 4557)**
- PII fields (SSN/ITIN, DOB, address) require **field-level encryption with KMS**
- The `users` table doesn't need this heavy encryption overhead
- Makes it easier to implement data masking, redaction, and "right to deletion" (GDPR/CCPA)
- Separation allows different retention policies (auth data vs tax records)

#### 4. **Role Distinction**
- `users` → generic auth for all system users (taxpayers, operators, admins)
- `user_profiles` → taxpayer-specific demographics
- `operators` → a separate table for PTIN holders with different fields

#### 5. **Schema Evolution & Flexibility**
- Tax rules change yearly; new visa types, new required fields for treaty claims
- Easier to add columns to `user_profiles` without touching the core `users` authentication table
- Reduces migration risk and schema lock contention

---

## Common Query Patterns

### 1. Authentication Flow

```sql
-- Step 1: Fast authentication lookup (uses email index)
SELECT id, email, password_hash, mfa_enabled 
FROM users 
WHERE email = 'user@example.com';

-- Step 2: Fetch profile data (only when needed, using the authenticated user_id)
SELECT * 
FROM user_profiles 
WHERE user_id = 'authenticated-user-uuid';
```

### 2. Complete User Profile with Join

```sql
-- Get user + profile in one query
SELECT 
    u.id,
    u.email,
    u.mfa_enabled,
    up.first_name,
    up.last_name,
    up.dob,
    up.visa_class,
    up.residency_country,
    up.ssn_last4,
    up.address_json
FROM users u
LEFT JOIN user_profiles up ON up.user_id = u.id
WHERE u.id = :user_id;
```

### 3. Chat History Retrieval

```sql
-- Basic: Get all messages for a session (chronological order)
SELECT * 
FROM chat_messages 
WHERE session_id = :session_id
ORDER BY created_at ASC;

-- With session metadata
SELECT 
    cs.id AS session_id,
    cs.status,
    cs.tax_return_id,
    cs.created_at AS session_started,
    cm.id AS message_id,
    cm.role,
    cm.content,
    cm.tool_calls_json,
    cm.created_at AS message_time
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cm.session_id = cs.id
WHERE cs.id = :session_id
ORDER BY cm.created_at ASC;

-- With authorization check (user owns this session)
SELECT cm.* 
FROM chat_messages cm
JOIN chat_sessions cs ON cm.session_id = cs.id
WHERE cs.id = :session_id 
  AND cs.user_id = :current_user_id
ORDER BY cm.created_at ASC;
```

### 4. Chat Session Linked to Tax Return

```sql
-- Get chat messages + associated tax return context
SELECT 
    cm.role,
    cm.content,
    cm.created_at,
    tr.tax_year,
    tr.status AS return_status,
    tr.totals_json
FROM chat_messages cm
JOIN chat_sessions cs ON cm.session_id = cs.id
LEFT JOIN tax_returns tr ON cs.tax_return_id = tr.id
WHERE cs.id = :session_id
ORDER BY cm.created_at ASC;
```

### 5. Operator Review Workflow

```sql
-- Get review queue for operator (pending returns)
SELECT 
    tr.id AS return_id,
    tr.tax_year,
    tr.status,
    u.email AS taxpayer_email,
    up.first_name,
    up.last_name,
    tr.created_at
FROM tax_returns tr
JOIN users u ON tr.user_id = u.id
LEFT JOIN user_profiles up ON up.user_id = u.id
WHERE tr.status = 'review'
ORDER BY tr.created_at ASC;

-- Get specific return for review with all context
SELECT 
    tr.*,
    u.email,
    up.first_name,
    up.last_name,
    up.visa_class,
    up.residency_country
FROM tax_returns tr
JOIN users u ON tr.user_id = u.id
LEFT JOIN user_profiles up ON up.user_id = u.id
WHERE tr.id = :return_id;

-- Get all chat history for a return (compliance/audit)
SELECT 
    cm.role,
    cm.content,
    cm.created_at
FROM chat_messages cm
JOIN chat_sessions cs ON cm.session_id = cs.id
WHERE cs.tax_return_id = :return_id
ORDER BY cm.created_at ASC;
```

### 6. Document Upload & Extraction

```sql
-- Get all documents for a tax return
SELECT 
    id,
    doc_type,
    status,
    extracted_json,
    validation_json,
    created_at
FROM documents
WHERE return_id = :return_id
ORDER BY doc_type, created_at;

-- Check extraction status for pending documents
SELECT 
    id,
    s3_key,
    doc_type,
    status,
    textract_job_id
FROM documents
WHERE return_id = :return_id 
  AND status IN ('uploaded', 'processing')
ORDER BY created_at ASC;
```

### 7. Audit Trail Export

```sql
-- Get complete audit trail for a tax return
SELECT 
    al.id,
    al.actor_type,
    al.action,
    al.payload_json,
    al.created_at,
    al.hash,
    CASE 
        WHEN al.actor_type = 'user' THEN u.email
        WHEN al.actor_type = 'operator' THEN o.email
        ELSE 'system'
    END AS actor_email
FROM audit_logs al
LEFT JOIN users u ON al.actor_type = 'user' AND al.actor_id = u.id
LEFT JOIN operators o ON al.actor_type = 'operator' AND al.actor_id = o.id
WHERE al.return_id = :return_id
ORDER BY al.created_at ASC;

-- Verify hash chain integrity
SELECT 
    id,
    action,
    hash,
    LAG(hash) OVER (ORDER BY created_at) AS previous_hash,
    created_at
FROM audit_logs
WHERE return_id = :return_id
ORDER BY created_at ASC;
```

---

## Performance Optimization

### 1. Pagination for Long Chat Histories

```sql
-- Paginate chat messages (50 per page)
SELECT * 
FROM chat_messages 
WHERE session_id = :session_id
ORDER BY created_at ASC
LIMIT 50 OFFSET :offset;

-- Get total count for pagination
SELECT COUNT(*) 
FROM chat_messages 
WHERE session_id = :session_id;
```

### 2. Redis Caching Pattern (FastAPI)

```python
import json
from redis import asyncio as aioredis

async def get_chat_history(session_id: str, db, redis):
    # Try cache first
    cache_key = f"chat:session:{session_id}:messages"
    cached = await redis.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # Cache miss: fetch from DB
    messages = await db.fetch_all(
        """
        SELECT role, content, tool_calls_json, created_at 
        FROM chat_messages 
        WHERE session_id = :session_id
        ORDER BY created_at ASC
        """,
        {"session_id": session_id}
    )
    
    # Cache for 1 hour
    await redis.setex(cache_key, 3600, json.dumps(messages, default=str))
    
    return messages
```

### 3. Materialized Views for Analytics

```sql
-- Create materialized view for operator dashboard stats
CREATE MATERIALIZED VIEW operator_stats AS
SELECT 
    o.id AS operator_id,
    o.email,
    COUNT(r.id) AS total_reviews,
    COUNT(CASE WHEN r.decision = 'approved' THEN 1 END) AS approved_count,
    COUNT(CASE WHEN r.decision = 'rejected' THEN 1 END) AS rejected_count,
    AVG(EXTRACT(EPOCH FROM (r.created_at - tr.updated_at))) AS avg_review_time_seconds
FROM operators o
LEFT JOIN reviews r ON r.operator_id = o.id
LEFT JOIN tax_returns tr ON r.return_id = tr.id
GROUP BY o.id, o.email;

-- Refresh periodically (cron job or trigger)
REFRESH MATERIALIZED VIEW operator_stats;
```

---

## Security & Encryption

### 1. Field-Level Encryption (KMS Envelope)

```python
import boto3
import json
from base64 import b64encode, b64decode

kms_client = boto3.client('kms')
KMS_KEY_ID = 'arn:aws:kms:us-east-1:123456789012:key/...'

async def encrypt_pii(plaintext: str) -> dict:
    """Encrypt SSN/ITIN using KMS envelope encryption"""
    # Generate data key
    response = kms_client.generate_data_key(
        KeyId=KMS_KEY_ID,
        KeySpec='AES_256'
    )
    
    plaintext_key = response['Plaintext']
    encrypted_key = response['CiphertextBlob']
    
    # Encrypt data with plaintext key (AES-256)
    from cryptography.fernet import Fernet
    cipher = Fernet(b64encode(plaintext_key[:32]))
    encrypted_data = cipher.encrypt(plaintext.encode())
    
    return {
        'encrypted_value': b64encode(encrypted_data).decode(),
        'encrypted_key': b64encode(encrypted_key).decode()
    }

async def decrypt_pii(encrypted_dict: dict) -> str:
    """Decrypt SSN/ITIN"""
    # Decrypt data key with KMS
    encrypted_key = b64decode(encrypted_dict['encrypted_key'])
    response = kms_client.decrypt(CiphertextBlob=encrypted_key)
    plaintext_key = response['Plaintext']
    
    # Decrypt data
    from cryptography.fernet import Fernet
    cipher = Fernet(b64encode(plaintext_key[:32]))
    encrypted_data = b64decode(encrypted_dict['encrypted_value'])
    plaintext = cipher.decrypt(encrypted_data)
    
    return plaintext.decode()

# Usage in FastAPI
@app.get("/users/me")
async def get_user_profile(current_user = Depends(get_current_user)):
    profile = await db.fetch_one(
        "SELECT * FROM user_profiles WHERE user_id = :user_id",
        {"user_id": current_user.id}
    )
    
    # Decrypt sensitive fields
    if profile['itin']:
        itin_dict = json.loads(profile['itin'])
        profile['itin'] = await decrypt_pii(itin_dict)
    
    return profile
```

### 2. Row-Level Security (PostgreSQL)

```sql
-- Enable RLS on sensitive tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own profile
CREATE POLICY user_profile_isolation ON user_profiles
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- Policy: Operators can see all profiles (with proper role)
CREATE POLICY operator_view_all ON user_profiles
    FOR SELECT
    USING (current_setting('app.user_role') = 'operator');

-- Set session variables in FastAPI before queries
await db.execute(
    "SET app.current_user_id = :user_id",
    {"user_id": current_user.id}
)
```

### 3. Audit Log Hash Chaining

```python
import hashlib
import json

async def create_audit_log(db, actor_type: str, actor_id: str, return_id: str, action: str, payload: dict):
    """Create immutable audit log with hash chain"""
    
    # Get previous hash
    prev_log = await db.fetch_one(
        """
        SELECT hash FROM audit_logs 
        WHERE return_id = :return_id 
        ORDER BY created_at DESC 
        LIMIT 1
        """,
        {"return_id": return_id}
    )
    
    previous_hash = prev_log['hash'] if prev_log else '0' * 64
    
    # Compute new hash
    log_data = {
        'actor_type': actor_type,
        'actor_id': actor_id,
        'return_id': return_id,
        'action': action,
        'payload': payload,
        'previous_hash': previous_hash
    }
    
    current_hash = hashlib.sha256(
        json.dumps(log_data, sort_keys=True).encode()
    ).hexdigest()
    
    # Insert with hash
    await db.execute(
        """
        INSERT INTO audit_logs 
        (actor_type, actor_id, return_id, action, payload_json, hash)
        VALUES (:actor_type, :actor_id, :return_id, :action, :payload, :hash)
        """,
        {
            'actor_type': actor_type,
            'actor_id': actor_id,
            'return_id': return_id,
            'action': action,
            'payload': json.dumps(payload),
            'hash': current_hash
        }
    )
```

---

## FastAPI Integration Examples

### Complete User Profile Endpoint

```python
from fastapi import FastAPI, Depends, HTTPException
from typing import Optional
import databases

app = FastAPI()
database = databases.Database("postgresql://...")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Extract user from JWT token"""
    payload = jwt.decode(token, SECRET_KEY)
    user_id = payload.get("sub")
    
    user = await database.fetch_one(
        "SELECT id, email, mfa_enabled FROM users WHERE id = :id",
        {"id": user_id}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user

@app.get("/users/me")
async def get_user_profile(current_user = Depends(get_current_user)):
    """Get complete user profile with decrypted PII"""
    
    # Fetch profile
    profile = await database.fetch_one(
        """
        SELECT 
            up.*,
            u.email 
        FROM user_profiles up
        JOIN users u ON u.id = up.user_id
        WHERE up.user_id = :user_id
        """,
        {"user_id": current_user['id']}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Decrypt sensitive fields
    if profile['itin']:
        profile['itin'] = await decrypt_pii(json.loads(profile['itin']))
    
    return {
        "email": profile['email'],
        "first_name": profile['first_name'],
        "last_name": profile['last_name'],
        "visa_class": profile['visa_class'],
        "residency_country": profile['residency_country'],
        "ssn_last4": profile['ssn_last4'],
        "itin": profile['itin']
    }
```

### Chat Session & Message Endpoints

```python
@app.post("/chat/session")
async def create_chat_session(
    tax_return_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Create new chat session"""
    session = await database.fetch_one(
        """
        INSERT INTO chat_sessions (user_id, tax_return_id, status)
        VALUES (:user_id, :tax_return_id, 'active')
        RETURNING *
        """,
        {
            "user_id": current_user['id'],
            "tax_return_id": tax_return_id
        }
    )
    return session

@app.post("/chat/message")
async def send_chat_message(
    session_id: str,
    message: str,
    current_user = Depends(get_current_user)
):
    """Send message and get AI response"""
    
    # Verify session ownership
    session = await database.fetch_one(
        """
        SELECT * FROM chat_sessions 
        WHERE id = :id AND user_id = :user_id
        """,
        {"id": session_id, "user_id": current_user['id']}
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Store user message
    await database.execute(
        """
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (:session_id, 'user', :content)
        """,
        {"session_id": session_id, "content": message}
    )
    
    # Get full history for context
    history = await database.fetch_all(
        """
        SELECT role, content FROM chat_messages
        WHERE session_id = :session_id
        ORDER BY created_at ASC
        """,
        {"session_id": session_id}
    )
    
    # Call OpenAI (simplified)
    openai_messages = [
        {"role": msg['role'], "content": msg['content']}
        for msg in history
    ]
    
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=openai_messages
    )
    
    assistant_message = response.choices[0].message.content
    
    # Store assistant response
    await database.execute(
        """
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (:session_id, 'assistant', :content)
        """,
        {"session_id": session_id, "content": assistant_message}
    )
    
    return {"message": assistant_message}

@app.get("/chat/history")
async def get_chat_history(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get chat history for a session"""
    
    # Verify ownership
    session = await database.fetch_one(
        """
        SELECT * FROM chat_sessions 
        WHERE id = :id AND user_id = :user_id
        """,
        {"id": session_id, "user_id": current_user['id']}
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = await database.fetch_all(
        """
        SELECT role, content, created_at 
        FROM chat_messages 
        WHERE session_id = :session_id
        ORDER BY created_at ASC
        """,
        {"session_id": session_id}
    )
    
    return {
        "session": session,
        "messages": messages
    }
```

---

## Summary

This database architecture provides:

1. **Security**: Separated auth from PII, field-level encryption, row-level security
2. **Performance**: Optimized indexes, caching strategies, materialized views
3. **Compliance**: Immutable audit logs with hash chaining, data retention policies
4. **Scalability**: Proper normalization, efficient joins, pagination support
5. **Maintainability**: Clear separation of concerns, flexible schema evolution

The separation of `users` and `user_profiles` is intentional and critical for security, performance, and compliance in a tax preparation system handling sensitive PII.

