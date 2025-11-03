"""
Database Initialization Script
Creates all tables and indexes for NRTaxAI
"""

import asyncio
import asyncpg
from pathlib import Path
from app.core.config import settings


# Read migration file
MIGRATION_PATH = Path(__file__).parent / "sql_table_column_updates.sql"
MIGRATIONS = MIGRATION_PATH.read_text() if MIGRATION_PATH.exists() else ""

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
    university_email_domain VARCHAR(100),
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
    partnership_id UUID,  -- FK to partnerships (nullable)
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Universities (B2B partners)
CREATE TABLE IF NOT EXISTS universities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- e.g., "ucla"
    domain VARCHAR(255),  -- e.g., "ucla.edu"
    logo_url VARCHAR(500),
    colors_json JSONB,  -- Branding colors
    contact_email VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',  -- active, inactive, suspended
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partnerships (contracts between NRTAX and universities)
CREATE TABLE IF NOT EXISTS partnerships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id UUID NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    model_type VARCHAR(20) NOT NULL,  -- saas_license, revenue_share, affiliate
    pricing_tier INTEGER,  -- 1, 2, 3 (based on enrollment size)
    price_per_seat DECIMAL(10,2),  -- For SaaS license model
    commission_percent DECIMAL(5,2),  -- For revenue-share model (e.g., 10.00)
    contract_start DATE NOT NULL,
    contract_end DATE,
    status VARCHAR(20) DEFAULT 'active',  -- active, expired, cancelled
    metadata_json JSONB,  -- Additional contract details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Referrals (attribution tracking for revenue-share model)
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    partnership_id UUID NOT NULL REFERENCES partnerships(id) ON DELETE CASCADE,
    referral_code VARCHAR(100) NOT NULL,  -- e.g., "ucla"
    source VARCHAR(50),  -- "university", "email", "orientation"
    first_touch_ts TIMESTAMP NOT NULL,
    last_touch_ts TIMESTAMP NOT NULL,
    expiry_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, locked, expired
    campaign_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions (payment tracking)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_return_id UUID REFERENCES tax_returns(id) ON DELETE SET NULL,
    partnership_id UUID REFERENCES partnerships(id) ON DELETE SET NULL,
    referral_id UUID REFERENCES referrals(id) ON DELETE SET NULL,
    transaction_type VARCHAR(20) NOT NULL,  -- filing_fee, license_payment, state_addon
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    stripe_payment_intent_id VARCHAR(255),
    stripe_charge_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, succeeded, failed, refunded
    platform_share DECIMAL(10,2),  -- Platform's portion (70%)
    cpa_share DECIMAL(10,2),  -- CPA's portion (30%)
    partner_share DECIMAL(10,2),  -- Partner's portion (10%)
    net_to_platform DECIMAL(10,2),  -- Net after all splits
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payouts (revenue share payouts to universities)
CREATE TABLE IF NOT EXISTS payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partnership_id UUID NOT NULL REFERENCES partnerships(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_transactions INTEGER DEFAULT 0,
    gross_amount DECIMAL(10,2) NOT NULL,
    commission_percent DECIMAL(5,2) NOT NULL,
    commission_amount DECIMAL(10,2) NOT NULL,
    payout_method VARCHAR(20),  -- stripe_connect, ach
    payout_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    stripe_transfer_id VARCHAR(255),
    ach_reference VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP
);

-- Licenses (per-seat license tracking for SaaS model)
CREATE TABLE IF NOT EXISTS licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partnership_id UUID NOT NULL REFERENCES partnerships(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    seat_type VARCHAR(20) NOT NULL,  -- pre_purchase, post_usage
    status VARCHAR(20) DEFAULT 'active',  -- active, consumed, expired
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consumed_at TIMESTAMP,
    expiry_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- University admins (DSO/ISO staff access)
CREATE TABLE IF NOT EXISTS university_admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    partnership_id UUID NOT NULL REFERENCES partnerships(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'viewer',  -- admin, viewer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, partnership_id)
);
"""

# Indexes
CREATE_INDEXES = """
-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_university_domain ON users(university_email_domain);
CREATE INDEX IF NOT EXISTS idx_tax_returns_user_year ON tax_returns(user_id, tax_year);
CREATE INDEX IF NOT EXISTS idx_tax_returns_partnership ON tax_returns(partnership_id);
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

-- B2B indexes
CREATE INDEX IF NOT EXISTS idx_universities_slug ON universities(slug);
CREATE INDEX IF NOT EXISTS idx_universities_domain ON universities(domain);
CREATE INDEX IF NOT EXISTS idx_partnerships_university ON partnerships(university_id);
CREATE INDEX IF NOT EXISTS idx_partnerships_model_type ON partnerships(model_type);
CREATE INDEX IF NOT EXISTS idx_partnerships_status ON partnerships(status);
CREATE INDEX IF NOT EXISTS idx_referrals_user ON referrals(user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_partnership ON referrals(partnership_id);
CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(referral_code);
CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status);
CREATE INDEX IF NOT EXISTS idx_referrals_expiry ON referrals(expiry_date);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_return ON transactions(tax_return_id);
CREATE INDEX IF NOT EXISTS idx_transactions_partnership ON transactions(partnership_id);
CREATE INDEX IF NOT EXISTS idx_transactions_stripe_pi ON transactions(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_payouts_partnership ON payouts(partnership_id);
CREATE INDEX IF NOT EXISTS idx_payouts_period ON payouts(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_payouts_status ON payouts(payout_status);
CREATE INDEX IF NOT EXISTS idx_licenses_partnership ON licenses(partnership_id);
CREATE INDEX IF NOT EXISTS idx_licenses_user ON licenses(user_id);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);
CREATE INDEX IF NOT EXISTS idx_licenses_expiry ON licenses(expiry_date);
CREATE INDEX IF NOT EXISTS idx_university_admins_user ON university_admins(user_id);
CREATE INDEX IF NOT EXISTS idx_university_admins_partnership ON university_admins(partnership_id);
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
        
        # Apply migrations if they exist
        # if MIGRATIONS:
        #     print("Applying migrations...")
        #     await conn.execute(MIGRATIONS)
        #     print("Migrations applied successfully")
        
        print("Database initialization completed!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(init_database())
