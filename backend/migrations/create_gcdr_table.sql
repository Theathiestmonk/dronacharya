-- Migration: Create GCDR (Google Cloud Drive Read) table for OAuth tokens
-- Date: 2026-01-20
-- Description: Creates table to store Google OAuth access tokens for Drive read operations

-- Drop table if exists (to recreate with correct schema)
DROP TABLE IF EXISTS gcdr;

-- Create GCDR table (PostgreSQL/Supabase compatible)
CREATE TABLE gcdr (
    id SERIAL PRIMARY KEY,
    admin_id TEXT NOT NULL,  -- References user_profiles.user_id (UUID from auth.users)
    user_email VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scope TEXT NOT NULL,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    client_id VARCHAR(255),
    project_name VARCHAR(255) DEFAULT 'Prakriti Drive Test',
    notes TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_gcdr_admin_id ON gcdr(admin_id);
CREATE INDEX IF NOT EXISTS idx_gcdr_user_email ON gcdr(user_email);
CREATE INDEX IF NOT EXISTS idx_gcdr_is_active ON gcdr(is_active);
CREATE INDEX IF NOT EXISTS idx_gcdr_created_at ON gcdr(created_at DESC);

-- Create updated_at trigger function if it doesn't exist
CREATE OR REPLACE FUNCTION update_gcdr_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_gcdr_updated_at ON gcdr;
CREATE TRIGGER trigger_gcdr_updated_at
    BEFORE UPDATE ON gcdr
    FOR EACH ROW
    EXECUTE FUNCTION update_gcdr_updated_at();



