-- SQL Queries to Verify Synced Data in Supabase
-- Run these in Supabase SQL Editor to check if data was stored

-- =============================================
-- VERIFY GOOGLE CLASSROOM DATA
-- =============================================

-- 1. Check courses
SELECT 
  COUNT(*) as total_courses,
  COUNT(DISTINCT user_id) as unique_users,
  MIN(last_synced_at) as oldest_sync,
  MAX(last_synced_at) as latest_sync
FROM google_classroom_courses;

-- 2. Check teachers
SELECT 
  COUNT(*) as total_teachers,
  COUNT(DISTINCT course_id) as courses_with_teachers
FROM google_classroom_teachers;

-- 3. Check students
SELECT 
  COUNT(*) as total_students,
  COUNT(DISTINCT course_id) as courses_with_students
FROM google_classroom_students;

-- 4. Check announcements
SELECT 
  COUNT(*) as total_announcements,
  COUNT(DISTINCT course_id) as courses_with_announcements
FROM google_classroom_announcements;

-- 5. Check coursework (may be empty due to scope issue)
SELECT 
  COUNT(*) as total_coursework
FROM google_classroom_coursework;

-- 6. Check submissions (may be empty due to scope issue)
SELECT 
  COUNT(*) as total_submissions
FROM google_classroom_submissions;

-- =============================================
-- VERIFY GOOGLE CALENDAR DATA
-- =============================================

-- 7. Check calendars
SELECT 
  COUNT(*) as total_calendars,
  COUNT(DISTINCT user_id) as unique_users
FROM google_calendar_calendars;

-- 8. Check events
SELECT 
  COUNT(*) as total_events,
  COUNT(DISTINCT user_id) as unique_users,
  MIN(start_time) as earliest_event,
  MAX(start_time) as latest_event
FROM google_calendar_events;

-- =============================================
-- DETAILED VIEW OF STORED DATA
-- =============================================

-- View all courses with their details
SELECT 
  id,
  course_id,
  name,
  section,
  room,
  course_state,
  last_synced_at,
  created_at
FROM google_classroom_courses
ORDER BY last_synced_at DESC
LIMIT 10;

-- View courses with teacher count
SELECT 
  c.course_id,
  c.name,
  c.section,
  COUNT(DISTINCT t.id) as teacher_count,
  COUNT(DISTINCT s.id) as student_count,
  COUNT(DISTINCT a.id) as announcement_count,
  c.last_synced_at
FROM google_classroom_courses c
LEFT JOIN google_classroom_teachers t ON c.id = t.course_id
LEFT JOIN google_classroom_students s ON c.id = s.course_id
LEFT JOIN google_classroom_announcements a ON c.id = a.course_id
GROUP BY c.id, c.course_id, c.name, c.section, c.last_synced_at
ORDER BY c.last_synced_at DESC;

-- View recent announcements
SELECT 
  a.text,
  c.name as course_name,
  a.update_time,
  a.last_synced_at
FROM google_classroom_announcements a
JOIN google_classroom_courses c ON a.course_id = c.id
ORDER BY a.update_time DESC
LIMIT 10;

-- View upcoming calendar events
SELECT 
  summary,
  start_time,
  end_time,
  location,
  hangout_link,
  last_synced_at
FROM google_calendar_events
WHERE start_time >= NOW()
ORDER BY start_time ASC
LIMIT 10;

-- =============================================
-- QUICK SUMMARY (RUN THIS FIRST)
-- =============================================

SELECT 
  'Courses' as table_name,
  COUNT(*) as record_count
FROM google_classroom_courses
UNION ALL
SELECT 
  'Teachers',
  COUNT(*)
FROM google_classroom_teachers
UNION ALL
SELECT 
  'Students',
  COUNT(*)
FROM google_classroom_students
UNION ALL
SELECT 
  'Announcements',
  COUNT(*)
FROM google_classroom_announcements
UNION ALL
SELECT 
  'Coursework',
  COUNT(*)
FROM google_classroom_coursework
UNION ALL
SELECT 
  'Submissions',
  COUNT(*)
FROM google_classroom_submissions
UNION ALL
SELECT 
  'Calendars',
  COUNT(*)
FROM google_calendar_calendars
UNION ALL
SELECT 
  'Calendar Events',
  COUNT(*)
FROM google_calendar_events;







