-- Google Integrations Database Schema
-- This file contains SQL for storing Google Classroom and Google Calendar data

-- =============================================
-- GOOGLE OAUTH CONNECTIONS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS google_oauth_connections (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  service VARCHAR(20) NOT NULL CHECK (service IN ('classroom', 'calendar')),
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  token_expires_at TIMESTAMP WITH TIME ZONE,
  scope TEXT[] NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  
  -- Constraints
  UNIQUE(user_id, service)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_google_oauth_user_service ON google_oauth_connections(user_id, service);
CREATE INDEX IF NOT EXISTS idx_google_oauth_active ON google_oauth_connections(is_active) WHERE is_active = true;

-- =============================================
-- GOOGLE CLASSROOM TABLES
-- =============================================

-- Google Classroom Courses
CREATE TABLE IF NOT EXISTS google_classroom_courses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  course_id VARCHAR(255) NOT NULL, -- Google's course ID
  name VARCHAR(500) NOT NULL,
  description TEXT,
  section VARCHAR(500),
  room VARCHAR(500),
  owner_id VARCHAR(255), -- Google's owner ID
  enrollment_code VARCHAR(100),
  course_state VARCHAR(50), -- ACTIVE, ARCHIVED, PROVISIONED, DECLINED, SUSPENDED
  alternate_link TEXT,
  teacher_group_email VARCHAR(255),
  course_group_email VARCHAR(255),
  guardians_enabled BOOLEAN DEFAULT false,
  calendar_enabled BOOLEAN DEFAULT false,
  max_rosters INTEGER,
  course_material_sets JSONB, -- Array of course material sets
  gradebook_settings JSONB, -- Gradebook settings
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_synced_at TIMESTAMP WITH TIME ZONE,
  
  -- Constraints
  UNIQUE(user_id, course_id)
);

-- Google Classroom Students
CREATE TABLE IF NOT EXISTS google_classroom_students (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  course_id UUID REFERENCES google_classroom_courses(id) ON DELETE CASCADE,
  user_id VARCHAR(255) NOT NULL, -- Google's user ID
  course_user_id VARCHAR(255) NOT NULL, -- Google's course user ID
  profile JSONB NOT NULL, -- Full Google profile data
  student_work_folder JSONB, -- Student work folder info
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Constraints
  UNIQUE(course_id, course_user_id)
);

-- Google Classroom Teachers
CREATE TABLE IF NOT EXISTS google_classroom_teachers (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  course_id UUID REFERENCES google_classroom_courses(id) ON DELETE CASCADE,
  user_id VARCHAR(255) NOT NULL, -- Google's user ID
  course_user_id VARCHAR(255) NOT NULL, -- Google's course user ID
  profile JSONB NOT NULL, -- Full Google profile data
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Constraints
  UNIQUE(course_id, course_user_id)
);

-- Google Classroom Course Work (Assignments)
CREATE TABLE IF NOT EXISTS google_classroom_coursework (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  course_id UUID REFERENCES google_classroom_courses(id) ON DELETE CASCADE,
  coursework_id VARCHAR(255) NOT NULL, -- Google's coursework ID
  title VARCHAR(500) NOT NULL,
  description TEXT,
  materials JSONB, -- Array of materials
  state VARCHAR(50), -- PUBLISHED, DRAFT, DELETED
  alternate_link TEXT,
  creation_time TIMESTAMP WITH TIME ZONE,
  update_time TIMESTAMP WITH TIME ZONE,
  due_date TIMESTAMP WITH TIME ZONE,
  due_time VARCHAR(20), -- Time of day
  max_points DECIMAL(10,2),
  work_type VARCHAR(50), -- ASSIGNMENT, SHORT_ANSWER_QUESTION, MULTIPLE_CHOICE_QUESTION
  associated_with_developer BOOLEAN DEFAULT false,
  assignee_mode VARCHAR(50), -- ALL_STUDENTS, INDIVIDUAL_STUDENTS
  individual_students_options JSONB,
  submission_modification_mode VARCHAR(50), -- MODIFIABLE_UNTIL_TURNED_IN, UNMODIFIABLE
  creator_user_id VARCHAR(255),
  topic_id VARCHAR(255),
  grade_category JSONB,
  assignment JSONB, -- Assignment specific data
  multiple_choice_question JSONB, -- Multiple choice specific data
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_synced_at TIMESTAMP WITH TIME ZONE,
  
  -- Constraints
  UNIQUE(course_id, coursework_id)
);

-- Google Classroom Student Submissions
CREATE TABLE IF NOT EXISTS google_classroom_submissions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  coursework_id UUID REFERENCES google_classroom_coursework(id) ON DELETE CASCADE,
  submission_id VARCHAR(255) NOT NULL, -- Google's submission ID
  course_id VARCHAR(255) NOT NULL,
  coursework_id_google VARCHAR(255) NOT NULL,
  user_id VARCHAR(255) NOT NULL, -- Google's user ID
  state VARCHAR(50), -- NEW, CREATED, TURNED_IN, RETURNED, RECLAIMED_BY_STUDENT
  alternate_link TEXT,
  assigned_grade DECIMAL(10,2),
  draft_grade DECIMAL(10,2),
  course_work_type VARCHAR(50),
  associated_with_developer BOOLEAN DEFAULT false,
  submission_history JSONB, -- Array of submission history
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_synced_at TIMESTAMP WITH TIME ZONE,
  
  -- Constraints
  UNIQUE(coursework_id, submission_id)
);

-- =============================================
-- GOOGLE CALENDAR TABLES
-- =============================================

-- Google Calendar Events
CREATE TABLE IF NOT EXISTS google_calendar_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  event_id VARCHAR(255) NOT NULL, -- Google's event ID
  calendar_id VARCHAR(255) NOT NULL, -- Google's calendar ID
  summary VARCHAR(500),
  description TEXT,
  location VARCHAR(500),
  start_time TIMESTAMP WITH TIME ZONE,
  end_time TIMESTAMP WITH TIME ZONE,
  all_day BOOLEAN DEFAULT false,
  timezone VARCHAR(100),
  recurrence JSONB, -- Recurrence rules
  attendees JSONB, -- Array of attendees
  creator JSONB, -- Creator information
  organizer JSONB, -- Organizer information
  html_link TEXT,
  hangout_link TEXT,
  conference_data JSONB, -- Conference data
  visibility VARCHAR(50), -- DEFAULT, PUBLIC, PRIVATE, CONFIDENTIAL
  transparency VARCHAR(50), -- TRANSPARENT, OPAQUE
  status VARCHAR(50), -- CONFIRMED, TENTATIVE, CANCELLED
  event_type VARCHAR(50), -- DEFAULT, OUT_OF_OFFICE, FOCUS_TIME
  color_id VARCHAR(10),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_synced_at TIMESTAMP WITH TIME ZONE,
  
  -- Constraints
  UNIQUE(user_id, event_id)
);

-- Google Calendar Calendars
CREATE TABLE IF NOT EXISTS google_calendar_calendars (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  calendar_id VARCHAR(255) NOT NULL, -- Google's calendar ID
  summary VARCHAR(500),
  description TEXT,
  location VARCHAR(500),
  timezone VARCHAR(100),
  color_id VARCHAR(10),
  background_color VARCHAR(10),
  foreground_color VARCHAR(10),
  access_role VARCHAR(50), -- FREE_BUSY_READER, READER, WRITER, OWNER
  selected BOOLEAN DEFAULT true,
  primary_calendar BOOLEAN DEFAULT false,
  deleted BOOLEAN DEFAULT false,
  conference_properties JSONB,
  notification_settings JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_synced_at TIMESTAMP WITH TIME ZONE,
  
  -- Constraints
  UNIQUE(user_id, calendar_id)
);

-- =============================================
-- INTEGRATION SYNC LOGS
-- =============================================

-- Sync logs for tracking integration status
CREATE TABLE IF NOT EXISTS integration_sync_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  service VARCHAR(20) NOT NULL CHECK (service IN ('classroom', 'calendar')),
  sync_type VARCHAR(50) NOT NULL, -- FULL_SYNC, INCREMENTAL_SYNC, COURSE_SYNC, EVENT_SYNC
  status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED')),
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  records_processed INTEGER DEFAULT 0,
  records_created INTEGER DEFAULT 0,
  records_updated INTEGER DEFAULT 0,
  records_deleted INTEGER DEFAULT 0,
  error_message TEXT,
  sync_details JSONB, -- Additional sync metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

-- Google Classroom indexes
CREATE INDEX IF NOT EXISTS idx_classroom_courses_user ON google_classroom_courses(user_id);
CREATE INDEX IF NOT EXISTS idx_classroom_courses_state ON google_classroom_courses(course_state);
CREATE INDEX IF NOT EXISTS idx_classroom_courses_synced ON google_classroom_courses(last_synced_at);

CREATE INDEX IF NOT EXISTS idx_classroom_students_course ON google_classroom_students(course_id);
CREATE INDEX IF NOT EXISTS idx_classroom_teachers_course ON google_classroom_teachers(course_id);

CREATE INDEX IF NOT EXISTS idx_classroom_coursework_course ON google_classroom_coursework(course_id);
CREATE INDEX IF NOT EXISTS idx_classroom_coursework_state ON google_classroom_coursework(state);
CREATE INDEX IF NOT EXISTS idx_classroom_coursework_due ON google_classroom_coursework(due_date);

CREATE INDEX IF NOT EXISTS idx_classroom_submissions_coursework ON google_classroom_submissions(coursework_id);
CREATE INDEX IF NOT EXISTS idx_classroom_submissions_state ON google_classroom_submissions(state);

-- Google Calendar indexes
CREATE INDEX IF NOT EXISTS idx_calendar_events_user ON google_calendar_events(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_calendar ON google_calendar_events(calendar_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON google_calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_end ON google_calendar_events(end_time);

CREATE INDEX IF NOT EXISTS idx_calendar_calendars_user ON google_calendar_calendars(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_calendars_selected ON google_calendar_calendars(selected);

-- Sync logs indexes
CREATE INDEX IF NOT EXISTS idx_sync_logs_user ON integration_sync_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_logs_service ON integration_sync_logs(service);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON integration_sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_started ON integration_sync_logs(started_at);

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

-- Apply updated_at triggers to all tables
CREATE TRIGGER update_google_oauth_updated_at 
    BEFORE UPDATE ON google_oauth_connections 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classroom_courses_updated_at 
    BEFORE UPDATE ON google_classroom_courses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classroom_students_updated_at 
    BEFORE UPDATE ON google_classroom_students 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classroom_teachers_updated_at 
    BEFORE UPDATE ON google_classroom_teachers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classroom_coursework_updated_at 
    BEFORE UPDATE ON google_classroom_coursework 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classroom_submissions_updated_at 
    BEFORE UPDATE ON google_classroom_submissions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_events_updated_at 
    BEFORE UPDATE ON google_calendar_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_calendars_updated_at 
    BEFORE UPDATE ON google_calendar_calendars 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================

-- Enable RLS on all tables
ALTER TABLE google_oauth_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_classroom_courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_classroom_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_classroom_teachers ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_classroom_coursework ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_classroom_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE google_calendar_calendars ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_sync_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Users can only access their own data
CREATE POLICY "Users can access their own oauth connections" ON google_oauth_connections
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access their own classroom courses" ON google_classroom_courses
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access their own calendar events" ON google_calendar_events
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access their own calendars" ON google_calendar_calendars
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access their own sync logs" ON integration_sync_logs
    FOR ALL USING (auth.uid() = user_id);

-- =============================================
-- GRANTS
-- =============================================

-- Grant permissions to authenticated users
GRANT ALL ON google_oauth_connections TO authenticated;
GRANT ALL ON google_classroom_courses TO authenticated;
GRANT ALL ON google_classroom_students TO authenticated;
GRANT ALL ON google_classroom_teachers TO authenticated;
GRANT ALL ON google_classroom_coursework TO authenticated;
GRANT ALL ON google_classroom_submissions TO authenticated;
GRANT ALL ON google_calendar_events TO authenticated;
GRANT ALL ON google_calendar_calendars TO authenticated;
GRANT ALL ON integration_sync_logs TO authenticated;

-- =============================================
-- USEFUL VIEWS
-- =============================================

-- View for active Google integrations
CREATE OR REPLACE VIEW active_google_integrations AS
SELECT 
    u.email,
    goc.service,
    goc.created_at as connected_at,
    goc.is_active,
    CASE 
        WHEN goc.token_expires_at < NOW() THEN 'EXPIRED'
        WHEN goc.token_expires_at < NOW() + INTERVAL '1 hour' THEN 'EXPIRING_SOON'
        ELSE 'ACTIVE'
    END as token_status
FROM google_oauth_connections goc
JOIN auth.users u ON goc.user_id = u.id
WHERE goc.is_active = true;

-- View for classroom course summary
CREATE OR REPLACE VIEW classroom_course_summary AS
SELECT 
    u.email,
    gcc.name as course_name,
    gcc.course_state,
    gcc.created_at as course_created,
    COUNT(DISTINCT gcs.id) as student_count,
    COUNT(DISTINCT gct.id) as teacher_count,
    COUNT(DISTINCT gcw.id) as assignment_count,
    gcc.last_synced_at
FROM google_classroom_courses gcc
JOIN auth.users u ON gcc.user_id = u.id
LEFT JOIN google_classroom_students gcs ON gcc.id = gcs.course_id
LEFT JOIN google_classroom_teachers gct ON gcc.id = gct.course_id
LEFT JOIN google_classroom_coursework gcw ON gcc.id = gcw.course_id
GROUP BY u.email, gcc.id, gcc.name, gcc.course_state, gcc.created_at, gcc.last_synced_at;

-- View for calendar event summary
CREATE OR REPLACE VIEW calendar_event_summary AS
SELECT 
    u.email,
    gce.summary as event_title,
    gce.start_time,
    gce.end_time,
    gce.location,
    gce.status,
    gcc.summary as calendar_name,
    gce.last_synced_at
FROM google_calendar_events gce
JOIN auth.users u ON gce.user_id = u.id
LEFT JOIN google_calendar_calendars gcc ON gce.calendar_id = gcc.calendar_id AND gce.user_id = gcc.user_id;

-- Grant access to views
GRANT SELECT ON active_google_integrations TO authenticated;
GRANT SELECT ON classroom_course_summary TO authenticated;
GRANT SELECT ON calendar_event_summary TO authenticated;










