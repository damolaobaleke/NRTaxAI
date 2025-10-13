"""
Database Initialization Script
Creates all tables and indexes for NRTaxAI
"""

import asyncio
import asyncpg
from app.core.config import settings


# Database schema
CREATE_TABLES = """
-- Users table (authentication)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User profiles (PII & tax data)
CREATE TABLE IF NOT EXISTS user_profiles (
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

-- Chat sessions (conversation threads)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_return_id UUID,  -- Will reference tax_returns(id) when created
    status VARCHAR(20) DEFAULT 'active',  -- active, completed, abandoned
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- user, assistant, system, tool
    content TEXT,
    tool_calls_json JSONB,  -- stores tool calls if role is assistant
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tax returns
CREATE TABLE IF NOT EXISTS tax_returns (
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

-- Add foreign key constraint to chat_sessions after tax_returns is created
ALTER TABLE chat_sessions 
ADD CONSTRAINT fk_chat_sessions_tax_return_id 
FOREIGN KEY (tax_return_id) REFERENCES tax_returns(id) ON DELETE SET NULL;

-- Documents
CREATE TABLE IF NOT EXISTS documents (
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

-- Validations
CREATE TABLE IF NOT EXISTS validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_id UUID NOT NULL REFERENCES tax_returns(id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL,  -- error, warning, info
    field VARCHAR(100),
    code VARCHAR(50),
    message VARCHAR(500) NOT NULL,
    data_path VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Computations
CREATE TABLE IF NOT EXISTS computations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_id UUID NOT NULL REFERENCES tax_returns(id) ON DELETE CASCADE,
    line_code VARCHAR(20) NOT NULL,
    description VARCHAR(200) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Forms
CREATE TABLE IF NOT EXISTS forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_id UUID NOT NULL REFERENCES tax_returns(id) ON DELETE CASCADE,
    form_type VARCHAR(20) NOT NULL,  -- 1040NR, 8843, W8BEN, 1040V
    s3_key_pdf VARCHAR(500) NOT NULL,
    status VARCHAR(20) DEFAULT 'generated',  -- generated, signed, filed
    checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Operators (PTIN holders)
CREATE TABLE IF NOT EXISTS operators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    ptin VARCHAR(20) NOT NULL,
    roles JSONB,  -- ['reviewer', 'admin']
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reviews (HITL)
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_id UUID NOT NULL REFERENCES tax_returns(id) ON DELETE CASCADE,
    operator_id UUID NOT NULL REFERENCES operators(id),
    decision VARCHAR(20),  -- approved, rejected, needs_revision
    comments TEXT,
    diffs_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authorizations
CREATE TABLE IF NOT EXISTS authorizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_id UUID NOT NULL REFERENCES tax_returns(id) ON DELETE CASCADE,
    method VARCHAR(20) NOT NULL,  -- esign, wet_sign, etc.
    status VARCHAR(20) DEFAULT 'pending',  -- pending, signed, expired
    signed_at TIMESTAMP,
    evidence_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs (immutable)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type VARCHAR(20),  -- user, operator, system
    actor_id UUID,
    return_id UUID REFERENCES tax_returns(id),
    action VARCHAR(100) NOT NULL,
    payload_json JSONB,
    hash VARCHAR(64),  -- SHA-256 hash for chain integrity
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    scopes JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature flags
CREATE TABLE IF NOT EXISTS feature_flags (
    key VARCHAR(100) PRIMARY KEY,
    value_json JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Indexes
CREATE_INDEXES = """
-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_tax_returns_user_year ON tax_returns(user_id, tax_year);
CREATE INDEX IF NOT EXISTS idx_documents_return_type ON documents(return_id, doc_type);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_time ON chat_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_return_time ON audit_logs(return_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validations_return_severity ON validations(return_id, severity);
CREATE INDEX IF NOT EXISTS idx_computations_return_line ON computations(return_id, line_code);
CREATE INDEX IF NOT EXISTS idx_reviews_return_operator ON reviews(return_id, operator_id);
CREATE INDEX IF NOT EXISTS idx_authorizations_return_status ON authorizations(return_id, status);
CREATE INDEX IF NOT EXISTS idx_operators_email ON operators(email);
CREATE INDEX IF NOT EXISTS idx_operators_ptin ON operators(ptin);
CREATE INDEX IF NOT EXISTS idx_forms_return_type ON forms(return_id, form_type);
CREATE INDEX IF NOT EXISTS idx_api_keys_owner ON api_keys(owner_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_feature_flags_key ON feature_flags(key);
"""


async def init_database():
    """Initialize database with tables and indexes"""
    # Parse DATABASE_URL for asyncpg connection
    # Convert from: postgresql://user:pass@host:port/db
    # to asyncpg format
    db_url = str(settings.DATABASE_URL)
    print(db_url)
    conn = None
    
    try:
        # Connect to database using asyncpg
        conn = await asyncpg.connect(db_url)
        print("Connected to database")
        
        # Create tables
        print("Creating tables...")
        await conn.execute(CREATE_TABLES)
        print("Tables created successfully")
        
        # Create indexes
        print("Creating indexes...")
        await conn.execute(CREATE_INDEXES)
        print("Indexes created successfully")
        
        print("Database initialization completed!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(init_database())
