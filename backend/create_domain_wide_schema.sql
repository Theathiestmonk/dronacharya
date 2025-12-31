-- Add domain-wide support to Google Classroom tables
-- This allows storing comprehensive classroom data from entire Google Workspace domain

-- Add is_domain_wide column to google_classroom_courses
ALTER TABLE google_classroom_courses
ADD COLUMN IF NOT EXISTS is_domain_wide BOOLEAN DEFAULT FALSE;

-- Add is_domain_wide column to google_classroom_teachers
ALTER TABLE google_classroom_teachers
ADD COLUMN IF NOT EXISTS is_domain_wide BOOLEAN DEFAULT FALSE;

-- Add is_domain_wide column to google_classroom_students
ALTER TABLE google_classroom_students
ADD COLUMN IF NOT EXISTS is_domain_wide BOOLEAN DEFAULT FALSE;

-- Add is_domain_wide column to google_classroom_coursework
ALTER TABLE google_classroom_coursework
ADD COLUMN IF NOT EXISTS is_domain_wide BOOLEAN DEFAULT FALSE;

-- Add is_domain_wide column to google_classroom_submissions
ALTER TABLE google_classroom_submissions
ADD COLUMN IF NOT EXISTS is_domain_wide BOOLEAN DEFAULT FALSE;

-- Add is_domain_wide column to google_classroom_announcements
ALTER TABLE google_classroom_announcements
ADD COLUMN IF NOT EXISTS is_domain_wide BOOLEAN DEFAULT FALSE;

-- Create indexes for better performance on domain-wide queries
CREATE INDEX IF NOT EXISTS idx_google_classroom_courses_domain_wide
ON google_classroom_courses(is_domain_wide);

CREATE INDEX IF NOT EXISTS idx_google_classroom_teachers_domain_wide
ON google_classroom_teachers(is_domain_wide);

CREATE INDEX IF NOT EXISTS idx_google_classroom_students_domain_wide
ON google_classroom_students(is_domain_wide);

CREATE INDEX IF NOT EXISTS idx_google_classroom_coursework_domain_wide
ON google_classroom_coursework(is_domain_wide);

CREATE INDEX IF NOT EXISTS idx_google_classroom_submissions_domain_wide
ON google_classroom_submissions(is_domain_wide);

CREATE INDEX IF NOT EXISTS idx_google_classroom_announcements_domain_wide
ON google_classroom_announcements(is_domain_wide);

-- Create a view for domain-wide classroom analytics
CREATE OR REPLACE VIEW domain_classroom_analytics AS
SELECT
    c.course_id,
    c.name as course_name,
    c.course_state,
    c.section,
    c.room,
    COUNT(DISTINCT t.id) as teacher_count,
    COUNT(DISTINCT s.id) as student_count,
    COUNT(DISTINCT cw.id) as coursework_count,
    COUNT(DISTINCT sub.id) as submission_count,
    COUNT(DISTINCT ann.id) as announcement_count,
    MAX(c.last_synced_at) as last_synced_at
FROM google_classroom_courses c
LEFT JOIN google_classroom_teachers t ON c.id = t.course_id AND t.is_domain_wide = true
LEFT JOIN google_classroom_students s ON c.id = s.course_id AND s.is_domain_wide = true
LEFT JOIN google_classroom_coursework cw ON c.id = cw.course_id AND cw.is_domain_wide = true
LEFT JOIN google_classroom_submissions sub ON cw.id = sub.coursework_id AND sub.is_domain_wide = true
LEFT JOIN google_classroom_announcements ann ON c.id = ann.course_id AND ann.is_domain_wide = true
WHERE c.is_domain_wide = true
GROUP BY c.id, c.course_id, c.name, c.course_state, c.section, c.room;

-- Grant permissions for the view
GRANT SELECT ON domain_classroom_analytics TO authenticated;




