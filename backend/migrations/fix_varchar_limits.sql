-- Fix VARCHAR(20) limits that are causing "value too long" errors
-- Comprehensive fix for all Google Classroom tables

-- First, identify and drop all views that depend on columns we're changing
DO $$
DECLARE
    view_name TEXT;
BEGIN
    -- Find all views that depend on the user_id columns we're changing
    FOR view_name IN
        SELECT DISTINCT dependent_view.relname
        FROM pg_depend
        JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
        JOIN pg_class dependent_view ON pg_rewrite.ev_class = dependent_view.oid
        JOIN pg_class dependent_table ON pg_depend.refobjid = dependent_table.oid
        JOIN pg_attribute ON pg_depend.refobjid = pg_attribute.attrelid
            AND pg_depend.refobjsubid = pg_attribute.attnum
        WHERE dependent_table.relname IN ('google_classroom_teachers', 'google_classroom_students', 'google_classroom_coursework', 'google_classroom_submissions', 'google_classroom_courses', 'google_classroom_announcements')
        AND pg_attribute.attname IN ('user_id', 'coursework_id', 'submission_id', 'course_id', 'owner_id', 'teacher_group_email', 'course_group_email', 'announcement_id', 'creator_user_id', 'topic_id', 'coursework_id_google')
        AND dependent_view.relkind = 'v'
    LOOP
        EXECUTE 'DROP VIEW IF EXISTS ' || view_name || ' CASCADE';
        RAISE NOTICE 'Dropped view: %', view_name;
    END LOOP;
END $$;

-- Now alter the columns
-- Fix google_classroom_coursework table
ALTER TABLE google_classroom_coursework
ALTER COLUMN coursework_id TYPE VARCHAR(100);

ALTER TABLE google_classroom_coursework
ALTER COLUMN creator_user_id TYPE VARCHAR(100);

ALTER TABLE google_classroom_coursework
ALTER COLUMN topic_id TYPE VARCHAR(100);

-- Additional coursework fields that might be VARCHAR(20)
ALTER TABLE google_classroom_coursework
ALTER COLUMN work_type TYPE VARCHAR(100);

ALTER TABLE google_classroom_coursework
ALTER COLUMN assignee_mode TYPE VARCHAR(100);

ALTER TABLE google_classroom_coursework
ALTER COLUMN submission_modification_mode TYPE VARCHAR(100);

ALTER TABLE google_classroom_coursework
ALTER COLUMN grade_category TYPE VARCHAR(100);

-- Fix google_classroom_submissions table
ALTER TABLE google_classroom_submissions
ALTER COLUMN submission_id TYPE VARCHAR(100);

ALTER TABLE google_classroom_submissions
ALTER COLUMN coursework_id_google TYPE VARCHAR(100);

ALTER TABLE google_classroom_submissions
ALTER COLUMN user_id TYPE VARCHAR(100);

-- Fix google_classroom_teachers table
ALTER TABLE google_classroom_teachers
ALTER COLUMN user_id TYPE VARCHAR(100);

-- Fix google_classroom_students table
ALTER TABLE google_classroom_students
ALTER COLUMN user_id TYPE VARCHAR(100);

-- Fix google_classroom_courses table
ALTER TABLE google_classroom_courses
ALTER COLUMN course_id TYPE VARCHAR(100);

ALTER TABLE google_classroom_courses
ALTER COLUMN owner_id TYPE VARCHAR(100);

ALTER TABLE google_classroom_courses
ALTER COLUMN teacher_group_email TYPE VARCHAR(200);

ALTER TABLE google_classroom_courses
ALTER COLUMN course_group_email TYPE VARCHAR(200);

-- Fix google_classroom_announcements table
ALTER TABLE google_classroom_announcements
ALTER COLUMN announcement_id TYPE VARCHAR(100);

ALTER TABLE google_classroom_announcements
ALTER COLUMN creator_user_id TYPE VARCHAR(100);

-- Add missing embedding columns for tables that need embeddings
-- These tables failed during embedding regeneration

-- Add embedding column to google_classroom_courses
ALTER TABLE google_classroom_courses
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Add embedding column to google_classroom_teachers
ALTER TABLE google_classroom_teachers
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Add embedding column to google_classroom_students
ALTER TABLE google_classroom_students
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Add embedding column to google_calendar_calendars
ALTER TABLE google_calendar_calendars
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Note: Any views that were dropped will need to be recreated by the application if needed
