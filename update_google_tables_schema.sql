-- Migration: Add missing fields to Google Classroom and Calendar tables
-- This ensures all required fields from user specification are available

-- =============================================
-- 1. UPDATE google_classroom_courses table
-- =============================================

-- Add descriptionHeading and updateTime if they don't exist
DO $$ 
BEGIN
    -- Add descriptionHeading column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'google_classroom_courses' 
        AND column_name = 'description_heading'
    ) THEN
        ALTER TABLE google_classroom_courses 
        ADD COLUMN description_heading VARCHAR(500);
        RAISE NOTICE 'Added description_heading column to google_classroom_courses';
    END IF;

    -- Add updateTime column (if not already present as update_time)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'google_classroom_courses' 
        AND column_name = 'update_time'
    ) THEN
        ALTER TABLE google_classroom_courses 
        ADD COLUMN update_time TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added update_time column to google_classroom_courses';
    END IF;
END $$;

-- =============================================
-- 2. UPDATE google_classroom_submissions table
-- =============================================

-- Add late field if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'google_classroom_submissions' 
        AND column_name = 'late'
    ) THEN
        ALTER TABLE google_classroom_submissions 
        ADD COLUMN late BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added late column to google_classroom_submissions';
    END IF;
END $$;

-- =============================================
-- 3. CREATE google_classroom_announcements table
-- =============================================

CREATE TABLE IF NOT EXISTS public.google_classroom_announcements (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  course_id UUID REFERENCES google_classroom_courses(id) ON DELETE CASCADE,
  announcement_id VARCHAR(255) NOT NULL, -- Google's announcement ID
  text TEXT, -- Announcement text
  materials JSONB, -- Array of materials (files, links, etc.)
  state VARCHAR(50), -- ANNOUNCEMENT_STATE_UNSPECIFIED, PUBLISHED, DELETED, DRAFT
  alternate_link TEXT,
  creation_time TIMESTAMP WITH TIME ZONE,
  update_time TIMESTAMP WITH TIME ZONE,
  scheduled_time TIMESTAMP WITH TIME ZONE, -- If scheduled for future
  assignee_mode VARCHAR(50), -- ALL_STUDENTS, INDIVIDUAL_STUDENTS
  individual_students_options JSONB,
  creator_user_id VARCHAR(255),
  course_work_type VARCHAR(50),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_synced_at TIMESTAMP WITH TIME ZONE,
  
  -- Constraints
  UNIQUE(course_id, announcement_id)
) TABLESPACE pg_default;

-- Indexes for announcements
CREATE INDEX IF NOT EXISTS idx_classroom_announcements_course 
  ON public.google_classroom_announcements(course_id) 
  TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_classroom_announcements_state 
  ON public.google_classroom_announcements(state) 
  TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_classroom_announcements_update_time 
  ON public.google_classroom_announcements(update_time DESC) 
  TABLESPACE pg_default;

-- Trigger for updated_at
CREATE TRIGGER update_classroom_announcements_updated_at 
  BEFORE UPDATE ON public.google_classroom_announcements 
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- 4. ADD EXTRACTED FIELDS FOR EASIER QUERYING
-- =============================================

-- Add teacher_name to google_classroom_teachers (extracted from profile JSONB)
-- This is computed field, we'll extract it in application code
-- But we can create a view for easier access

-- Add student_name to google_classroom_students (extracted from profile JSONB)
-- Similarly, extracted in application code

-- =============================================
-- 5. ROW LEVEL SECURITY for announcements
-- =============================================

ALTER TABLE public.google_classroom_announcements ENABLE ROW LEVEL SECURITY;

-- Policy: Users can access announcements for courses they own
CREATE POLICY "Users can access announcements for their courses" 
  ON public.google_classroom_announcements
  FOR ALL 
  USING (
    EXISTS (
      SELECT 1 FROM public.google_classroom_courses gcc
      WHERE gcc.id = google_classroom_announcements.course_id
      AND gcc.user_id = auth.uid()
    )
  );

-- =============================================
-- 6. GRANT PERMISSIONS
-- =============================================

GRANT ALL ON public.google_classroom_announcements TO authenticated;

-- =============================================
-- 7. CREATE VIEW FOR EASIER QUERYING WITH EXTRACTED NAMES
-- =============================================

-- View for teachers with extracted names
CREATE OR REPLACE VIEW public.google_classroom_teachers_view AS
SELECT 
  gct.id,
  gct.course_id,
  gct.user_id,
  gct.course_user_id,
  gct.profile->>'name.fullName' as teacher_name,
  gct.profile->>'emailAddress' as teacher_email,
  gct.profile as profile_full,
  gct.created_at,
  gct.updated_at
FROM public.google_classroom_teachers gct;

-- View for students with extracted names
CREATE OR REPLACE VIEW public.google_classroom_students_view AS
SELECT 
  gcs.id,
  gcs.course_id,
  gcs.user_id,
  gcs.course_user_id,
  gcs.profile->>'name.fullName' as student_name,
  gcs.profile->>'emailAddress' as student_email,
  gcs.profile as profile_full,
  gcs.student_work_folder,
  gcs.created_at,
  gcs.updated_at
FROM public.google_classroom_students gcs;

-- Grant access to views
GRANT SELECT ON public.google_classroom_teachers_view TO authenticated;
GRANT SELECT ON public.google_classroom_students_view TO authenticated;

-- =============================================
-- NOTES
-- =============================================
-- 1. descriptionHeading: Added as description_heading (snake_case)
-- 2. updateTime: Added as update_time (snake_case) 
-- 3. late: Added as boolean field to submissions
-- 4. Announcements: New table created with all required fields
-- 5. Teacher/Student names: Extracted via views from profile JSONB
-- 6. hangoutLink: Already exists in google_calendar_events table

















