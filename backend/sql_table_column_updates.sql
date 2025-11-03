-- Migration script for schema updates
-- All migrations use IF NOT EXISTS to be idempotent

-- Add new columns to existing users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS university_email_domain VARCHAR(100);

-- Update existing users to be active (idempotent - only updates NULL values)
UPDATE users SET is_active = TRUE WHERE is_active IS NULL;
UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL;

-- Add partnership_id to tax_returns
ALTER TABLE tax_returns ADD COLUMN IF NOT EXISTS partnership_id UUID;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_users_university_domain ON users(university_email_domain);
CREATE INDEX IF NOT EXISTS idx_tax_returns_partnership ON tax_returns(partnership_id);

-- Add new columns to existing documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
