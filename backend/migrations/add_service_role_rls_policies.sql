-- Add RLS Policies for Service Role Access
-- This allows the backend (using service role key) to access all classroom data
-- Run this in Supabase SQL Editor

-- =============================================
-- SERVICE ROLE RLS POLICIES
-- =============================================

-- Allow service role to access all google_classroom_courses
DROP POLICY IF EXISTS "Service role can access all classroom courses" ON google_classroom_courses;
CREATE POLICY "Service role can access all classroom courses" 
    ON google_classroom_courses
    FOR ALL 
    USING (auth.role() = 'service_role');

-- Allow service role to access all google_classroom_students
DROP POLICY IF EXISTS "Service role can access all classroom students" ON google_classroom_students;
CREATE POLICY "Service role can access all classroom students" 
    ON google_classroom_students
    FOR ALL 
    USING (auth.role() = 'service_role');

-- Allow service role to access all google_classroom_teachers
DROP POLICY IF EXISTS "Service role can access all classroom teachers" ON google_classroom_teachers;
CREATE POLICY "Service role can access all classroom teachers" 
    ON google_classroom_teachers
    FOR ALL 
    USING (auth.role() = 'service_role');

-- Allow service role to access all google_classroom_coursework
DROP POLICY IF EXISTS "Service role can access all classroom coursework" ON google_classroom_coursework;
CREATE POLICY "Service role can access all classroom coursework" 
    ON google_classroom_coursework
    FOR ALL 
    USING (auth.role() = 'service_role');

-- Allow service role to access all google_classroom_submissions
DROP POLICY IF EXISTS "Service role can access all classroom submissions" ON google_classroom_submissions;
CREATE POLICY "Service role can access all classroom submissions" 
    ON google_classroom_submissions
    FOR ALL 
    USING (auth.role() = 'service_role');

-- Allow service role to access all google_classroom_announcements
DROP POLICY IF EXISTS "Service role can access all classroom announcements" ON google_classroom_announcements;
CREATE POLICY "Service role can access all classroom announcements" 
    ON google_classroom_announcements
    FOR ALL 
    USING (auth.role() = 'service_role');

-- Allow service role to access all google_calendar_events
DROP POLICY IF EXISTS "Service role can access all calendar events" ON google_calendar_events;
CREATE POLICY "Service role can access all calendar events" 
    ON google_calendar_events
    FOR ALL 
    USING (auth.role() = 'service_role');

-- Allow service role to access all google_calendar_calendars
DROP POLICY IF EXISTS "Service role can access all calendars" ON google_calendar_calendars;
CREATE POLICY "Service role can access all calendars" 
    ON google_calendar_calendars
    FOR ALL 
    USING (auth.role() = 'service_role');

-- =============================================
-- GRANT PERMISSIONS
-- =============================================

-- Grant ALL permissions to service_role on all tables
GRANT ALL ON google_classroom_courses TO service_role;
GRANT ALL ON google_classroom_students TO service_role;
GRANT ALL ON google_classroom_teachers TO service_role;
GRANT ALL ON google_classroom_coursework TO service_role;
GRANT ALL ON google_classroom_submissions TO service_role;
GRANT ALL ON google_classroom_announcements TO service_role;
GRANT ALL ON google_calendar_events TO service_role;
GRANT ALL ON google_calendar_calendars TO service_role;

-- Grant permissions on user_profiles for admin lookups
GRANT SELECT ON user_profiles TO service_role;

-- Grant permissions on google_integrations for token lookups
GRANT ALL ON google_integrations TO service_role;

