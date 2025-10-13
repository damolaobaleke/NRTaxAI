-- A "migration" to add is_active and email_verified columns to the users table

-- Add new columns to existing users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- Update existing users to be active
UPDATE users SET is_active = TRUE WHERE is_active IS NULL;
UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL;
