-- Create Admin Tables in Supabase
-- Run this in your Supabase SQL Editor

-- =============================================
-- ADMIN TABLES
-- =============================================

-- Admins table
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Google integration flags
    google_classroom_enabled BOOLEAN DEFAULT false,
    google_calendar_enabled BOOLEAN DEFAULT false,
    
    -- Additional admin settings
    school_name VARCHAR(255),
    school_settings JSONB,
    integration_settings JSONB
);

-- Google Integrations table
CREATE TABLE IF NOT EXISTS google_integrations (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(id) ON DELETE CASCADE,
    service_type VARCHAR(20) NOT NULL CHECK (service_type IN ('classroom', 'calendar')),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scope TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Classroom Data table
CREATE TABLE IF NOT EXISTS classroom_data (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(id) ON DELETE CASCADE,
    course_id VARCHAR(255) NOT NULL,
    course_name VARCHAR(500) NOT NULL,
    course_description TEXT,
    course_room VARCHAR(500),
    course_section VARCHAR(500),
    course_state VARCHAR(50),
    teacher_email VARCHAR(255),
    student_count INTEGER DEFAULT 0,
    raw_data JSONB,
    last_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Calendar Data table
CREATE TABLE IF NOT EXISTS calendar_data (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(id) ON DELETE CASCADE,
    event_id VARCHAR(255) NOT NULL,
    event_title VARCHAR(500) NOT NULL,
    event_description TEXT,
    event_start TIMESTAMP WITH TIME ZONE NOT NULL,
    event_end TIMESTAMP WITH TIME ZONE NOT NULL,
    event_location VARCHAR(500),
    event_attendees JSONB,
    event_status VARCHAR(50),
    calendar_id VARCHAR(255),
    raw_data JSONB,
    last_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- INDEXES
-- =============================================

-- Admin indexes
CREATE INDEX IF NOT EXISTS idx_admins_email ON admins(email);
CREATE INDEX IF NOT EXISTS idx_admins_active ON admins(is_active) WHERE is_active = true;

-- Google integrations indexes
CREATE INDEX IF NOT EXISTS idx_google_integrations_admin ON google_integrations(admin_id);
CREATE INDEX IF NOT EXISTS idx_google_integrations_service ON google_integrations(service_type);
CREATE INDEX IF NOT EXISTS idx_google_integrations_active ON google_integrations(is_active) WHERE is_active = true;

-- Classroom data indexes
CREATE INDEX IF NOT EXISTS idx_classroom_data_admin ON classroom_data(admin_id);
CREATE INDEX IF NOT EXISTS idx_classroom_data_course ON classroom_data(course_id);

-- Calendar data indexes
CREATE INDEX IF NOT EXISTS idx_calendar_data_admin ON calendar_data(admin_id);
CREATE INDEX IF NOT EXISTS idx_calendar_data_event ON calendar_data(event_id);
CREATE INDEX IF NOT EXISTS idx_calendar_data_start ON calendar_data(event_start);

-- =============================================
-- TRIGGERS FOR UPDATED_AT
-- =============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_admins_updated_at 
    BEFORE UPDATE ON admins 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_integrations_updated_at 
    BEFORE UPDATE ON google_integrations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================

-- Enable RLS on all tables
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_data ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Allow service role to access all data
CREATE POLICY "Service role can access all admin data" ON admins
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all google integrations" ON google_integrations
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all classroom data" ON classroom_data
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all calendar data" ON calendar_data
    FOR ALL USING (auth.role() = 'service_role');

-- =============================================
-- GRANTS
-- =============================================

-- Grant permissions to service role
GRANT ALL ON admins TO service_role;
GRANT ALL ON google_integrations TO service_role;
GRANT ALL ON classroom_data TO service_role;
GRANT ALL ON calendar_data TO service_role;

-- Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- =============================================
-- INSERT DEFAULT ADMIN
-- =============================================

-- Insert default admin user
INSERT INTO admins (email, name, role, is_active)
VALUES ('admin@prakriti.org.in', 'System Administrator', 'admin', true)
ON CONFLICT (email) DO NOTHING;







