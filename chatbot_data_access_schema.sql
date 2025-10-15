-- Chatbot Data Access Schema
-- This file contains SQL functions and views for chatbot to access user data

-- =============================================
-- CHATBOT DATA ACCESS FUNCTIONS
-- =============================================

-- Function to get user's classroom courses for chatbot
CREATE OR REPLACE FUNCTION get_user_classroom_courses(p_user_id UUID)
RETURNS TABLE (
    course_name VARCHAR(500),
    course_description TEXT,
    course_state VARCHAR(50),
    student_count BIGINT,
    teacher_count BIGINT,
    assignment_count BIGINT,
    last_synced_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gcc.name,
        gcc.description,
        gcc.course_state,
        COUNT(DISTINCT gcs.id) as student_count,
        COUNT(DISTINCT gct.id) as teacher_count,
        COUNT(DISTINCT gcw.id) as assignment_count,
        gcc.last_synced_at
    FROM google_classroom_courses gcc
    LEFT JOIN google_classroom_students gcs ON gcc.id = gcs.course_id
    LEFT JOIN google_classroom_teachers gct ON gcc.id = gct.course_id
    LEFT JOIN google_classroom_coursework gcw ON gcc.id = gcw.course_id
    WHERE gcc.user_id = p_user_id
    GROUP BY gcc.id, gcc.name, gcc.description, gcc.course_state, gcc.last_synced_at
    ORDER BY gcc.created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's upcoming assignments
CREATE OR REPLACE FUNCTION get_user_upcoming_assignments(p_user_id UUID, p_days_ahead INTEGER DEFAULT 7)
RETURNS TABLE (
    course_name VARCHAR(500),
    assignment_title VARCHAR(500),
    due_date TIMESTAMP WITH TIME ZONE,
    max_points DECIMAL(10,2),
    work_type VARCHAR(50),
    description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gcc.name as course_name,
        gcw.title as assignment_title,
        gcw.due_date,
        gcw.max_points,
        gcw.work_type,
        gcw.description
    FROM google_classroom_coursework gcw
    JOIN google_classroom_courses gcc ON gcw.course_id = gcc.id
    WHERE gcc.user_id = p_user_id
    AND gcw.state = 'PUBLISHED'
    AND gcw.due_date IS NOT NULL
    AND gcw.due_date BETWEEN NOW() AND NOW() + INTERVAL '1 day' * p_days_ahead
    ORDER BY gcw.due_date ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's calendar events
CREATE OR REPLACE FUNCTION get_user_calendar_events(p_user_id UUID, p_days_ahead INTEGER DEFAULT 7)
RETURNS TABLE (
    event_title VARCHAR(500),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    location VARCHAR(500),
    description TEXT,
    calendar_name VARCHAR(500),
    all_day BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gce.summary as event_title,
        gce.start_time,
        gce.end_time,
        gce.location,
        gce.description,
        gcc.summary as calendar_name,
        gce.all_day
    FROM google_calendar_events gce
    LEFT JOIN google_calendar_calendars gcc ON gce.calendar_id = gcc.calendar_id AND gce.user_id = gcc.user_id
    WHERE gce.user_id = p_user_id
    AND gce.start_time BETWEEN NOW() AND NOW() + INTERVAL '1 day' * p_days_ahead
    ORDER BY gce.start_time ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's classroom students
CREATE OR REPLACE FUNCTION get_user_classroom_students(p_user_id UUID, p_course_name VARCHAR DEFAULT NULL)
RETURNS TABLE (
    course_name VARCHAR(500),
    student_name VARCHAR(500),
    student_email VARCHAR(255),
    student_id VARCHAR(255)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gcc.name as course_name,
        COALESCE(gcs.profile->>'name', gcs.profile->>'fullName') as student_name,
        gcs.profile->>'emailAddress' as student_email,
        gcs.user_id as student_id
    FROM google_classroom_students gcs
    JOIN google_classroom_courses gcc ON gcs.course_id = gcc.id
    WHERE gcc.user_id = p_user_id
    AND (p_course_name IS NULL OR gcc.name ILIKE '%' || p_course_name || '%')
    ORDER BY gcc.name, gcs.profile->>'name';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's assignment submissions
CREATE OR REPLACE FUNCTION get_user_assignment_submissions(p_user_id UUID, p_course_name VARCHAR DEFAULT NULL)
RETURNS TABLE (
    course_name VARCHAR(500),
    assignment_title VARCHAR(500),
    student_name VARCHAR(500),
    submission_state VARCHAR(50),
    assigned_grade DECIMAL(10,2),
    draft_grade DECIMAL(10,2),
    due_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gcc.name as course_name,
        gcw.title as assignment_title,
        COALESCE(gcs.profile->>'name', gcs.profile->>'fullName') as student_name,
        gcs_sub.state as submission_state,
        gcs_sub.assigned_grade,
        gcs_sub.draft_grade,
        gcw.due_date
    FROM google_classroom_submissions gcs_sub
    JOIN google_classroom_coursework gcw ON gcs_sub.coursework_id = gcw.id
    JOIN google_classroom_courses gcc ON gcw.course_id = gcc.id
    JOIN google_classroom_students gcs ON gcs.course_id = gcc.id
    WHERE gcc.user_id = p_user_id
    AND (p_course_name IS NULL OR gcc.name ILIKE '%' || p_course_name || '%')
    ORDER BY gcc.name, gcw.due_date DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================
-- CHATBOT CONTEXT VIEWS
-- =============================================

-- View for chatbot context - user's current academic status
CREATE OR REPLACE VIEW chatbot_user_context AS
SELECT 
    u.id as user_id,
    u.email,
    up.first_name,
    up.last_name,
    up.role,
    up.grade,
    up.subjects,
    up.learning_goals,
    up.interests,
    up.learning_style,
    -- Google Classroom integration status
    CASE WHEN goc_classroom.user_id IS NOT NULL THEN true ELSE false END as has_classroom_access,
    goc_classroom.created_at as classroom_connected_at,
    -- Google Calendar integration status
    CASE WHEN goc_calendar.user_id IS NOT NULL THEN true ELSE false END as has_calendar_access,
    goc_calendar.created_at as calendar_connected_at,
    -- Counts
    (SELECT COUNT(*) FROM google_classroom_courses WHERE user_id = u.id) as total_courses,
    (SELECT COUNT(*) FROM google_calendar_events WHERE user_id = u.id AND start_time >= NOW()) as upcoming_events,
    (SELECT COUNT(*) FROM google_classroom_coursework gcw 
     JOIN google_classroom_courses gcc ON gcw.course_id = gcc.id 
     WHERE gcc.user_id = u.id AND gcw.due_date >= NOW()) as upcoming_assignments
FROM auth.users u
LEFT JOIN user_profiles up ON u.id = up.user_id
LEFT JOIN google_oauth_connections goc_classroom ON u.id = goc_classroom.user_id AND goc_classroom.service = 'classroom' AND goc_classroom.is_active = true
LEFT JOIN google_oauth_connections goc_calendar ON u.id = goc_calendar.user_id AND goc_calendar.service = 'calendar' AND goc_calendar.is_active = true;

-- View for chatbot - recent activity summary
CREATE OR REPLACE VIEW chatbot_recent_activity AS
SELECT 
    u.id as user_id,
    u.email,
    -- Recent courses
    ARRAY_AGG(DISTINCT gcc.name) FILTER (WHERE gcc.id IS NOT NULL) as recent_courses,
    -- Recent assignments
    ARRAY_AGG(DISTINCT gcw.title) FILTER (WHERE gcw.id IS NOT NULL) as recent_assignments,
    -- Recent events
    ARRAY_AGG(DISTINCT gce.summary) FILTER (WHERE gce.id IS NOT NULL) as recent_events,
    -- Last sync times
    MAX(gcc.last_synced_at) as last_classroom_sync,
    MAX(gce.last_synced_at) as last_calendar_sync
FROM auth.users u
LEFT JOIN google_classroom_courses gcc ON u.id = gcc.user_id
LEFT JOIN google_classroom_coursework gcw ON gcc.id = gcw.course_id
LEFT JOIN google_calendar_events gce ON u.id = gce.user_id
WHERE gcc.last_synced_at >= NOW() - INTERVAL '7 days' 
   OR gce.last_synced_at >= NOW() - INTERVAL '7 days'
GROUP BY u.id, u.email;

-- =============================================
-- CHATBOT QUERY FUNCTIONS
-- =============================================

-- Function to search courses by name or description
CREATE OR REPLACE FUNCTION search_user_courses(p_user_id UUID, p_search_term TEXT)
RETURNS TABLE (
    course_name VARCHAR(500),
    course_description TEXT,
    course_state VARCHAR(50),
    assignment_count BIGINT,
    last_synced_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gcc.name,
        gcc.description,
        gcc.course_state,
        COUNT(DISTINCT gcw.id) as assignment_count,
        gcc.last_synced_at
    FROM google_classroom_courses gcc
    LEFT JOIN google_classroom_coursework gcw ON gcc.id = gcw.course_id
    WHERE gcc.user_id = p_user_id
    AND (gcc.name ILIKE '%' || p_search_term || '%' 
         OR gcc.description ILIKE '%' || p_search_term || '%')
    GROUP BY gcc.id, gcc.name, gcc.description, gcc.course_state, gcc.last_synced_at
    ORDER BY gcc.last_synced_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get assignments by course
CREATE OR REPLACE FUNCTION get_assignments_by_course(p_user_id UUID, p_course_name VARCHAR)
RETURNS TABLE (
    assignment_title VARCHAR(500),
    due_date TIMESTAMP WITH TIME ZONE,
    max_points DECIMAL(10,2),
    work_type VARCHAR(50),
    description TEXT,
    state VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gcw.title,
        gcw.due_date,
        gcw.max_points,
        gcw.work_type,
        gcw.description,
        gcw.state
    FROM google_classroom_coursework gcw
    JOIN google_classroom_courses gcc ON gcw.course_id = gcc.id
    WHERE gcc.user_id = p_user_id
    AND gcc.name ILIKE '%' || p_course_name || '%'
    ORDER BY gcw.due_date ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get events by date range
CREATE OR REPLACE FUNCTION get_events_by_date_range(p_user_id UUID, p_start_date TIMESTAMP, p_end_date TIMESTAMP)
RETURNS TABLE (
    event_title VARCHAR(500),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    location VARCHAR(500),
    calendar_name VARCHAR(500),
    all_day BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gce.summary,
        gce.start_time,
        gce.end_time,
        gce.location,
        gcc.summary as calendar_name,
        gce.all_day
    FROM google_calendar_events gce
    LEFT JOIN google_calendar_calendars gcc ON gce.calendar_id = gcc.calendar_id AND gce.user_id = gcc.user_id
    WHERE gce.user_id = p_user_id
    AND gce.start_time >= p_start_date
    AND gce.start_time <= p_end_date
    ORDER BY gce.start_time ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================
-- CHATBOT RESPONSE HELPERS
-- =============================================

-- Function to get formatted course summary for chatbot
CREATE OR REPLACE FUNCTION get_course_summary_for_chatbot(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
    result TEXT := '';
    course_record RECORD;
BEGIN
    FOR course_record IN 
        SELECT 
            gcc.name,
            gcc.course_state,
            COUNT(DISTINCT gcs.id) as student_count,
            COUNT(DISTINCT gcw.id) as assignment_count
        FROM google_classroom_courses gcc
        LEFT JOIN google_classroom_students gcs ON gcc.id = gcs.course_id
        LEFT JOIN google_classroom_coursework gcw ON gcc.id = gcw.course_id
        WHERE gcc.user_id = p_user_id
        GROUP BY gcc.id, gcc.name, gcc.course_state
        ORDER BY gcc.name
    LOOP
        result := result || '• ' || course_record.name || ' (' || course_record.course_state || ') - ' || 
                 course_record.student_count || ' students, ' || course_record.assignment_count || ' assignments' || E'\n';
    END LOOP;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get formatted upcoming assignments for chatbot
CREATE OR REPLACE FUNCTION get_upcoming_assignments_for_chatbot(p_user_id UUID, p_days INTEGER DEFAULT 7)
RETURNS TEXT AS $$
DECLARE
    result TEXT := '';
    assignment_record RECORD;
BEGIN
    FOR assignment_record IN 
        SELECT 
            gcc.name as course_name,
            gcw.title as assignment_title,
            gcw.due_date,
            gcw.max_points
        FROM google_classroom_coursework gcw
        JOIN google_classroom_courses gcc ON gcw.course_id = gcc.id
        WHERE gcc.user_id = p_user_id
        AND gcw.state = 'PUBLISHED'
        AND gcw.due_date IS NOT NULL
        AND gcw.due_date BETWEEN NOW() AND NOW() + INTERVAL '1 day' * p_days
        ORDER BY gcw.due_date ASC
        LIMIT 10
    LOOP
        result := result || '• ' || assignment_record.assignment_title || ' (' || assignment_record.course_name || ') - Due: ' || 
                 TO_CHAR(assignment_record.due_date, 'Mon DD, YYYY at HH24:MI') || 
                 CASE WHEN assignment_record.max_points IS NOT NULL THEN ' (' || assignment_record.max_points || ' points)' ELSE '' END || E'\n';
    END LOOP;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================
-- GRANTS FOR CHATBOT ACCESS
-- =============================================

-- Grant execute permissions on functions to authenticated users
GRANT EXECUTE ON FUNCTION get_user_classroom_courses(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_upcoming_assignments(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_calendar_events(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_classroom_students(UUID, VARCHAR) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_assignment_submissions(UUID, VARCHAR) TO authenticated;
GRANT EXECUTE ON FUNCTION search_user_courses(UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_assignments_by_course(UUID, VARCHAR) TO authenticated;
GRANT EXECUTE ON FUNCTION get_events_by_date_range(UUID, TIMESTAMP, TIMESTAMP) TO authenticated;
GRANT EXECUTE ON FUNCTION get_course_summary_for_chatbot(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_upcoming_assignments_for_chatbot(UUID, INTEGER) TO authenticated;

-- Grant select permissions on views
GRANT SELECT ON chatbot_user_context TO authenticated;
GRANT SELECT ON chatbot_recent_activity TO authenticated;

-- =============================================
-- EXAMPLE USAGE FOR CHATBOT
-- =============================================

/*
-- Example queries the chatbot can use:

-- 1. Get user's basic context
SELECT * FROM chatbot_user_context WHERE user_id = auth.uid();

-- 2. Get upcoming assignments
SELECT * FROM get_user_upcoming_assignments(auth.uid(), 7);

-- 3. Get upcoming events
SELECT * FROM get_user_calendar_events(auth.uid(), 7);

-- 4. Search for courses
SELECT * FROM search_user_courses(auth.uid(), 'math');

-- 5. Get assignments for a specific course
SELECT * FROM get_assignments_by_course(auth.uid(), 'Algebra 101');

-- 6. Get formatted summaries for chatbot responses
SELECT get_course_summary_for_chatbot(auth.uid());
SELECT get_upcoming_assignments_for_chatbot(auth.uid(), 7);

-- 7. Get events for a specific date range
SELECT * FROM get_events_by_date_range(auth.uid(), '2024-01-01', '2024-01-31');
*/
