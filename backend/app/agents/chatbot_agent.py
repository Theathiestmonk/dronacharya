import os
import json
import re
from app.core.openai_client import get_openai_client, get_default_gpt_model
from app.agents.youtube_intent_classifier import process_video_query
from app.agents.web_crawler_agent import get_web_enhanced_response
from dotenv import load_dotenv
try:
    from sqlalchemy.orm import Session
    from app.core.database import get_db
    from app.models.admin import Admin, ClassroomData, CalendarData
    ADMIN_FEATURES_AVAILABLE = True
except ImportError:
    ADMIN_FEATURES_AVAILABLE = False
    print("Warning: Admin features not available - missing dependencies")

# Ensure environment variables are loaded
load_dotenv()

# Note: rapidfuzz is optional, we'll handle it gracefully
try:
    from rapidfuzz import fuzz  # type: ignore
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    # Define a dummy fuzz function to avoid errors
    class DummyFuzz:
        @staticmethod
        def token_set_ratio(a, b):
            return 0
    fuzz = DummyFuzz()
    print("Warning: rapidfuzz not available, fuzzy matching disabled")

# Path to local knowledge base JSON
KB_PATH = os.path.join(os.path.dirname(__file__), '../../core/knowledge_base.json')

def retrieve_from_json(query: str, threshold: int = 50) -> str | None:
    """Fuzzy match the user query to questions in the local JSON KB."""
    try:
        with open(KB_PATH, 'r', encoding='utf-8') as f:
            kb = json.load(f)
        best_score = 0
        best_answer = None
        for entry in kb.get('entries', []):
            score = fuzz.token_set_ratio(query.lower(), entry['question'].lower())
            print(f"[Chatbot] Comparing to: {entry['question']} | Score: {score}")
            if score > best_score and score >= threshold:
                best_score = score
                best_answer = entry['answer']
        return best_answer
    except Exception as e:
        print(f"[Chatbot] Error reading KB: {e}")
    return None

def get_student_coursework_data(student_user_id: str, student_email: str = None, limit_coursework: int = None, user_grade: str = None, work_type_filter: str = None) -> dict:
    """
    Get coursework data directly from google_classroom_coursework table for a student.
    This is used when students ask about assignments/homework - we check coursework table directly
    instead of going through courses (since courses may be synced by admin).
    
    Strategy: Query coursework directly and join with courses to get course names.
    We get all coursework that exists (synced by students or admin) and filter by
    checking if submissions exist for this student.
    
    Also filters by student's grade if provided - only shows assignments from courses matching their grade.
    
    Args:
        work_type_filter: Filter by work_type (e.g., 'ASSIGNMENT', 'QUIZ', etc.). 
                         If 'homework' is provided, filters for homework-specific work types.
    """
    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        
        print(f"[Chatbot] Getting student coursework for user_id: {student_user_id}, email: {student_email}")
        if user_grade:
            print(f"[Chatbot] Grade filter: Will filter coursework for Grade {user_grade} student")
        
        # Get student's Google email if not provided
        if not student_email:
            profile_result = supabase.table('user_profiles').select('email').eq('user_id', student_user_id).single().execute()
            if profile_result.data:
                student_email = profile_result.data.get('email')
        
        # Get student's submissions first to identify which coursework belongs to them
        # user_id in submissions table is the Google user ID (email)
        submissions_result = None
        coursework_ids_from_submissions = set()
        
        if student_email:
            # Get submissions for this student - this identifies their coursework
            submissions_result = supabase.table('google_classroom_submissions').select(
                'coursework_id, course_id, state, assigned_grade, draft_grade'
            ).eq('user_id', student_email).execute()
            
            if submissions_result.data:
                print(f"[Chatbot] Found {len(submissions_result.data)} submissions for student")
                # Extract unique coursework IDs from submissions
                for sub in submissions_result.data:
                    cw_id = sub.get('coursework_id')  # UUID in our DB
                    if cw_id:
                        coursework_ids_from_submissions.add(cw_id)
        
        # If no submissions found, try alternative: get coursework from courses synced by this student
        # (when student syncs, coursework is linked to courses)
        if not coursework_ids_from_submissions:
            print(f"[Chatbot] No submissions found, trying to get coursework from student-synced courses...")
            # Get courses synced by this student (user_id in google_classroom_courses)
            student_courses_result = supabase.table('google_classroom_courses').select(
                'id'
            ).eq('user_id', student_user_id).execute()
            
            if student_courses_result.data:
                student_course_ids = [c.get('id') for c in student_courses_result.data]
                # Get coursework for these courses
                coursework_from_student = supabase.table('google_classroom_coursework').select(
                    'id'
                ).in_('course_id', student_course_ids).execute()
                
                if coursework_from_student.data:
                    coursework_ids_from_submissions = set([cw.get('id') for cw in coursework_from_student.data])
                    print(f"[Chatbot] Found {len(coursework_ids_from_submissions)} coursework from student-synced courses")
        
        if not coursework_ids_from_submissions:
            print(f"[Chatbot] No coursework found for this student")
            return {"classroom_data": []}
        
        # Get coursework details for student's coursework only
        coursework_result = supabase.table('google_classroom_coursework').select(
            'id, course_id, coursework_id, title, description, due_date, due_time, state, alternate_link, max_points, work_type'
        ).in_('id', list(coursework_ids_from_submissions)).order('due_date', desc=False).limit(limit_coursework or 100).execute()
        
        if not coursework_result.data:
            print(f"[Chatbot] No coursework details found")
            return {"classroom_data": []}
        
        print(f"[Chatbot] Found {len(coursework_result.data)} coursework items for this student")
        
        # Get course IDs to fetch course names
        course_ids = list(set([cw.get('course_id') for cw in coursework_result.data if cw.get('course_id')]))
        courses_map = {}
        if course_ids:
            courses_result = supabase.table('google_classroom_courses').select(
                'id, course_id, name, section, alternate_link'
            ).in_('id', course_ids).execute()
            
            if courses_result.data:
                # Filter courses by grade if provided
                user_grade_num = None
                if user_grade:
                    grade_match = re.search(r'(\d+)', str(user_grade))
                    if grade_match:
                        user_grade_num = grade_match.group(1)
                        print(f"[Chatbot] Extracted grade number: {user_grade_num}")
                
                # First pass: collect all courses
                all_courses = []
                for course in courses_result.data:
                    all_courses.append(course)
                
                # Apply grade filtering only if grade is provided
                # But if filtering would exclude all courses, skip filtering and use email/user_id based access
                if user_grade_num:
                    filtered_courses = []
                    for course in all_courses:
                        course_name = course.get('name', '')
                        course_section = course.get('section') or ''  # Handle None case
                        
                        # Check if course name or section contains the grade number (e.g., "Grade 6", "G6", "6")
                        grade_pattern = rf'\b(?:Grade|G|grade)\s*{user_grade_num}\b|\b{user_grade_num}\b'
                        name_matches = bool(re.search(grade_pattern, course_name, re.IGNORECASE))
                        section_matches = bool(re.search(grade_pattern, course_section, re.IGNORECASE)) if course_section else False
                        
                        if name_matches or section_matches:
                            filtered_courses.append(course)
                            print(f"[Chatbot] ✅ Course '{course_name}' matches Grade {user_grade_num}")
                        else:
                            print(f"[Chatbot] ⚠️ Skipping course '{course_name}' (section: {course_section or 'N/A'}) - doesn't match Grade {user_grade_num}")
                    
                    # If grade filtering would exclude all courses, skip filtering and use email/user_id based access
                    if not filtered_courses and len(all_courses) > 0:
                        print(f"[Chatbot] ⚠️ Grade filtering would exclude all courses. Using email/user_id based access instead (showing all {len(all_courses)} courses)")
                        for course in all_courses:
                            courses_map[course.get('id')] = course
                    else:
                        # Use filtered courses
                        for course in filtered_courses:
                            courses_map[course.get('id')] = course
                else:
                    # No grade filtering - use all courses (email/user_id based access)
                    for course in all_courses:
                        courses_map[course.get('id')] = course
        
        # Build submissions map for submission status
        submissions_map = {}
        if submissions_result and submissions_result.data:
            for sub in submissions_result.data:
                cw_id = sub.get('coursework_id')
                if cw_id:
                    submissions_map[cw_id] = {
                        'state': sub.get('state'),
                        'assigned_grade': sub.get('assigned_grade'),
                        'draft_grade': sub.get('draft_grade')
                    }
        
        # Format coursework with course info (only include courses that passed grade filter)
        coursework_list = []
        for cw in coursework_result.data:
            course_id = cw.get('course_id')
            course = courses_map.get(course_id) if course_id else None
            
            # Skip if course was filtered out by grade
            if not course:
                continue
            
            course_name = course.get('name', 'Unknown Course')
            course_link = course.get('alternate_link')
            
            # Filter by work_type if specified
            if work_type_filter:
                cw_work_type = cw.get('work_type', '').upper()
                if work_type_filter.upper() == 'HOMEWORK':
                    # For homework, filter for ASSIGNMENT type (homework is typically assignments)
                    # You can add other homework-related work types here if needed
                    if cw_work_type != 'ASSIGNMENT':
                        continue
                elif work_type_filter.upper() != cw_work_type:
                    continue
            
            # Get submission info if available
            sub_info = submissions_map.get(cw.get('id'))
            
            coursework_list.append({
                'course_name': course_name,
                'course_link': course_link,
                'title': cw.get('title', ''),
                'description': cw.get('description', ''),
                'due_date': cw.get('due_date', ''),
                'due_time': cw.get('due_time', ''),
                'state': cw.get('state', ''),
                'alternate_link': cw.get('alternate_link', ''),
                'max_points': cw.get('max_points', ''),
                'work_type': cw.get('work_type', ''),
                'submission_state': sub_info.get('state') if sub_info else None,
                'assigned_grade': sub_info.get('assigned_grade') if sub_info else None,
                'draft_grade': sub_info.get('draft_grade') if sub_info else None
            })
        
        # Group by course
        courses_dict = {}
        for cw in coursework_list:
            course_name = cw.get('course_name', 'Unknown Course')
            if course_name not in courses_dict:
                courses_dict[course_name] = {
                    'name': course_name,
                    'course_link': cw.get('course_link'),
                    'coursework': []
                }
            courses_dict[course_name]['coursework'].append({
                'title': cw.get('title', ''),
                'alternate_link': cw.get('alternate_link', ''),  # Put link right after title for visibility
                'description': cw.get('description', ''),
                'due_date': cw.get('due_date', ''),
                'due_time': cw.get('due_time', ''),
                'state': cw.get('state', ''),
                'max_points': cw.get('max_points', ''),
                'work_type': cw.get('work_type', ''),
                'submission_state': cw.get('submission_state'),
                'assigned_grade': cw.get('assigned_grade'),
                'draft_grade': cw.get('draft_grade')
            })
        
        formatted_data = list(courses_dict.values())
        
        # Debug: Check if alternate_link is present in coursework
        for course_data in formatted_data:
            coursework_items = course_data.get('coursework', [])
            for cw in coursework_items:
                alt_link = cw.get('alternate_link', '')
                if not alt_link:
                    print(f"[Chatbot] ⚠️ WARNING: Assignment '{cw.get('title', 'Unknown')}' has no alternate_link!")
                else:
                    print(f"[Chatbot] ✅ Assignment '{cw.get('title', 'Unknown')}' has alternate_link: {alt_link[:50]}...")
        
        print(f"[Chatbot] Found {len(formatted_data)} courses with {len(coursework_list)} coursework items for student")
        
        return {"classroom_data": formatted_data}
        
    except Exception as e:
        print(f"[Chatbot] Error getting student coursework: {e}")
        import traceback
        traceback.print_exc()
        return {"classroom_data": []}

def get_admin_data(user_email: str = None,
                   load_teachers: bool = True,
                   load_students: bool = True, 
                   load_announcements: bool = True,
                   load_coursework: bool = True,
                   load_calendar: bool = True,
                   announcement_date_ranges: list = None,
                   limit_announcements: int = None,
                   limit_students: int = None,
                   limit_teachers: int = None,
                   limit_coursework: int = None) -> dict:
    """Get reference data (Google Classroom/Calendar sync) from Supabase for chatbot responses.
    
    This is REFERENCE DATA used by chatbot for ALL users - not restricted to admins.
    If user_email is provided, tries that user first; otherwise uses any admin with synced data.
    
    Uses normalized tables: google_classroom_courses, google_classroom_teachers, etc.
    
    Args:
        user_email: Email to fetch data for
        load_teachers: Whether to load teacher data (default: True)
        load_students: Whether to load student data (default: True)
        load_announcements: Whether to load announcement data (default: True)
        load_coursework: Whether to load coursework data (default: True)
        load_calendar: Whether to load calendar data (default: True)
        announcement_date_ranges: List of (start_date, end_date) tuples for SQL filtering by date
        limit_announcements: Limit number of announcements per course (SQL LIMIT)
        limit_students: Limit number of students per course (SQL LIMIT)
        limit_teachers: Limit number of teachers per course (SQL LIMIT)
        limit_coursework: Limit number of coursework per course (SQL LIMIT)
    """
    try:
        from supabase_config import get_supabase_client
        from datetime import datetime
        
        supabase = get_supabase_client()
        user_id = None
        
        # If user_email provided, try to get their synced data
        # IMPORTANT: Use user_id (auth.users.id) not id (user_profiles.id) 
        # because google_classroom_courses.user_id references auth.users.id
        if user_email:
            user_profile = supabase.table('user_profiles').select('user_id, id').eq('email', user_email).eq('is_active', True).limit(1).execute()
            if user_profile.data and len(user_profile.data) > 0:
                # Use user_id (auth.users.id) not id (user_profiles.id)
                user_id = user_profile.data[0].get('user_id') or user_profile.data[0].get('id')
                profile_id = user_profile.data[0].get('id')
                print(f"[Chatbot] Getting reference data from user: {user_email} (profile_id: {profile_id}, auth_user_id: {user_id})")
        
        # If no user_email or no data found, find any admin with synced data
        if not user_id:
            # Find any user_id that has synced classroom or calendar data
            classroom_check = supabase.table('google_classroom_courses').select('user_id').limit(1).execute()
            if classroom_check.data and len(classroom_check.data) > 0:
                user_id = classroom_check.data[0]['user_id']
            else:
                # calendar_event_data is global (no user_id), so we just check if it exists
                # but we can't extract user_id from it - this is just to verify table exists
                calendar_check = supabase.table('calendar_event_data').select('id').limit(1).execute()
                # Note: calendar_event_data doesn't have user_id, so we can't use it to find user_id
                # This check just verifies the table has data
            
            if user_id:
                print(f"[Chatbot] Using reference data from user ID: {user_id}")
        
        if not user_id:
            print(f"[Chatbot] No synced data found in Supabase")
            return {"classroom_data": [], "calendar_data": []}
        
        # Get classroom courses from normalized table
        courses_result = supabase.table('google_classroom_courses').select('*').eq('user_id', user_id).execute()
        courses = courses_result.data if courses_result.data else []
        
        print(f"[Chatbot] Found {len(courses)} courses in Supabase")
        
        # Format classroom data with nested relationships (only load what's needed based on query intent)
        formatted_classroom_data = []
        for course in courses:
            course_id = course.get('id')  # UUID of course in our DB
            
            teachers = []
            students = []
            coursework_list = []
            announcements = []
            
            # Only query relationships that are needed (optimize for speed and cost)
            if load_teachers:
                teachers_query = supabase.table('google_classroom_teachers').select('user_id, course_user_id, profile').eq('course_id', course_id)
                if limit_teachers:
                    teachers_query = teachers_query.limit(limit_teachers)
                teachers_result = teachers_query.execute()
                teachers = teachers_result.data if teachers_result.data else []
            
            if load_students:
                students_query = supabase.table('google_classroom_students').select('user_id, course_user_id, profile').eq('course_id', course_id)
                if limit_students:
                    students_query = students_query.limit(limit_students)
                students_result = students_query.execute()
                students = students_result.data if students_result.data else []
            
            if load_coursework:
                coursework_query = supabase.table('google_classroom_coursework').select('coursework_id, title, description, due_date, due_time, state, alternate_link').eq('course_id', course_id).order('due_date', desc=False)
                if limit_coursework:
                    coursework_query = coursework_query.limit(limit_coursework)
                coursework_result = coursework_query.execute()
                coursework_list = coursework_result.data if coursework_result.data else []
            
            if load_announcements:
                # SQL-level filtering for announcements by date range if provided (CRITICAL for token reduction)
                announcements_query = supabase.table('google_classroom_announcements').select('text, update_time, alternate_link').eq('course_id', course_id)
                
                # Filter by date ranges at SQL level (cost optimization - reduces tokens significantly)
                if announcement_date_ranges and len(announcement_date_ranges) > 0:
                    # Find the earliest start time and latest end time to create a bounding date range
                    earliest_start = min(date_start for date_start, date_end in announcement_date_ranges)
                    latest_end = max(date_end for date_start, date_end in announcement_date_ranges)
                    
                    # Filter at SQL level using date range (reduces data fetched dramatically)
                    # Convert datetime to ISO string for Supabase query (ensure UTC timezone format)
                    # Format: 'YYYY-MM-DDTHH:MM:SS+00:00' or 'YYYY-MM-DDTHH:MM:SSZ'
                    if earliest_start.tzinfo:
                        earliest_start_iso = earliest_start.isoformat().replace('+00:00', 'Z')
                    else:
                        earliest_start_iso = earliest_start.isoformat() + 'Z'
                    
                    if latest_end.tzinfo:
                        latest_end_iso = latest_end.isoformat().replace('+00:00', 'Z')
                    else:
                        latest_end_iso = latest_end.isoformat() + 'Z'
                    
                    print(f"[Chatbot] SQL filtering by date range: {earliest_start.date()} to {latest_end.date()} ({earliest_start_iso} to {latest_end_iso})")
                    
                    # SQL-level date filtering: only fetch announcements in the date range
                    # Supabase PostgREST accepts ISO 8601 datetime strings for .gte() and .lte()
                    announcements_query = announcements_query.gte('update_time', earliest_start_iso).lte('update_time', latest_end_iso)
                    announcements_query = announcements_query.order('update_time', desc=True)
                    
                    # Apply limit after SQL filtering (much smaller dataset)
                    if limit_announcements:
                        announcements_query = announcements_query.limit(limit_announcements * 2)  # Get 2x to account for exact date matching
                    else:
                        announcements_query = announcements_query.limit(20)  # Default limit
                else:
                    # No date filtering, just order and limit
                    announcements_query = announcements_query.order('update_time', desc=True)
                    if limit_announcements:
                        announcements_query = announcements_query.limit(limit_announcements)
                    else:
                        announcements_query = announcements_query.limit(10)  # Default limit when no date filter
                
                announcements_result = announcements_query.execute()
                announcements = announcements_result.data if announcements_result.data else []
                print(f"[Chatbot] Fetched {len(announcements)} announcements from SQL (after SQL-level date filtering) for course {course.get('name', '')}")
                
                # Final exact date matching in Python (on much smaller dataset now)
                if announcement_date_ranges and len(announcement_date_ranges) > 0 and announcements:
                    filtered_announcements = []
                    for ann in announcements:
                        update_time_str = ann.get('update_time', '')
                        if update_time_str:
                            try:
                                from datetime import datetime, timezone
                                update_time = datetime.fromisoformat(update_time_str.replace('Z', '+00:00'))
                                if update_time.tzinfo is None:
                                    update_time = update_time.replace(tzinfo=timezone.utc)
                                # Check if announcement is from any of the target dates (exact match)
                                for date_start, date_end in announcement_date_ranges:
                                    if date_start <= update_time <= date_end:
                                        filtered_announcements.append(ann)
                                        break  # Found match, no need to check other dates
                            except Exception as e:
                                print(f"[Chatbot] Error parsing announcement date: {e}")
                                pass
                    announcements = filtered_announcements[:limit_announcements] if limit_announcements else filtered_announcements
                    print(f"[Chatbot] After exact date matching: {len(announcements)} announcements match the requested dates")
                else:
                    # No date filtering, just use what we got
                    if limit_announcements and len(announcements) > limit_announcements:
                        announcements = announcements[:limit_announcements]
            
            # Format students with extracted names (minimal fields only)
            formatted_students = []
            for student in students:
                profile = student.get('profile', {})
                student_name = profile.get('name', {}).get('fullName') or profile.get('emailAddress', '')
                formatted_students.append({
                    "studentId": student.get('user_id', ''),
                    "studentName": student_name,
                    "profile": profile  # Keep profile for email extraction if needed
                })
            
            # Format teachers with extracted names (minimal fields only)
            formatted_teachers = []
            for teacher in teachers:
                profile = teacher.get('profile', {})
                teacher_name = profile.get('name', {}).get('fullName') or profile.get('emailAddress', '')
                formatted_teachers.append({
                    "teacherId": teacher.get('user_id', ''),
                    "teacherName": teacher_name,
                    "profile": profile  # Keep profile for email extraction if needed
                })
            
            # Format coursework (minimal fields - remove description if not needed)
            formatted_coursework = []
            for cw in coursework_list:
                formatted_coursework.append({
                    "courseWorkId": cw.get('coursework_id', ''),
                    "title": cw.get('title', ''),
                    "dueDate": cw.get('due_date', ''),
                    "dueTime": cw.get('due_time', ''),
                    "state": cw.get('state', '')
                    # Removed: description, alternateLink to save tokens
                })
            
            # Format announcements with URL (only essential fields to reduce tokens)
            formatted_announcements = []
            for ann in announcements:
                formatted_announcements.append({
                    "text": ann.get('text', ''),
                    "updateTime": ann.get('update_time', ''),
                    "url": ann.get('alternate_link', '')  # URL to access announcement
                })
            
            # Build minimal course data - only include what's requested
            course_data = {
                "name": course.get('name', ''),  # Always include course name
            }
            
            # Add course link (alternate_link) if available - useful for coursework queries
            if course.get('alternate_link'):
                course_data["course_link"] = course.get('alternate_link')
            
            # Only add nested data if it was loaded (based on query intent)
            if formatted_teachers:
                course_data["teachers"] = formatted_teachers
            if formatted_students:
                course_data["students"] = formatted_students
            if formatted_coursework:
                course_data["coursework"] = formatted_coursework
            if formatted_announcements:
                course_data["announcements"] = formatted_announcements
            
            # Add minimal metadata only if needed
            if course.get('section'):
                course_data["section"] = course.get('section', '')
            formatted_classroom_data.append(course_data)
            
        # Get calendar data (upcoming events) from website calendar page (calendar_event_data table) - only if requested
        formatted_calendar_data = []
        calendar_events = []  # Initialize to empty list
        if load_calendar:
            from datetime import date, datetime, timezone
            today = date.today()
            
            # Fetch from calendar_event_data table (from website calendar page)
            events_result = supabase.table('calendar_event_data').select('*').gte('event_date', today.isoformat()).eq('is_active', True).order('event_date', desc=False).order('event_time', desc=False).limit(20).execute()
            calendar_events = events_result.data if events_result.data else []
            
            print(f"[Chatbot] Found {len(calendar_events)} upcoming calendar events from website calendar")
            
            # Format calendar data to match expected structure
            for event in calendar_events:
                # Combine date and time for start_time
                event_date = event.get('event_date')
                event_time = event.get('event_time')
                start_time = None
                if event_date:
                    if event_time:
                        # Combine date and time
                        start_time = f"{event_date}T{event_time}"
                    else:
                        # Just date, assume start of day
                        start_time = f"{event_date}T00:00:00"
                
                formatted_calendar_data.append({
                        "eventId": str(event.get('id', '')),  # Use database ID
                        "summary": event.get('event_title', ''),
                        "description": event.get('event_description', ''),
                        "startTime": start_time,
                        "endTime": start_time,  # Use same as start if no end time
                        "location": "",  # Not available from website calendar
                        "hangoutLink": "",  # Not available from website calendar
                        "eventType": event.get('event_type', 'upcoming'),  # Add event type
                        "sourceUrl": event.get('source_url', '')  # Add source URL
                    })
        else:
            print(f"[Chatbot] Skipping calendar data (not requested)")
        
        return {
            "classroom_data": formatted_classroom_data,
            "calendar_data": formatted_calendar_data
        }
    except Exception as e:
        print(f"[Chatbot] Error getting reference data from Supabase: {e}")
        import traceback
        traceback.print_exc()
        return {"classroom_data": [], "calendar_data": []}

def detect_query_language(query):
    """
    Detect the language of the user's query
    Returns: 'english', 'hindi', 'gujarati', or 'english' as default
    """
    query_lower = query.lower()

    # Hindi indicators - removed generic substrings that cause false positives
    hindi_words = ['hai', 'kya', 'meri', 'mere', 'aaj', 'kal', 'school', 'event', 'koi', 'mein', 'बजे', 'घंटे']
    hindi_chars = ['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ए', 'ऐ', 'ओ', 'औ', 'अं', 'अः', 'क', 'ख', 'ग', 'घ', 'ङ', 'च', 'छ', 'ज', 'झ', 'ञ', 'ट', 'ठ', 'ड', 'ढ', 'ण', 'त', 'थ', 'द', 'ध', 'न', 'प', 'फ', 'ब', 'भ', 'म', 'य', 'र', 'ल', 'व', 'श', 'ष', 'स', 'ह']

    # Gujarati indicators - removed generic substrings that cause false positives
    gujarati_words = ['che', 'chhe', 'chu', 'shava', 'mari', 'mare', 'aaj', 'kal', 'shala', 'koi', 'athi']
    gujarati_chars = ['અ', 'આ', 'ઇ', 'ઈ', 'ઉ', 'ઊ', 'એ', 'ઐ', 'ઓ', 'ઔ', 'અં', 'અઃ', 'ક', 'ખ', 'ગ', 'ઘ', 'ઙ', 'ચ', 'છ', 'જ', 'ઝ', 'ઞ', 'ટ', 'ઠ', 'ડ', 'ઢ', 'ણ', 'ત', 'થ', 'દ', 'ધ', 'ન', 'પ', 'ફ', 'બ', 'ભ', 'મ', 'ય', 'ર', 'લ', 'વ', 'શ', 'ષ', 'સ', 'હ']

    # Check for Gujarati characters
    if any(char in query for char in gujarati_chars):
        return 'gujarati'

    # Check for Hindi characters
    if any(char in query for char in hindi_chars):
        return 'hindi'

    # Check for Hindi/Gujarati words (using word boundaries for better accuracy)
    hindi_count = sum(1 for word in hindi_words if re.search(r'\b' + re.escape(word) + r'\b', query_lower))
    gujarati_count = sum(1 for word in gujarati_words if re.search(r'\b' + re.escape(word) + r'\b', query_lower))

    # Debug logging
    print(f"[Chatbot] Language detection debug:")
    print(f"  Query: '{query}'")
    print(f"  Hindi words found: {[word for word in hindi_words if word in query_lower]}")
    print(f"  Gujarati words found: {[word for word in gujarati_words if word in query_lower]}")
    print(f"  Hindi count: {hindi_count}, Gujarati count: {gujarati_count}")

    if gujarati_count > hindi_count and gujarati_count > 2:
        return 'gujarati'
    elif hindi_count > 2:
        return 'hindi'

    # Default to English
    return 'english'

def load_holiday_data():
    """
    Load holiday data from g7_infosheet_data.json file
    Returns a dictionary mapping (month, day) tuples to holiday information
    """
    try:
        import os
        import json
        from datetime import datetime

        # Path to the g7 infosheet data
        data_path = os.path.join(os.path.dirname(__file__), '../../g7_infosheet_data.json')

        if not os.path.exists(data_path):
            print("[Holiday] g7_infosheet_data.json not found, using fallback holiday data")
            return get_fallback_holidays()

        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        holidays = {}
        holiday_sheet = data.get('sheet_data', {}).get('Holidays', [])

        if not holiday_sheet:
            print("[Holiday] No 'Holidays' sheet found in data, using fallback")
            return get_fallback_holidays()

        # Parse holiday data from the sheet
        # Skip header rows and process data rows
        for row in holiday_sheet:
            if len(row) >= 4:  # Need at least S.No., Holiday, Date, Day
                try:
                    # Check if this is a data row (has S.No. as number)
                    s_no = row[0].strip() if row[0] else ""
                    if s_no and s_no.isdigit():
                        holiday_name = row[1].strip() if len(row) > 1 and row[1] else ""
                        date_str = row[2].strip() if len(row) > 2 and row[2] else ""
                        day_name = row[3].strip() if len(row) > 3 and row[3] else ""

                        if holiday_name and date_str:
                            # Parse date string like "April 10" or "August 15"
                            try:
                                # Handle different date formats
                                if " " in date_str:
                                    parts = date_str.split(" ")
                                    if len(parts) >= 2:
                                        month_str = parts[0]
                                        day_str = parts[1]

                                        # Convert month name to number
                                        month_names = {
                                            'January': 1, 'February': 2, 'March': 3, 'April': 4,
                                            'May': 5, 'June': 6, 'July': 7, 'August': 8,
                                            'September': 9, 'October': 10, 'November': 11, 'December': 12
                                        }

                                        month = month_names.get(month_str)
                                        if month:
                                            # Extract day number (remove any non-numeric characters)
                                            day_str_clean = ''.join(c for c in day_str if c.isdigit())
                                            if day_str_clean:
                                                day = int(day_str_clean)

                                                holidays[(month, day)] = {
                                                    "name": holiday_name,
                                                    "message": f"Today is {holiday_name}! 🎉",
                                                    "context": f"{holiday_name} is a special holiday. At Prakriti School, we celebrate this day with appropriate activities and respect for the occasion."
                                                }
                            except Exception as e:
                                print(f"[Holiday] Error parsing holiday date '{date_str}': {e}")
                                continue

                except Exception as e:
                    print(f"[Holiday] Error processing holiday row: {e}")
                    continue

        print(f"[Holiday] Loaded {len(holidays)} holidays from g7_infosheet_data.json")
        return holidays

    except Exception as e:
        print(f"[Holiday] Error loading holiday data: {e}")
        return get_fallback_holidays()

def get_fallback_holidays():
    """
    Fallback holiday data when JSON file is not available
    """
    return {
        (12, 25): {
            "name": "Christmas",
            "message": "Today is Christmas Day! 🎄",
            "context": "Christmas is a joyful celebration of love, giving, and togetherness. At Prakriti School, we celebrate the spirit of Christmas through cultural activities, festive decorations, and special assemblies that emphasize the values of kindness and community."
        },
        (1, 26): {
            "name": "Republic Day",
            "message": "Today is Republic Day! 🇮🇳",
            "context": "Republic Day celebrates the adoption of the Constitution of India. At Prakriti School, we commemorate this day with patriotic activities and reflection on our nation's values."
        },
        (8, 15): {
            "name": "Independence Day",
            "message": "Today is Independence Day! 🇮🇳",
            "context": "Independence Day marks India's freedom from colonial rule. At Prakriti School, we celebrate with patriotic fervor and appreciation for our nation's achievements."
        },
        (10, 2): {
            "name": "Mahatma Gandhi's Birthday",
            "message": "Today is Mahatma Gandhi's Birthday! 🇮🇳",
            "context": "We celebrate the birth anniversary of Mahatma Gandhi, the Father of the Nation, remembering his principles of truth, non-violence, and service to humanity."
        }
    }

def detect_holiday_context(date):
    """
    Detect if today is a special holiday or celebration day
    Returns contextual information for the AI to use in responses
    Uses holiday data from g7_infosheet_data.json file
    """
    month, day = date.month, date.day

    # Load holidays from JSON file (cached for performance)
    if not hasattr(detect_holiday_context, '_holidays_cache'):
        detect_holiday_context._holidays_cache = load_holiday_data()

    holidays = detect_holiday_context._holidays_cache

    if (month, day) in holidays:
        return holidays[(month, day)]

    return None

def generate_chatbot_response(request):
    """
    Use OpenAI GPT-4 to generate a chatbot response with RAG logic and fuzzy matching.
    """
    # 🔍 MODEL LOGGING FOR CHATBOT RESPONSE GENERATION
    import re  # For post-processing regex patterns
    selected_model = get_default_gpt_model()
    print(f"[ChatbotResponse] 🔍 MODEL SELECTION: Using {selected_model.upper()} for comprehensive chatbot response generation")
    print(f"[ChatbotResponse] 🤖 AI MODEL: {selected_model} (Default: GPT-4o-mini, Fallback: GPT-3.5-turbo)")
    print(f"[ChatbotResponse] 📝 QUERY: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")

    # 🎄 EARLY HOLIDAY DETECTION - Check if today is a holiday for all responses
    from datetime import datetime, timezone, timedelta
    today_date = datetime.now(timezone.utc).date()
    global_holiday_context = detect_holiday_context(today_date)
    yesterday_date = today_date - timedelta(days=1)
    yesterday_holiday_context = detect_holiday_context(yesterday_date)

    if global_holiday_context:
        print(f"[ChatbotResponse] 🎄 HOLIDAY DETECTED: {global_holiday_context['message']}")
    if yesterday_holiday_context:
        print(f"[ChatbotResponse] 🎄 HOLIDAY DETECTED for yesterday: {yesterday_holiday_context['message']}")

    # Capture re module at function start to avoid closure issues in generator expressions
    re_module = re
    openai_client = get_openai_client()
    user_query = request.message
    conversation_history = getattr(request, 'conversation_history', []) or []  # Ensure it's never None
    user_profile = getattr(request, 'user_profile', None)

    # Profile includes embedding for semantic personalization
    # Basic fields (first_name, role, grade) used for greetings and basic personalization
    # Embedding provides additional semantic context for more personalized responses

    # Step 0.1: Handle empty queries - treat them as greetings so they get proper handling
    query_stripped = user_query.strip() if user_query else ""
    
    # Check conversation history for homework context if query is empty
    homework_context_in_history = False
    if not query_stripped and conversation_history:
        # Check last few messages for homework-related keywords
        recent_messages = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
        for msg in recent_messages:
            msg_content = msg.get('content', '').lower() if isinstance(msg, dict) else str(msg).lower()
            if any(kw in msg_content for kw in ['homework', 'help', 'assignment', 'solve', 'question', 'problem']):
                homework_context_in_history = True
                break
    
    # If query is completely empty, handle appropriately
    if not query_stripped:
        # If there's homework context in history and user is guest, prompt to connect
        if homework_context_in_history and not user_profile:
            return """Hello! I noticed you're asking about homework help. To provide you with the most relevant assistance, I need access to your assignments and coursework.

**To get personalized homework help:**

**Step 1: Sign In**
- Click on the profile icon in the top right corner
- Select "Sign In" or "Log In"
- Use your Google account to authenticate

**Step 2: Connect Google Classroom**
- After signing in, click on your profile icon again
- Go to "Profile Settings" or "Edit Profile"
- Click on "Connect Google Classroom" button
- Authorize the connection with your Google account

**Step 3: Sync Your Data**
- Once connected, click "Sync Classroom Data" to load your courses, assignments, and announcements

After connecting, I'll be able to help you with your specific assignments and provide subject-specific guidance!"""
        
        # If there's homework context and logged-in user, ask for subject/topic
        elif homework_context_in_history and user_profile:
            first_name = user_profile.get('first_name', '') or ''
            capitalized_first_name = first_name.capitalize() if first_name else ''
            return f"""Hi {capitalized_first_name}! I'd be happy to help you with your homework!

To provide you with the most accurate and helpful answer, could you please tell me:

1. **Which subject** are you working on? (e.g., Mathematics, Science, English, History, etc.)
2. **What specific topic or problem** do you need help with?

For example:
- "Help me with math - solving quadratic equations"
- "I need help with science - photosynthesis"
- "Can you explain the water cycle in geography?"

Once you provide the subject and topic, I'll be able to give you detailed, step-by-step explanations!"""
        
        # Otherwise, treat as greeting and let it proceed to greeting handler
        pass  # Continue to greeting handler
    elif len(query_stripped) < 3:
        # Very short query (1-2 chars) - check if it's a greeting
        greeting_patterns_quick = [
            r'\bhi\b', r'\bhello\b', r'\bhey\b', 
            r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b', 
            r'\bgreetings\b'
        ]
        is_likely_greeting = any(re_module.search(pattern, query_stripped.lower()) for pattern in greeting_patterns_quick)
        
        # If it's not a greeting, treat very short queries as needing more input
        if not is_likely_greeting:
            # Very short non-greeting - let it proceed to LLM for natural handling
            pass  # Continue to normal processing
    
    # Step 0.2: Check if user is asking about classroom/homework/assignments FIRST (before generic check)
    # This ensures queries like "help with homework" are caught here and show connection steps
    query_lower = user_query.lower()
    
    # Expanded keywords to catch queries like "help with homework", "I need help with my homework", etc.
    is_coursework_query_early = any(kw in query_lower for kw in [
        'assignment', 'homework', 'coursework', 'task', 'due', 'submit',
        'my assignments', 'my coursework', 'my classes', 'my courses', 'my homework',
        'help with homework', 'help with assignment', 'help with coursework',
        'need help with homework', 'need help with assignment',
        'homework help', 'assignment help', 'coursework help'
    ])
    is_classroom_related_query_early = any(kw in query_lower for kw in [
        'assignment', 'homework', 'coursework', 'task', 'due', 'submit', 
        'announcement', 'announce', 'notice', 'update',
        'student', 'classmate', 'roster',
        'teacher', 'instructor', 'faculty',
        'course', 'class', 'subject',
        'event', 'events', 'calendar', 'schedule',
        'my assignments', 'my coursework', 'my classes', 'my courses', 'my homework',
        'help with homework', 'help with assignment', 'help with coursework',
        'need help with homework', 'need help with assignment',
        'homework help', 'assignment help', 'coursework help'
    ])
    is_home_related_query_early = any(kw in query_lower for kw in [
        'home', 'homework', 'my assignments', 'my coursework', 'my classes', 'my courses',
        'help with homework', 'help with assignment'
    ])
    
    # For guest users: Tell them to login first
    if not user_profile and (is_classroom_related_query_early or is_home_related_query_early):
        print(f"[Chatbot] 🚫 Guest user asking about classroom/home - returning early (user needs to login first)")
        return """To access your assignments, homework, and coursework information, please follow these steps:

**Step 1: Sign In**
- Click on the profile icon in the top right corner
- Select "Sign In" or "Log In"
- Use your Google account to authenticate

**Step 2: Connect Google Classroom**
- After signing in, click on your profile icon again
- Go to "Profile Settings" or "Edit Profile"
- Click on "Connect Google Classroom" button
- Authorize the connection with your Google account

**Step 3: Sync Your Data**
- Once connected, click "Sync Classroom Data" to load your courses, assignments, and announcements

After completing these steps, I'll be able to help you with all your coursework-related questions!"""
    
    # For logged-in users: Check if they have Google Classroom connected
    if user_profile and (is_coursework_query_early or is_home_related_query_early):
        user_id = user_profile.get('user_id') or user_profile.get('id')  # Try both possible keys
        if user_id:
            try:
                from supabase_config import get_supabase_client
                supabase = get_supabase_client()
                
                # Check if user has any courses synced (indicates Google Classroom is connected)
                courses_check = supabase.table('google_classroom_courses').select('id').eq('user_id', user_id).limit(1).execute()
                has_classroom_connected = courses_check.data and len(courses_check.data) > 0
                
                if not has_classroom_connected:
                    print(f"[Chatbot] 🚫 Logged-in user asking about coursework/homework but no Google Classroom connection found")
                    first_name = user_profile.get('first_name', '') or ''
                    capitalized_first_name = first_name.capitalize() if first_name else ''
                    return f"""Hi {capitalized_first_name}! To access your assignments, homework, and coursework information, please connect your Google Classroom account. Here's how:

**Step 1: Access Profile Settings**
- Click on your profile icon in the top right corner
- Select "Profile Settings" or "Edit Profile"

**Step 2: Connect Google Classroom**
- Look for the "Connect Google Classroom" button in your profile settings
- Click on it and authorize the connection with your Google account

**Step 3: Sync Your Data**
- After connecting, click "Sync Classroom Data" to load your courses, assignments, and announcements

Once you've completed these steps, I'll be able to help you with all your coursework-related questions!"""
            except Exception as e:
                print(f"[Chatbot] ⚠️ Error checking Google Classroom connection: {e}")
                # Continue anyway - don't block the user if there's an error checking
    
    # Step 0: Check if this is a greeting and provide role-specific greeting (PRIORITY)
    greeting_patterns = [
        r'\bhi\b', r'\bhello\b', r'\bhey\b', 
        r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b', 
        r'\bgreetings\b'
    ]
    is_greeting = any(re_module.search(pattern, user_query.lower()) for pattern in greeting_patterns)
    
    # Check for "how are you" type questions
    how_are_you_keywords = ['how are you', 'how are you doing', 'how do you do', 'how\'s it going', 'how\'s everything']
    is_how_are_you = any(keyword in user_query.lower() for keyword in how_are_you_keywords)
    
    
    if is_greeting and user_profile:

        role = user_profile.get('role', '') or ''
        first_name = user_profile.get('first_name', '') or ''
        gender = user_profile.get('gender', '') or ''
        
        # Convert to lowercase safely
        role = role.lower() if role else ''
        gender = gender.lower() if gender else ''
        
        # Determine appropriate title based on gender and role
        # Only use titles for teachers and parents, not students
        if role in ['teacher', 'parent']:
            if gender == 'male':
                title = 'Sir'
            elif gender == 'female':
                title = 'Madam'
            else:
                title = ''  # No title for 'other' or 'prefer_not_to_say'
        else:
            title = ''  # No title for students regardless of gender
        
        # Format greeting with appropriate title and capitalize first name
        capitalized_first_name = first_name.capitalize() if first_name else first_name
        greeting_prefix = f"Hello {capitalized_first_name}{f' {title}' if title else ''}!"
        
        # Check if this is the first greeting (conversation history <= 1)
        is_first_greeting = len(conversation_history) <= 1
        
        if role == 'student':
            if is_first_greeting:
                grade = user_profile.get('grade', '')
                subjects = user_profile.get('subjects', [])
                return f"{greeting_prefix} Welcome to Prakriti School's AI assistant! I'm here to help you with your studies, answer questions about our school, and support your learning journey. I see you're in {grade} and studying {', '.join(subjects) if subjects else 'various subjects'}. How can I assist you today? Remember, at Prakriti, we believe in 'learning for happiness' - so let's make your learning experience joyful and meaningful!"
            else:
                return f"{greeting_prefix} How can I help you with your studies today?"
        
        elif role == 'teacher':
            if is_first_greeting:
                department = user_profile.get('department', '')
                subjects_taught = user_profile.get('subjects_taught', [])
                return f"{greeting_prefix} Welcome to Prakriti School's AI assistant for educators! I'm here to support you in your teaching journey at Prakriti. I see you're in the {department} department, teaching {', '.join(subjects_taught) if subjects_taught else 'various subjects'}. How can I help you with curriculum planning, teaching strategies, or any questions about our progressive educational approach? Let's work together to create amazing learning experiences for our students!"
            else:
                return f"{greeting_prefix} How can I assist you with your teaching today?"
        
        elif role == 'parent':
            if is_first_greeting:
                relationship = user_profile.get('relationship_to_student', '')
                return f"{greeting_prefix} Welcome to Prakriti School's AI assistant for parents! I'm here to help you understand our school's approach and support your child's educational journey. As a {relationship.lower() if relationship else 'parent'}, you play a crucial role in your child's development. How can I assist you today? Whether you have questions about our curriculum, activities, or how to support your child's learning at home, I'm here to help!"
            else:
                return f"{greeting_prefix} How can I help you with your child's education today?"
        
        else:
            if is_first_greeting:
                return f"{greeting_prefix} Welcome to Prakriti School's AI assistant! I'm here to help you learn about our unique educational philosophy and programs. How can I assist you today?"
            else:
                return f"{greeting_prefix} How can I help you today?"

    # Handle greetings for guest users (no personalization)
    if is_greeting and not user_profile:
        return "Hello! Welcome to Prakriti School's AI assistant. I'm here to help you learn about our unique educational philosophy and programs. How can I assist you today?"
    
    # Handle empty queries that didn't match homework context - return greeting
    if not query_stripped:
        if not user_profile:
            return "Hello! Welcome to Prakriti School's AI assistant. I'm here to help you learn about our unique educational philosophy and programs. How can I assist you today?"
        else:
            first_name = user_profile.get('first_name', '') or ''
            capitalized_first_name = first_name.capitalize() if first_name else ''
            return f"Hello {capitalized_first_name}! How can I help you today?"

    # Step 0.25: Built-in responses for common queries (to reduce API costs)
    
    # Check for concept explanation queries
    concept_explanation_keywords = ['explain a concept', 'explain concept', 'explain in simple terms', 'simple terms', 'clear understanding', 'explain with examples', 'concept explanation']
    concept_explanation_patterns = [
        r'\bexplain\s+a\s+concept\b',
        r'\bexplain\s+concept\b',
        r'\bexplain\s+.*\s+in\s+simple\s+terms\b',
        r'\bexplain\s+.*\s+with\s+examples\b',
        r'\b(?:can\s+you|could\s+you|please).*explain\s+.*\s+concept\b',
        r'\b(?:can\s+you|could\s+you|please).*explain\s+.*\s+simple\s+terms\b',
        r'\b(?:can\s+you|could\s+you|please).*explain\s+.*\s+clear\s+understanding\b',
        r'\b(?:can\s+you|could\s+you|please).*explain\s+.*\s+examples\b',
        r'\bclear\s+understanding\b',
        r'\b(?:looking\s+for|i\'m\s+looking\s+for).*clear\s+understanding\b',
    ]
    is_concept_explanation_query = any(kw in query_lower for kw in concept_explanation_keywords) or any(re_module.search(pattern, query_lower) for pattern in concept_explanation_patterns)
    
    if is_concept_explanation_query:
        print(f"[Chatbot] 📖 Concept explanation query detected - using built-in response (no API call)")
        return """Of course! I'd be happy to help. Please let me know which concept you would like me to explain, along with any specific details or examples you are interested in."""
    
    # Check for IGCSE curriculum queries
    igcse_keywords = ['igcse', 'international general certificate', 'secondary education', 'igcse curriculum', 'igcse program']
    igcse_query_patterns = [
        r'\bigcse\b',
        r'\b(?:explain|tell|about|what|information|details).*igcse',
        r'\bigcse.*(?:curriculum|program|course|benefits|advantages)',
        r'\b(?:curriculum|program|course).*igcse',
    ]
    is_igcse_query = any(kw in query_lower for kw in igcse_keywords) or any(re_module.search(pattern, query_lower) for pattern in igcse_query_patterns)
    
    if is_igcse_query:
        print(f"[Chatbot] 📚 IGCSE curriculum query detected - using built-in response (no API call)")
        return """The IGCSE (International General Certificate of Secondary Education) curriculum offered at Prakriti School is a globally recognized program that provides students with a broad and balanced education. This curriculum is designed to develop students' critical thinking, problem-solving, and communication skills.

**Benefits of the IGCSE curriculum at Prakriti School include:**

**Internationally Recognized Qualification:** IGCSE is widely accepted by universities and employers around the world, providing students with opportunities for higher education and career advancement.

**Holistic Development:** The curriculum focuses on developing students academically, socially, and emotionally, preparing them for the challenges of the modern world.

**Flexibility:** IGCSE offers a wide range of subjects, allowing students to tailor their education to their interests and career goals.

**Emphasis on Practical Skills:** The curriculum includes practical assessments and real-world applications, helping students develop skills that are relevant in today's job market.

**Preparation for Further Education:** IGCSE prepares students for advanced study in subjects such as A-levels, IB Diploma, or other post-secondary programs.

Overall, the IGCSE curriculum at Prakriti School aims to provide students with a well-rounded education that equips them with the knowledge, skills, and attitudes needed to succeed in the 21st century."""
    
    # Check for study tips queries
    study_tips_keywords = ['study tips', 'study techniques', 'study methods', 'how to study', 'effective study', 'study better', 'learning techniques', 'study strategies', 'study help', 'improve study']
    study_tips_patterns = [
        r'\bstudy\s+tips\b',
        r'\bstudy\s+techniques?\b',
        r'\bstudy\s+methods?\b',
        r'\bhow\s+to\s+study\b',
        r'\beffective\s+study\b',
        r'\bstudy\s+better\b',
        r'\blearning\s+techniques?\b',
        r'\bstudy\s+strateg(?:ies|y)\b',
        r'\b(?:what|tell|give|share|provide).*study\s+tips',
        r'\b(?:what|tell|give|share|provide).*effective\s+study',
        r'\b(?:how|what).*learn\s+better',
        r'\b(?:how|what).*study\s+effectively',
    ]
    is_study_tips_query = any(kw in query_lower for kw in study_tips_keywords) or any(re_module.search(pattern, query_lower) for pattern in study_tips_patterns)
    
    if is_study_tips_query:
        print(f"[Chatbot] 📖 Study tips query detected - using built-in response (no API call)")
        return """Here are some effective study tips and techniques that can help you learn better:

**1. Create a study schedule**: Plan your study time and allocate specific time slots for each subject or topic. This will help you stay organized and focused.

**2. Set specific goals**: Break down your study material into smaller goals and set achievable targets. This will make your study sessions more manageable and rewarding.

**3. Use active learning techniques**: Instead of passively reading or listening, engage with the material actively. This can include summarizing, teaching someone else, or solving practice problems.

**4. Take regular breaks**: Studies have shown that taking short breaks during study sessions can improve focus and retention. Try the Pomodoro technique - study for 25 minutes, then take a 5-minute break.

**5. Stay organized**: Keep your study space clutter-free and organized. Use tools like folders, color-coded notes, or digital apps to keep track of your study material.

**6. Practice self-testing**: Quiz yourself regularly to reinforce learning and identify areas that need more focus. Flashcards, practice quizzes, and past papers can be helpful for self-testing.

**7. Stay hydrated and get enough sleep**: A well-rested and hydrated brain functions better. Make sure to drink water and get enough sleep to support your learning and memory.

**8. Stay motivated**: Find ways to stay motivated, whether it's setting rewards for achieving study goals, studying with a group, or visualizing your success.

Remember, everyone has different learning styles, so it's important to experiment with these techniques and find what works best for you. If you need personalized study help or have specific questions, feel free to ask!"""

    # Check for math problems queries
    math_problems_keywords = ['math problems', 'mathematics problems', 'solve math', 'math help', 'math solutions', 'math explanations', 'help solving', 'solving problems', 'math questions']
    math_problems_patterns = [
        r'\bmath\s+problems?\b',
        r'\bmathematics\s+problems?\b',
        r'\b(?:I\s+have|I\'ve\s+got|I\s+got)\s+math\s+problems?\b',
        r'\b(?:help|solve|assistance).*math\s+problems?\b',
        r'\bmath\s+problems?.*(?:help|solve|assistance|solutions?|explanations?)\b',
        r'\b(?:can\s+you|could\s+you|please).*help.*math\s+problems?\b',
        r'\b(?:can\s+you|could\s+you|please).*solve.*math\s+problems?\b',
        r'\b(?:can\s+you|could\s+you|please).*provide.*solutions?.*explanations?\b',
        r'\b(?:I\s+have|I\'ve\s+got|I\s+got).*math\s+problems?.*(?:help|solve|assistance|solutions?|explanations?)\b',
        r'\bmath\s+problems?.*(?:need|want|require).*help\s+solving\b',
        r'\b(?:need|want|require).*help\s+solving.*math\s+problems?\b',
    ]
    is_math_problems_query = any(kw in query_lower for kw in math_problems_keywords) or any(re_module.search(pattern, query_lower) for pattern in math_problems_patterns)
    
    if is_math_problems_query:
        print(f"[Chatbot] 🔢 Math problems query detected - using built-in response (no API call)")
        return """Of course! I'd be happy to help. Please go ahead and share the math problems you need assistance with."""

    # Check for science questions queries
    science_questions_keywords = ['science questions', 'scientific explanations', 'science help', 'science answers', 'science problems', 'science queries', 'scientific questions', 'detailed scientific', 'scientific explanations']
    science_questions_patterns = [
        r'\bscience\s+questions?\b',
        r'\bscientific\s+questions?\b',
        r'\b(?:I\s+have|I\'ve\s+got|I\s+got)\s+science\s+questions?\b',
        r'\b(?:help|answer|explain|assistance).*science\s+questions?\b',
        r'\bscience\s+questions?.*(?:need|want|require).*answering\b',
        r'\bscience\s+questions?.*(?:need|want|require).*detailed\s+scientific\s+explanations?\b',
        r'\b(?:can\s+you|could\s+you|please).*help.*science\s+questions?\b',
        r'\b(?:can\s+you|could\s+you|please).*answer.*science\s+questions?\b',
        r'\b(?:can\s+you|could\s+you|please).*provide.*detailed\s+scientific\s+explanations?\b',
        r'\b(?:I\s+have|I\'ve\s+got|I\s+got).*science\s+questions?.*(?:need|want|require).*answering\b',
        r'\b(?:I\s+have|I\'ve\s+got|I\s+got).*science\s+questions?.*detailed\s+scientific\s+explanations?\b',
        r'\bdetailed\s+scientific\s+explanations?\b',
        r'\bscientific\s+explanations?.*(?:need|want|require|provide)\b',
    ]
    is_science_questions_query = any(kw in query_lower for kw in science_questions_keywords) or any(re_module.search(pattern, query_lower) for pattern in science_questions_patterns)
    
    if is_science_questions_query:
        print(f"[Chatbot] 🔬 Science questions query detected - using built-in response (no API call)")
        return """I can help with your science questions. Please go ahead and ask your first question."""

    # Check for "learning for happiness" philosophy queries
    # More specific keywords to avoid false positives
    happiness_philosophy_keywords = ['learning for happiness', 'happiness philosophy', 'prakriti philosophy', 'school philosophy', 'educational philosophy']
    happiness_philosophy_patterns = [
        r'\blearning\s+for\s+happiness\b',
        r'\bhappiness\s+philosophy\b',
        r'\b(?:how|what|explain|tell|about).*learning\s+for\s+happiness',
        r'\b(?:how|what|explain|tell|about).*happiness.*philosophy',
        r'\b(?:prakriti|school).*philosophy.*(?:work|practice|implement|how)',
        r'\bphilosophy.*(?:prakriti|school).*(?:work|practice|implement|how)',
        r'\b(?:how|what).*prakriti.*philosophy',
        r'\b(?:how|what).*school.*philosophy',
    ]
    is_happiness_philosophy_query = any(kw in query_lower for kw in happiness_philosophy_keywords) or any(re_module.search(pattern, query_lower) for pattern in happiness_philosophy_patterns)
    
    if is_happiness_philosophy_query:
        print(f"[Chatbot] 🌟 Learning for happiness philosophy query detected - using built-in response (no API call)")
        return """Prakriti School's "learning for happiness" philosophy is implemented in various ways to ensure a holistic and fulfilling educational experience for students:

**Holistic Curriculum:** The school offers a well-rounded curriculum that focuses not only on academic excellence but also on the overall development of students. This includes a balance of academics, arts, sports, and life skills education.

**Emphasis on Well-being:** Prakriti School prioritizes the well-being of students and staff members. Various initiatives are in place to promote mental health, emotional well-being, and a positive school environment.

**Student-Centric Approach:** The school follows a student-centric approach where the individual needs, interests, and strengths of each student are recognized and nurtured. This helps in fostering a sense of purpose and fulfillment among students.

**Life Skills Education:** Along with traditional subjects, students are also taught essential life skills such as critical thinking, problem-solving, communication, and collaboration. These skills are crucial for personal growth and happiness.

**Community Engagement:** Prakriti School actively involves parents, teachers, and the community in the learning process. This collaborative approach creates a supportive network for students and enhances their overall well-being.

By incorporating these elements into its educational framework, Prakriti School ensures that students not only excel academically but also develop a sense of happiness, purpose, and fulfillment in their learning journey."""

    # Step 0.3: Detect generic homework/study help queries and handle them appropriately
    # CRITICAL: Only detect ACTUAL homework/assignment queries, not general educational queries
    # Check for specific homework/assignment context keywords
    homework_specific_keywords = [
        'homework', 'assignment', 'due', 'deadline', 'submit', 'turn in',
        'my homework', 'my assignment', 'homework help', 'assignment help',
        'coursework', 'classwork', 'project due', 'essay due'
    ]
    has_homework_keyword = any(kw in query_lower for kw in homework_specific_keywords)
    
    # Check for patterns that indicate homework/assignment context
    homework_context_patterns = [
        r'\b(?:my|this|that)\s+(?:homework|assignment|project|essay)\b',
        r'\bhelp\s+with\s+(?:my|this|that)\s+(?:homework|assignment)\b',
        r'\b(?:homework|assignment)\s+(?:help|due|deadline)\b',
        r'\bI\s+need\s+help\s+with\s+(?:my|this|that)\s+(?:homework|assignment)\b',
    ]
    has_homework_context = any(re_module.search(pattern, query_lower) for pattern in homework_context_patterns)
    
    # Check if it's a generic "help with homework" request (without specific subject/topic)
    generic_homework_patterns = [
        r'\bhelp\s+(?:me\s+)?with\s+(?:my\s+)?homework\b',
        r'\bI\s+need\s+help\s+(?:with\s+)?(?:my\s+)?homework\b',
        r'\bcan\s+you\s+help\s+(?:me\s+)?with\s+(?:my\s+)?homework\b',
        r'\bhelp\s+(?:me\s+)?with\s+(?:my\s+)?assignment\b',
    ]
    is_generic_homework_request = any(re_module.search(pattern, query_lower) for pattern in generic_homework_patterns)
    
    # Only consider it a homework query if it has homework-specific keywords or context
    is_homework_help_query = has_homework_keyword or has_homework_context or is_generic_homework_request
    
    # Check if subject/topic is mentioned in the query
    subject_keywords = ['math', 'mathematics', 'science', 'english', 'history', 'physics', 'chemistry', 
                       'biology', 'geography', 'computer', 'programming', 'art', 'music', 'drama',
                       'literature', 'algebra', 'geometry', 'calculus', 'grammar', 'writing']
    topic_indicators = ['chapter', 'lesson', 'topic', 'concept', 'formula', 'theorem', 'theory']
    has_subject = any(kw in query_lower for kw in subject_keywords)
    has_topic = any(kw in query_lower for kw in topic_indicators)
    
    # For guest users asking for ACTUAL homework help (not general educational queries)
    if not user_profile and is_homework_help_query:
        print(f"[Chatbot] 🚫 Guest user asking for homework help - prompting to connect Google Classroom")
        return """Hello! I'd love to help you with your homework and studies! To provide you with the most relevant assistance, I need access to your assignments and coursework.

**To get personalized homework help:**

**Step 1: Sign In**
- Click on the profile icon in the top right corner
- Select "Sign In" or "Log In"
- Use your Google account to authenticate

**Step 2: Connect Google Classroom**
- After signing in, click on your profile icon again
- Go to "Profile Settings" or "Edit Profile"
- Click on "Connect Google Classroom" button
- Authorize the connection with your Google account

**Step 3: Sync Your Data**
- Once connected, click "Sync Classroom Data" to load your courses, assignments, and announcements

After connecting, I'll be able to:
- Help you with your specific assignments
- Provide subject-specific guidance
- Answer questions about your coursework
- Track your progress and deadlines

**Note:** If you have a specific question about a subject (like math, science, etc.), feel free to ask me directly! I can still help with general academic questions."""
    
    # For logged-in users asking generic homework help without subject/topic
    if user_profile and is_generic_homework_request and not (has_subject or has_topic):
        print(f"[Chatbot] 📝 User asking for generic homework help - requesting subject/topic information")
        first_name = user_profile.get('first_name', '') or ''
        capitalized_first_name = first_name.capitalize() if first_name else ''
        role = user_profile.get('role', '').lower() if user_profile.get('role') else ''
        
        if role == 'student':
            grade = user_profile.get('grade', '')
            subjects = user_profile.get('subjects', [])
            subjects_text = f" I see you're in {grade} and studying {', '.join(subjects) if subjects else 'various subjects'}." if grade else ""
            return f"""Hi {capitalized_first_name}! I'd be happy to help you with your homework!{subjects_text}

To provide you with the most accurate and helpful answer, could you please tell me:

1. **Which subject** are you working on? (e.g., Mathematics, Science, English, History, etc.)
2. **What specific topic or problem** do you need help with?

For example, you could say:
- "Help me with math - solving quadratic equations"
- "I need help with science - photosynthesis"
- "Can you explain the water cycle in geography?"

Once you provide the subject and topic, I'll be able to give you detailed, step-by-step explanations!"""
        else:
            return f"""Hi {capitalized_first_name}! I'd be happy to help with homework!

To provide you with the most accurate answer, could you please tell me:

1. **Which subject** do you need help with? (e.g., Mathematics, Science, English, History, etc.)
2. **What specific topic or problem** are you working on?

Once you provide the subject and topic, I'll be able to give you detailed assistance!"""

    # Step 0.5: Handle "how are you" type questions with friendly responses
    if is_how_are_you and user_profile:
        role = user_profile.get('role', '') or ''
        first_name = user_profile.get('first_name', '') or ''
        gender = user_profile.get('gender', '') or ''
        
        # Convert to lowercase safely
        role = role.lower() if role else ''
        gender = gender.lower() if gender else ''
        
        # Determine appropriate title based on gender and role
        if role in ['teacher', 'parent']:
            if gender == 'male':
                title = 'Sir'
            elif gender == 'female':
                title = 'Madam'
            else:
                title = ''
        else:
            title = ''
        
        title_text = f' {title}' if title else ''
        capitalized_first_name = first_name.capitalize() if first_name else first_name
        
        if role == 'teacher':
            return f"I'm doing wonderfully, thank you for asking! I'm energized and ready to help you with your teaching at Prakriti School. How can I assist you today, {capitalized_first_name}{title_text}?"
        elif role == 'parent':
            return f"I'm doing great, thank you! I'm here and excited to help you support your child's education at Prakriti School. How can I assist you today, {capitalized_first_name}{title_text}?"
        elif role == 'student':
            return f"I'm doing fantastic, thank you for asking! I'm here and ready to help you with your studies and learning journey at Prakriti School. How can I assist you today, {capitalized_first_name}?"
        else:
            return f"I'm doing great, thank you! I'm here and ready to help you learn about Prakriti School. How can I assist you today, {capitalized_first_name}?"

    # Step 1: Intent detection for holiday calendar
    holiday_keywords = [
        'holiday calendar', 'school holidays', 'vacation calendar', 'holidays', 'school calendar', 'show holidays', 'holiday list', 'calendar of holidays'
    ]
    if any(kw in user_query.lower() for kw in holiday_keywords):
        return {
            'type': 'calendar',
            'url': 'https://calendar.google.com/calendar/embed?src=Y185MWZiZDlkMjE4ZTQ5YzZjY2RhNGEyOTg3ZWI0ZDJkYjcyYTJmYTBlN2JiMTkzYWY2N2U4NjlhY2NiYmRiZWQ3QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20&ctz=Asia/Kolkata'
        }

    # Step 0.5: Intent-based Q&A for "What kind of school is Prakriti?"
    school_type_intents = [
        'what kind of school is prakriti',
        'what type of school is prakriti',
        'what is prakriti school',
        'describe prakriti school',
        'tell me about prakriti',
        'prakriti school description',
        'is prakriti a progressive school',
        'is prakriti an alternative school',
        'what grades does prakriti have',
        'what makes prakriti different',
        'what is special about prakriti school',
        'prakriti school overview',
        'prakriti k12 school',
        'what does prakriti focus on',
        'what is the philosophy of prakriti school',
    ]
    if any(kw in user_query.lower() for kw in school_type_intents):
        print(f"[Chatbot] ✅ Matched Step 0.5 intent handler: 'tell me about prakriti' - returning early (skipping web crawler)")
        canonical_answer = (
            'Prakriti is an alternative/progressive K–12 school in Noida/Greater Noida focusing on "learning for happiness" through deep experiential education.'
        )
        prompt = (
            f"A user asked about the type of school Prakriti is. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = openai_client.chat.completions.create(
            model=get_default_gpt_model(),
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.6: Intent-based Q&A for "What's the teaching philosophy at Prakriti?"
    teaching_philosophy_intents = [
        "what's the teaching philosophy at prakriti",
        "what is prakriti's teaching philosophy",
        "how does prakriti teach",
        "what is the teaching style at prakriti",
        "prakriti school teaching approach",
        "prakriti education philosophy",
        "how are students taught at prakriti",
        "what is the learning model at prakriti",
        "what is prakriti's approach to education",
        "what is the classroom environment at prakriti",
        "prakriti's learning philosophy",
        "what is the focus of teaching at prakriti",
        "prakriti school philosophy",
    ]
    if any(kw in user_query.lower() for kw in teaching_philosophy_intents):
        print(f"[Chatbot] ✅ Matched Step 0.6 intent handler: 'teaching philosophy' - returning early (skipping web crawler)")
        canonical_answer = (
            'The school follows a compassionate, learner-centric model based on reconnecting with inner nature ("prakriti"), promoting joy, self-expression, and holistic development.'
        )
        prompt = (
            f"A user asked about the teaching philosophy at Prakriti. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = openai_client.chat.completions.create(
            model=get_default_gpt_model(),
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.7: Intent-based Q&A for "Which subjects are available for IGCSE and AS/A Level?"
    igcse_subjects_intents = [
        "which subjects are available for igcse and as/a level",
        "igcse subjects",
        "as level subjects",
        "a level subjects",
        "subjects offered igcse",
        "subjects offered as level",
        "subjects offered a level",
        "prakriti igcse subjects",
        "prakriti as level subjects",
        "prakriti a level subjects",
        "what can i study at prakriti",
        "what are the options for igcse",
        "what are the options for a level",
        "what are the options for as level",
        "prakriti subject list",
        "prakriti subject options",
        "subjects for grade 9",
        "subjects for grade 10",
        "subjects for grade 11",
        "subjects for grade 12",
    ]
    if any(kw in user_query.lower() for kw in igcse_subjects_intents):
        canonical_answer = (
            'IGCSE (Grades 9–10) covers core subjects. For AS/A Level (Grades 11–12), available subjects include Design & Tech, History, Computer Science, Enterprise, Art & Design, Physics, Chemistry, Biology, Combined Sciences, English First & Second Language, French, and Math.'
        )
        prompt = (
            f"A user asked about the subjects available for IGCSE and AS/A Level. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = openai_client.chat.completions.create(
            model=get_default_gpt_model(),
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.8: Intent-based Q&A for "How are learners with special needs supported?"
    special_needs_intents = [
        "how are learners with special needs supported",
        "special needs support",
        "prakriti special needs",
        "bridge programme",
        "support for special needs",
        "inclusive education prakriti",
        "special educators prakriti",
        "therapists prakriti",
        "parent support prakriti",
        "how does prakriti help special needs",
        "prakriti inclusion",
        "prakriti support for disabilities",
        "prakriti learning support",
        "prakriti therapy",
        "prakriti special education",
    ]
    if any(kw in user_query.lower() for kw in special_needs_intents):
        canonical_answer = (
            'Prakriti runs a Bridge Programme with an inclusive curriculum. Children with diverse needs learn together. Special educators, therapists, and parent support systems are in place.'
        )
        prompt = (
            f"A user asked about support for learners with special needs. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = openai_client.chat.completions.create(
            model=get_default_gpt_model(),
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.9: Intent-based Q&A for "What sports, arts, and enrichment activities are available?"
    enrichment_activities_intents = [
        "what sports, arts, and enrichment activities are available",
        "sports at prakriti",
        "arts at prakriti",
        "enrichment activities prakriti",
        "prakriti sports",
        "prakriti arts",
        "prakriti enrichment",
        "activities at prakriti",
        "prakriti extracurricular",
        "prakriti co-curricular",
        "prakriti after school",
        "prakriti clubs",
        "prakriti music",
        "prakriti theater",
        "prakriti stem",
        "prakriti design lab",
        "prakriti mindfulness",
        "prakriti meditation",
        "prakriti maker projects",
        "prakriti farm outings",
        "prakriti field trips",
    ]
    if any(kw in user_query.lower() for kw in enrichment_activities_intents):
        canonical_answer = (
            'Prakriti integrates sports, visual & performing arts, music, theater, STEM/design labs, farm outings, meditation/mindfulness, and maker projects across all grades.'
        )
        prompt = (
            f"A user asked about sports, arts, and enrichment activities at Prakriti. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = openai_client.chat.completions.create(
            model=get_default_gpt_model(),
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.10: Intent-based Q&A for "What are the fees for different grades?"
    fees_intents = [
        "what are the fees for different grades",
        "prakriti fee structure",
        "school fees",
        "What is the school fees",
        "prakriti fees",
        "grade wise fees",
        "admission charges",
        "fee for nursery",
        "fee for grade 1",
        "fee for grade 12",
        "prakriti admission fee",
        "prakriti tuition",
        "prakriti security deposit",
        "prakriti monthly fee",
        "prakriti one time charges",
        "prakriti payment",
        "prakriti fee breakdown",
        "prakriti fee details",
        "prakriti fee for 2024",
        "prakriti fee for 2025",
    ]
    if any(kw in user_query.lower() for kw in fees_intents):
        canonical_answer = (
            '(2024–25 fee structure)\n'
            '| Grade | Monthly Fee (₹) | Security Deposit (₹, refundable) |\n'
            '|---|---|---|\n'
            '| Pre-Nursery–KG | 21,000 | 60,000 |\n'
            '| Grade I–V | 25,400 | 75,000 |\n'
            '| Grade VI–VIII | 28,000 | 90,000 |\n'
            '| Grade IX | 31,200 | 100,000 |\n'
            '| Grade X | 32,400 | 100,000 |\n'
            '| Grade XI–XII | 35,000 | 100,000 |\n'
            '| Admission charges (one-time, non-refundable) | – | 125,000'
        )
        prompt = (
            f"A user asked about the fees for different grades. Here is the official answer (including a table):\n{canonical_answer}\n"
            "Please explain this in your own words, summarize the fee structure, and mention the admission charges."
        )
        response = openai_client.chat.completions.create(
            model=get_default_gpt_model(),
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.11: Intent-based Q&A for "Where is Prakriti School located?" with Google Map embed
    location_intents = [
        "where is prakriti school located",
        "prakriti school location",
        "prakriti address",
        "prakriti location",
        "school address",
        "prakriti map",
        "how to reach prakriti",
        "prakriti school directions",
        "prakriti school google map",
        "prakriti school route",
        "prakriti school navigation",
        "prakriti school in greater noida",
        "prakriti school on expressway",
        "prakriti school ncr",
    ]
    if any(kw in user_query.lower() for kw in location_intents):
        canonical_answer = (
            'Prakriti is located on the Noida Expressway in Greater Noida, NCR.'
        )
        prompt = (
            f"A user asked about the location of Prakriti School. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = openai_client.chat.completions.create(
            model=get_default_gpt_model(),
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        # Google Maps embed URL for Prakriti School
        map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3502.123456789!2d77.123456!3d28.123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce4b123456789:0xabcdefabcdefabcd!2sPrakriti%20School!5e0!3m2!1sen!2sin!4v1710000000000!5m2!1sen!2sin"
        return [content.strip() if content else canonical_answer, {"type": "map", "url": map_url}]

    # Step 0.12: YouTube Video Intent Detection (only for clear video requests)
    # Explicit video request keywords - user is asking for a video
    explicit_video_keywords = [
        "show me a video", "show me video", "watch a video", "watch video", "see a video", "see video",
        "video about", "video of", "video on", "videos about", "videos of", "videos on",
        "play video", "play a video", "demonstration video", "video demonstration"
    ]
    
    # School activity keywords - these are specific to school events/activities that have videos
    school_activity_keywords = [
        "gardening program", "art exhibition", "sports day", "campus tour", "school tour",
        "facilities tour", "science fair", "music performance", "dance performance",
        "workshop video", "school activity", "school program", "school event"
    ]
    
    # Educational concept keywords that should NOT trigger video intent
    educational_concept_keywords = [
        "explain", "what is", "how does", "describe", "tell me about", "define", "meaning of",
        "concept", "theory", "principle", "detail", "details", "example", "examples",
        "magnetic field", "electric field", "gravity", "force", "energy", "molecule", "atom"
    ]
    
    query_lower = user_query.lower()
    
    # Check for explicit video requests
    is_explicit_video_query = any(kw in query_lower for kw in explicit_video_keywords)
    
    # Check for school activity queries
    is_school_activity_query = any(kw in query_lower for kw in school_activity_keywords)
    
    # Check if it's an educational concept query (should NOT trigger video)
    is_educational_concept_query = any(kw in query_lower for kw in educational_concept_keywords)
    
    # Only detect video intent for explicit video requests or school activities, NOT for educational concepts
    is_article_query = any(word in query_lower for word in ["article", "articles", "substack", "blog", "news", "text", "read"])
    is_video_query = (is_explicit_video_query or is_school_activity_query) and not is_educational_concept_query
    
    if is_video_query and not is_article_query:
        print("[Chatbot] Detected video intent, processing with LangGraph...")
        try:
            video_result = process_video_query(user_query)
            if video_result and isinstance(video_result, dict) and "videos" in video_result and video_result.get("videos"):
                # Return mixed response with text and videos
                response_text = video_result.get("response", "")
                videos = video_result.get("videos", [])
                if videos:
                    return [response_text, {"type": "videos", "videos": videos}]
            # Fall through to regular LLM response if no videos found
        except Exception as e:
            print(f"[Chatbot] Error processing video query: {e}")
            import traceback
            traceback.print_exc()
            # Continue with regular LLM processing instead of failing

    # Step 1.5: Web Crawling Enhancement for PrakritSchool queries
    # Detect query intent for smart data loading
    query_lower = user_query.lower()
    
    # Detect coursework queries FIRST (before person detail detection) to avoid conflicts
    is_homework_query = any(kw in query_lower for kw in ['homework', 'my homework', 'homework help', 'show homework'])
    is_assignment_query = any(kw in query_lower for kw in ['assignment', 'assignments', 'my assignment', 'my assignments', 'assignment help', 'show assignment', 'show assignments'])
    is_coursework_query = is_homework_query or is_assignment_query or any(kw in query_lower for kw in ['coursework', 'task', 'due', 'submit'])
    
    # Check if this is a person introduction/detail query (should use web crawler, NOT classroom data)
    # BUT exclude coursework/assignment queries - if query is about coursework, it's not a person detail query
    person_detail_keywords = ['introduction', 'detail', 'details', 'who is', 'about', 'little bit about', 
                             'information about', 'tell me about', 'profile', 'biography']
    is_person_detail_query = any(kw in query_lower for kw in person_detail_keywords) and not is_coursework_query
    
    # Check if query mentions a specific person name (capitalized words or known names)
    # Try both original query (for capitalized names) and lowercase (for case-insensitive detection)
    person_name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
    potential_names = re_module.findall(person_name_pattern, user_query)
    # If no capitalized names found, try case-insensitive pattern on lowercase query
    if not potential_names:
        # First, try to extract name after common question patterns (e.g., "who is X", "tell me about X")
        question_patterns = [
            r'(?:who\s+is|who\'?s|what\s+is|what\'?s|tell\s+me\s+about|information\s+about|details?\s+about|introduction\s+to|profile\s+of|biography\s+of|about)\s+(?:the\s+)?([a-z]+\s+[a-z]+(?:\s+[a-z]+)?)',
            r'(?:who\s+is|who\'?s|what\s+is|what\'?s|tell\s+me\s+about|information\s+about|details?\s+about|introduction\s+to|profile\s+of|biography\s+of|about)\s+([a-z]+\s+[a-z]+(?:\s+[a-z]+)?)',
        ]
        
        extracted_name = None
        for pattern in question_patterns:
            match = re_module.search(pattern, query_lower)
            if match:
                extracted_name = match.group(1).strip()
                # Remove trailing punctuation and question marks
                extracted_name = re_module.sub(r'[?.,!]+$', '', extracted_name).strip()
                if len(extracted_name) > 5:
                    potential_names = [extracted_name.title()]
                    break
        
        # Fallback: More restrictive pattern for lowercase names
        # Only consider 2-word phrases that look like actual names (not technical terms)
        if not potential_names:
            person_name_pattern_lower = r'\b[a-z]+\s+[a-z]+\b'  # Only 2-word phrases
            # Extract potential names (exclude common words, verbs, technical terms)
            excluded_words = {'the', 'is', 'who', 'what', 'when', 'where', 'why', 'how', 'about', 'tell', 'me',
                             'information', 'detail', 'details', 'introduction', 'profile', 'biography',
                             'little', 'bit', 'explain', 'describe', 'what', 'how', 'why', 'when', 'where',
                             'magnetic', 'field', 'fields', 'energy', 'force', 'physics', 'chemistry', 'math',
                             'science', 'biology', 'history', 'geography', 'computer', 'programming', 'code',
                             'data', 'system', 'process', 'method', 'theory', 'concept', 'principle', 'law'}
            all_words = re_module.findall(person_name_pattern_lower, query_lower)
            # Filter out phrases that contain excluded words, technical terms, or question words
            # Also exclude if it looks like a technical/scientific phrase
            potential_names_lower = []
            for name in all_words:
                words = name.split()
                if (len(words) == 2 and  # Must be exactly 2 words
                    len(name) > 6 and len(name) < 25 and  # Reasonable name length
                    not any(word in excluded_words for word in words) and
                    not name.endswith(('ing', 'ed', 'er', 'est', 'ly', 'tion', 'ment'))):  # Not verb forms or nouns
                    potential_names_lower.append(name)
            if potential_names_lower:
                # Convert to title case for consistency
                potential_names = [name.title() for name in potential_names_lower[:2]]  # Limit to first 2 matches
    
    has_person_name = len(potential_names) > 0 and not any(name.lower() in ['Prakriti', 'School', 'Google', 'Classroom', 'Calendar'] for name in potential_names)
    
    # Check if person query might be about a teacher (so we can verify with Classroom data)
    # If query mentions teacher-related terms, we should load teacher data to verify web crawler claims
    teacher_context_in_query = any(kw in query_lower for kw in ['teacher', 'teachers', 'homeroom', 'instructor', 'faculty', 'staff'])
    
    # If person detail query, use web crawler (even if name detection is imperfect)
    # Web crawler can search by the query itself, and we'll verify against Classroom data
    # BUT prioritize web crawler if we found a name (more specific search)
    should_use_web_crawling_first = is_person_detail_query  # Run web crawler for person queries regardless of name detection
    
    # Detect specific classroom data intent for optimized loading
    is_announcement_query = any(kw in query_lower for kw in ['announcement', 'announcements', 'announce', 'annuncement', 'notice', 'update', 'updates', 'news'])
    # Enhanced student query detection: includes "want", "list", "check", "exists" patterns
    is_student_query = any(kw in query_lower for kw in ['student', 'students', 'classmate', 'classmates', 'roster', 'enrollment']) or \
                       (any(kw in query_lower for kw in ['want', 'show', 'list', 'check']) and any(kw in query_lower for kw in ['classmate', 'student']))
    # Enhanced teacher query detection: includes "want", "list", "check" patterns
    is_teacher_query = any(kw in query_lower for kw in ['teacher', 'teachers', 'faculty', 'instructor', 'instructors', 'staff member', 'staff']) or \
                       (any(kw in query_lower for kw in ['want', 'show', 'list', 'check']) and any(kw in query_lower for kw in ['teacher', 'instructor']))
    
    # Check if query is about faculty with specific subject (e.g., "art and design facilitator", "math teacher")
    # These should use team_member_data instead of Classroom data
    subject_keywords_for_faculty = ['art', 'design', 'math', 'mathematics', 'science', 'english', 'history', 'physics', 
                                   'chemistry', 'biology', 'geography', 'computer', 'french', 'music', 'drama', 
                                   'literature', 'philosophy', 'economics', 'business', 'technology']
    faculty_role_keywords = ['facilitator', 'teacher', 'instructor', 'faculty', 'staff']
    has_subject_with_faculty = any(subj in query_lower for subj in subject_keywords_for_faculty) and \
                               any(role in query_lower for role in faculty_role_keywords)
    is_subject_faculty_query = has_subject_with_faculty or \
                               (is_person_detail_query and any(subj in query_lower for subj in subject_keywords_for_faculty))
    
    # Note: is_coursework_query, is_homework_query, and is_assignment_query are already defined above
    is_course_query = any(kw in query_lower for kw in ['course', 'courses', 'class', 'classes', 'subject', 'subjects'])
    # Separate holiday and event detection
    holiday_keywords = ['holiday', 'holidays', 'vacation', 'school holidays', 'holiday calendar', 'vacation calendar', 'holidays calendar', 'show holidays', 'holiday list']
    is_holiday_query = any(kw in query_lower for kw in holiday_keywords)

    event_keywords = ['event', 'events', 'calendar', 'schedule', 'meeting',
                      # Date/time question patterns
                      'when is', 'when will', 'when does', 'when do', 'when are',
                      'what date', 'what day', 'which date', 'which day',
                      'date of', 'day of', 'when', 'date', 'dates',
                      # Week/month patterns
                      'first week', 'second week', 'third week', 'fourth week', 'last week',
                      'this week', 'next week', 'upcoming week',
                      'events in', 'events on', 'events for', 'events during',
                      'held on', 'held in', 'scheduled on', 'scheduled in',
                      # Hindi calendar keywords (with common typos)
                      'ko kya hai', 'ko kya hota hai', 'ko kaya hai',
                      'ko kya hia', 'kya hai', 'kya hota hai', 'kya hia',
                      'mere school', 'school me', 'schoolm me', 'mere schoolm',
                      'merre schoolm', 'schoolm', 'mere', 'school']
    is_event_query = any(kw in query_lower for kw in event_keywords)
    
    # Also check for common event names (sports day, spring break, etc.)
    # This helps detect queries like "when is sports day" even without explicit event keywords
    common_event_names = ['sports day', 'spring break', 'book swap', 'session begins', 
                         'holiday', 'holidays', 'festival', 'festivals', 'diwali', 'holi',
                         'eid', 'christmas', 'vacation', 'break', 'semester', 'term']
    has_event_name = any(event_name in query_lower for event_name in common_event_names)
    
    # Check for "upcoming events" patterns (even with typos like "even s")
    upcoming_event_patterns = ['upcoming event', 'upcoming even', 'coming event', 'coming even',
                              'future event', 'future even', 'next event', 'next even']
    has_upcoming_pattern = any(pattern in query_lower for pattern in upcoming_event_patterns)
    
    # If query has event name, date/time question pattern, or upcoming events pattern, treat as event query
    if has_event_name or has_upcoming_pattern or any(pattern in query_lower for pattern in ['when is', 'when will', 'what date', 'what day', 'which date', 'which event', 'events on', 'events in', 'held on', 'held in']):
        is_event_query = True

    # Combined calendar query for backward compatibility
    is_calendar_query = is_holiday_query or is_event_query
    # Detect existence check queries
    is_existence_check_query = any(kw in query_lower for kw in ['exists', 'exist', 'check if', 'is there', 'is there a']) and \
                               (is_student_query or is_teacher_query)
    
    print(f"[Chatbot] Query Intent Detection:")
    print(f"  - is_person_detail_query: {is_person_detail_query}")
    print(f"  - has_person_name: {has_person_name} (names found: {potential_names})")
    print(f"  - Person Detail Query: {should_use_web_crawling_first}")
    print(f"  - Announcement: {is_announcement_query}")
    print(f"  - Student: {is_student_query}")
    print(f"  - Teacher: {is_teacher_query}")
    print(f"  - Coursework: {is_coursework_query}")
    print(f"  - Course: {is_course_query}")
    print(f"  - Calendar: {is_calendar_query}")
    print(f"  - Existence Check: {is_existence_check_query}")
    print(f"  - is_subject_faculty_query: {is_subject_faculty_query}")
    print(f"  - is_classroom_related_query (early): {(is_announcement_query or is_coursework_query or is_student_query or is_teacher_query or is_course_query or is_calendar_query) and not is_subject_faculty_query}")
    
    # Detect exam-related queries for drive integration (HIGH PRIORITY - before classroom detection)
    exam_keywords = ['exam', 'examination', 'test', 'assessment', 'schedule', 'timetable', 'time table', 'date sheet', 'syllabus', 'upcoming exam', 'exam date', 'exam schedule']
    # Also check for common variations and abbreviations
    timetable_variations = ['tim table', 'timetable', 'time table', 'tt', 'schedule', 'class schedule', 'daily schedule']
    # Check if query contains timetable-related words (including variations)
    has_timetable_keyword = any(variation in query_lower for variation in timetable_variations)
    # Check if query mentions a day (mon, tue, wed, thu, fri, sat, sun, monday, tuesday, etc.)
    day_keywords = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'today', 'tomorrow']
    has_day_keyword = any(day in query_lower for day in day_keywords)
    
    # If query has timetable keyword OR (has day keyword AND seems like a schedule query), treat as exam/timetable query
    is_exam_query = any(kw in query_lower for kw in exam_keywords) or (has_timetable_keyword or (has_day_keyword and ('give' in query_lower or 'show' in query_lower or 'get' in query_lower)))
    print(f"[Chatbot] 🧪 DEBUG: query_lower='{query_lower}', exam_keywords={exam_keywords}, is_exam_query={is_exam_query}")

    # For person detail queries, use web crawler first (team page)
    web_enhanced_info = ""
    should_use_web_crawling = False  # Initialize to avoid UnboundLocalError
    
    # Define web enhancement keywords outside if/else to avoid UnboundLocalError
    # Include common typos for admission/fees
    web_enhancement_keywords = [
        'latest', 'recent', 'news', 'update', 'current', 'new', 'recently',
        'prakriti school', 'prakrit school', 'progressive education',
        'alternative school', 'igcse', 'a level', 'bridge programme',
        'admission', 'admissions', 'addmission', 'addmissions', 'fees', 'fee', 'fee structure', 'fees structure',
        'curriculum', 'activities', 'facilities', 'contact', 'contact us',
        'article', 'articles', 'substack', 'philosophy', 'learning approach'
    ]
    
    if should_use_web_crawling_first:
        try:
            print("[Chatbot] Person detail query detected - using web crawler for team page...")
            web_enhanced_info = get_web_enhanced_response(user_query)
            if web_enhanced_info:
                print(f"[Chatbot] Web enhancement found: {len(web_enhanced_info)} characters")
            else:
                print("[Chatbot] No web enhancement found")
        except Exception as e:
            print(f"[Chatbot] Error in web crawling: {e}")
            web_enhanced_info = ""
    else:
        # For other queries, check if web crawling is beneficial
        # ONLY trigger for Prakriti-specific website content queries, NOT general academic questions
        # (web_enhancement_keywords already defined above)
        
        # Exclude academic/educational queries that don't need web crawling
        academic_keywords = ['newton', 'einstein', 'darwin', 'law of', 'laws', 'theorem', 'formula', 'solve', 'explain', 'understand', 'learn', 'study', 'help me with', 'teach me', 'how to', 'what is', 'concept', 'example']
        is_pure_academic_query = any(keyword in user_query.lower() for keyword in academic_keywords) and not any(school_keyword in user_query.lower() for school_keyword in ['prakriti', 'prakrit', 'school'])
        
        # Also exclude translation/reference queries (they reference previous responses, not website)
        translation_keywords = ['translate', 'translation', 'gujrati', 'gujarati', 'hindi', 'english', 'language', 'below response', 'previous response', 'that response', 'last response', 'above response']
        is_translation_query = any(keyword in user_query.lower() for keyword in translation_keywords)
        
        # CRITICAL: Skip web crawling for Classroom-related queries (announcements, coursework, students, teachers, courses, calendar)
        # These should use Classroom/Calendar data first, not web crawler
        # BUT exclude subject faculty queries (use team_member_data instead)
        # AND exclude exam queries (use drive integration instead)
        is_classroom_related_query = (is_announcement_query or is_coursework_query or is_student_query or is_teacher_query or is_course_query or is_calendar_query) and not is_subject_faculty_query and not is_exam_query
        
        # Normalize query to handle common typos (e.g., "addmission" -> "admission")
        normalized_query = user_query.lower()
        typo_corrections = {
            'addmission': 'admission', 'addmissions': 'admissions', 'addmision': 'admission',
            'fee structure': 'fees structure', 'fee': 'fees'  # Normalize fee to fees for matching
        }
        for typo, correct in typo_corrections.items():
            normalized_query = normalized_query.replace(typo, correct)
        
        # SPECIAL CASE: Allow article queries to use web crawling even if they're classroom-related
        # Trigger for any article query that might be philosophical/educational in nature
        is_article_query_override = 'article' in normalized_query.lower() and any(word in normalized_query.lower() for word in ['prakriti', 'philosophy', 'learning', 'education', 'environment', 'shaping', 'guide', 'voice', 'student'])

        should_use_web_crawling = any(keyword in normalized_query for keyword in web_enhancement_keywords) and not is_pure_academic_query and not is_translation_query and (not is_classroom_related_query or is_article_query_override) and not is_subject_faculty_query

        # For calendar queries with no events, skip web crawling to avoid showing generic fallback data
        # Note: calendar_events will be checked later after admin_data is loaded

        # Log why web crawling was skipped for classroom queries (but not for article queries)
        if is_classroom_related_query and any(keyword in user_query.lower() for keyword in web_enhancement_keywords) and not is_article_query_override:
            print(f"[Chatbot] ⚠️ Web crawling skipped - Classroom-related query detected. Using Classroom/Calendar data instead.")
        elif is_article_query_override:
            print(f"[Chatbot] 📝 Article query override - allowing web crawling for Prakriti/philosophy content despite classroom detection.")
    
    # Check if frontend provided cached web data
    cached_web_data = getattr(request, 'cached_web_data', None)

    # Special handling for calendar queries with no events - check after admin_data is loaded
    # This will be done later in the code after admin_data is available

    if should_use_web_crawling:
        # Use cached web data from browser if available (fastest)
        if cached_web_data and cached_web_data.strip():
            print(f"[Chatbot] ✅ Using cached web data from browser (fast response, no crawling needed)")
            web_enhanced_info = cached_web_data
        else:
            try:
                print(f"[Chatbot] ✅ Web crawling triggered for query: '{user_query}'")
                print("[Chatbot] Getting web-enhanced information...")
                web_enhanced_info = get_web_enhanced_response(user_query)
                if web_enhanced_info:
                    print(f"[Chatbot] ✅ Web enhancement found: {len(web_enhanced_info)} characters")
                else:
                    print("[Chatbot] ⚠️ Web enhancement returned empty")
            except Exception as e:
                print(f"[Chatbot] ❌ Error in web crawling: {e}")
                import traceback
                traceback.print_exc()
                web_enhanced_info = ""
    else:
        print(f"[Chatbot] ⚠️ Web crawling NOT triggered. Query: '{user_query}' | Keywords checked: {web_enhancement_keywords}")

    # Early detection of teacher/subject queries (needed before drive query check)
    is_teacher_drive_query = False
    is_teacher_subject_query = False
    try:
        from grade_exam_detector import GradeExamDetector
        detector = GradeExamDetector()
        analysis = detector.analyze_query(user_query)
        print(f"[Chatbot] DEBUG: Analysis result: {analysis}")
        is_teacher_drive_query = analysis.get('query_type') == 'teacher' and analysis.get('subject')
        is_teacher_subject_query = analysis.get('query_type') == 'teacher_subject' and analysis.get('teacher_name')
        print(f"[Chatbot] DEBUG: is_teacher_drive_query={is_teacher_drive_query}, is_teacher_subject_query={is_teacher_subject_query}")
    except Exception as e:
        print(f"[Chatbot] Error checking teacher queries: {e}")
        is_teacher_drive_query = False
        is_teacher_subject_query = False

    # Check for exam queries and teacher queries - use drive integration (HIGH PRIORITY - bypass classroom logic)
    drive_response = ""
    print(f"[Chatbot] 🔍 DRIVE QUERY CHECK: is_exam_query={is_exam_query}, is_teacher_drive_query={is_teacher_drive_query}, is_teacher_subject_query={is_teacher_subject_query}, query='{user_query}'")
    if is_exam_query or is_teacher_drive_query or is_teacher_subject_query:
        print(f"[Chatbot] 📚 EXAM QUERY DETECTED: '{user_query}' - using Google Drive integration")
        print(f"[Chatbot] 📊 is_exam_query: {is_exam_query}, exam_keywords: {exam_keywords}")
        try:
            # Import drive integration
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from drive_chatbot_integrator import DriveChatbotIntegrator

            integrator = DriveChatbotIntegrator()
            print(f"[Chatbot] 🧪 Calling drive integration with query='{user_query}', user_profile={user_profile}")
            drive_response = integrator.get_exam_info(user_query, user_profile)
            print(f"[Chatbot] 🧪 Drive integration returned: '{drive_response[:100]}...'")
            print(f"[Chatbot] 🔍 Drive integration returned: {len(drive_response) if drive_response else 0} characters")
            if drive_response:
                print(f"[Chatbot] 📄 Response preview: {drive_response[:100]}...")

            # Check if drive integration returned a "no data" error
            if drive_response and (drive_response.lower().startswith("sorry") or drive_response.lower().startswith("i couldn't")):
                print(f"[Chatbot] ⚠️ Drive integration returned no data error: {drive_response[:100]}")
                # Return a context-aware message based on query type
                if is_teacher_drive_query:
                    return f"I couldn't find teacher information for that subject in the timetable."
                elif is_exam_query:
                    # Check if it's a timetable query vs exam query
                    query_lower = user_query.lower()
                    if 'timetable' in query_lower or 'time table' in query_lower or 'schedule' in query_lower:
                        # It's a timetable query
                        return f"I couldn't find the timetable information. The information sheet for your grade may not be available or accessible. Please contact your administrator for assistance."
                    else:
                        # It's an exam query
                        return "There are no upcoming exams scheduled at this time."
                else:
                    # Generic fallback
                    return drive_response  # Return the original error message from drive integration
            elif drive_response and drive_response.startswith("TEACHER_INFO:"):
                print(f"[Chatbot] 👨‍🏫 Teacher info detected, enhancing with AI model")
                # Extract the raw teacher info and enhance it with AI
                teacher_info = drive_response.replace("TEACHER_INFO:", "").strip()
                print(f"[Chatbot] 📝 Raw teacher info: {teacher_info}")

                # Don't return directly - let it go through AI enhancement
                # Store it for later use in the main response logic
                teacher_enhanced_info = teacher_info
                drive_response = ""  # Clear drive response so it continues to AI
                print(f"[Chatbot] 🔄 Teacher info stored for AI enhancement")
            elif drive_response and drive_response.startswith("TEACHER_SUBJECT:"):
                print(f"[Chatbot] 📚 Teacher subject info detected, enhancing with AI model")
                # Extract the raw teacher subject info and enhance it with AI
                teacher_subject_info = drive_response.replace("TEACHER_SUBJECT:", "").strip()
                print(f"[Chatbot] 📝 Raw teacher subject info: {teacher_subject_info}")

                # Don't return directly - let it go through AI enhancement
                # Store it for later use in the main response logic
                teacher_enhanced_info = teacher_subject_info
                drive_response = ""  # Clear drive response so it continues to AI
                print(f"[Chatbot] 🔄 Teacher subject info stored for AI enhancement")
            elif drive_response:
                print(f"[Chatbot] ✅ Drive integration successful: {len(drive_response)} characters")
                print(f"[Chatbot] 📤 RETURNING DRIVE RESPONSE NOW: {len(drive_response)} chars")
                return drive_response
            else:
                print(f"[Chatbot] ⚠️ Drive integration returned no results or error: {drive_response[:100] if drive_response else 'None'}")
                drive_response = ""  # Reset to empty if invalid
        except Exception as e:
            print(f"[Chatbot] ❌ Error in drive integration: {e}")
            import traceback
            traceback.print_exc()
            exam_response = ""
            return f"Sorry, there was an error accessing exam information: {str(e)}"

    # Get admin data for enhanced responses - BUT only if not a person detail query OR web-only query
    # IMPORTANT: Use admin data (synced Google Classroom/Calendar) as REFERENCE for ALL users
    # This data is a shared knowledge base - not restricted to admins only
    admin_data = {"classroom_data": [], "calendar_data": []}

    # Check if this is a classroom/calendar/home related query
    # Exclude subject faculty queries from classroom-related (use team_member_data instead)
    # AND exclude exam queries (use drive integration instead)
    # AND exclude holiday queries (use classroom data, not admin drive data)
    # AND exclude teacher queries that should go to drive integration (timetable teacher lookup)

    is_classroom_related_query = (is_announcement_query or is_coursework_query or is_student_query or is_teacher_query or is_course_query or is_event_query or is_calendar_query) and not is_subject_faculty_query and not is_exam_query and not is_holiday_query and not is_teacher_drive_query
    is_home_related_query = any(kw in query_lower for kw in ['home', 'homework', 'my assignments', 'my coursework', 'my classes', 'my courses'])
    
    # Check for teacher-specific queries (submissions, grading, student work)
    is_submission_query = any(kw in query_lower for kw in ['submission', 'submitted', 'submitted work', 'student submission', 'check submission', 'grade submission', 'review submission', 'view submission'])
    is_grading_query = any(kw in query_lower for kw in ['grade', 'grading', 'assign grade', 'student grade', 'check grade', 'review grade'])
    is_teacher_classroom_query = is_submission_query or is_grading_query or (is_teacher_query and any(kw in query_lower for kw in ['my courses', 'my classes', 'my students', 'student work']))
    
    # Skip classroom data for web-only queries (PERFORMANCE OPTIMIZATION)
    is_web_only_query = should_use_web_crawling and not (is_announcement_query or is_coursework_query or is_student_query or is_teacher_query or is_course_query or is_calendar_query)
    
    # For guest users: Skip loading classroom data for classroom/home queries - they need to connect first
    # Include holiday queries in guest check (they need classroom connection for holiday info)
    is_guest_classroom_query = not user_profile and (is_classroom_related_query or is_home_related_query or is_holiday_query)
    
    # For teachers: Check if they need their own classroom connection for teacher-specific features
    user_role = user_profile.get('role', '').lower() if user_profile else None
    is_teacher_needing_connection = user_role == 'teacher' and (is_teacher_classroom_query or is_submission_query or is_grading_query)
    
    # Only load classroom data if it's actually needed for the query type
    # Don't load for general academic queries that don't need classroom data
    should_load_classroom_data = is_classroom_related_query or is_home_related_query or should_use_web_crawling_first
    
    if is_guest_classroom_query:
        print(f"[Chatbot] 🚫 Guest user asking about classroom/home - skipping data load (user needs to connect first)")
        admin_data = {"classroom_data": [], "calendar_data": []}
    elif is_teacher_needing_connection:
        print(f"[Chatbot] 🚫 Teacher asking about submissions/grading/their courses - requires their own Google Classroom connection")
        admin_data = {"classroom_data": [], "calendar_data": []}
    elif is_web_only_query:
        print(f"[Chatbot] ⚡ Skipping classroom data fetch - web-only query detected (faster response)")
    elif not should_load_classroom_data:
        print(f"[Chatbot] ⚡ Skipping classroom data fetch - not a classroom/home related query (general academic query)")
        admin_data = {"classroom_data": [], "calendar_data": []}
    elif ADMIN_FEATURES_AVAILABLE:
        try:
            print("[Chatbot] Getting reference data from Supabase (Google Classroom/Calendar sync)...")
            print(f"[Chatbot] User: {user_profile.get('email', 'Anonymous') if user_profile else 'Anonymous'}")
            
            # Try to get data from current user if they're admin, otherwise get from first available admin
            # This is REFERENCE data, not user-specific - anyone can use it
            user_email = user_profile.get('email', '') if user_profile else ''
            
            # Determine what to load based on query intent (optimize for speed and cost)
            # Only load what's needed: if asking about teachers, only load teachers; if students, only students; etc.
            # CRITICAL: Only load classroom data if it's explicitly needed for the query
            # For person detail queries, always load teachers to verify web crawler claims (web might say someone is a teacher)
            # BUT skip Classroom data for subject-related faculty queries (use team_member_data instead)
            if is_subject_faculty_query:
                print(f"[Chatbot] 🎯 Subject faculty query detected - using team_member_data instead of Classroom data")
            should_load_teachers = (is_teacher_query or should_use_web_crawling_first) and not is_subject_faculty_query
            should_load_students = is_student_query
            should_load_announcements = is_announcement_query
            should_load_coursework = is_coursework_query
            should_load_calendar = is_calendar_query or is_event_query  # Load calendar for event queries too
            
            # If no specific classroom data is needed, don't load anything
            if not (should_load_teachers or should_load_students or should_load_announcements or should_load_coursework or should_load_calendar):
                print(f"[Chatbot] ⚡ Skipping classroom data fetch - no classroom-specific data needed for this query")
                admin_data = {"classroom_data": [], "calendar_data": []}
                # Skip the rest of the data loading logic
                if admin_data.get('classroom_data') or admin_data.get('calendar_data'):
                    print(f"[Chatbot] ✅ Reference data loaded: {len(admin_data.get('classroom_data', []))} courses, {len(admin_data.get('calendar_data', []))} events")
                else:
                    print(f"[Chatbot] ⚠️ No reference data available (no courses or events synced yet)")
            else:
                # Set SQL-level limits to reduce token usage (cost optimization)
                # Only fetch what's needed from database, not everything
                limit_teachers = 50 if should_load_teachers else None  # Max 50 teachers
                limit_students = 50 if should_load_students else None  # Max 50 students
                limit_announcements = 20 if should_load_announcements else None  # Max 20 announcements (will filter by date if needed)
                limit_coursework = 20 if should_load_coursework else None  # Max 20 coursework items
                
                print(f"[Chatbot] Data loading plan (SQL-optimized):")
                print(f"  - Teachers: {should_load_teachers} (limit: {limit_teachers})")
                print(f"  - Students: {should_load_students} (limit: {limit_students})")
                print(f"  - Announcements: {should_load_announcements} (limit: {limit_announcements})")
                print(f"  - Coursework: {should_load_coursework} (limit: {limit_coursework})")
                print(f"  - Calendar: {should_load_calendar}")
                
                # Detect dates BEFORE calling get_admin_data for SQL-level filtering (cost optimization)
                query_lower = user_query.lower()
                is_today_query = any(kw in query_lower for kw in ['today', 'todays', "today's"])
                is_yesterday_query = any(kw in query_lower for kw in ['yesterday', "yesterday's"])
                
                # Get today's date for filtering
                from datetime import datetime, timezone, timedelta
                now = datetime.now(timezone.utc)
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Detect specific date(s) in query for SQL filtering
                target_date_ranges_for_sql = []  # List of (start, end) tuples for SQL filtering

                # Check for week-related queries
                is_past_week_query = any(kw in query_lower for kw in ['past week', 'last week', 'previous week'])
                is_this_week_query = any(kw in query_lower for kw in ['this week', 'current week'])

                if is_yesterday_query:
                    yesterday = now - timedelta(days=1)
                    target_date_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                    target_date_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
                    target_date_ranges_for_sql.append((target_date_start, target_date_end))
                    print(f"[Chatbot] SQL filtering for 'yesterday': {yesterday.date()}")
                elif is_today_query:
                    target_date_ranges_for_sql.append((today_start, today_end))
                    print(f"[Chatbot] SQL filtering for 'today': {now.date()}")
                elif is_past_week_query:
                    # Past week: from 7 days ago to yesterday
                    week_ago = now - timedelta(days=7)
                    week_start = week_ago.replace(hour=0, minute=0, second=0, microsecond=0)
                    yesterday_end = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
                    target_date_ranges_for_sql.append((week_start, yesterday_end))
                    print(f"[Chatbot] SQL filtering for 'past week': {week_start.date()} to {yesterday_end.date()}")
                elif is_this_week_query:
                    # This week: from Monday of current week to today
                    # Find Monday of current week (Monday = 0)
                    monday = now - timedelta(days=now.weekday())
                    week_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
                    target_date_ranges_for_sql.append((week_start, today_end))
                    print(f"[Chatbot] SQL filtering for 'this week': {week_start.date()} to {today_end.date()}")
                else:
                    # Check for specific dates in query - handle "21 and 29 september" or "21, 24, 29 september"
                    month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                                  'july', 'august', 'september', 'october', 'november', 'december']
                    month_abbrevs = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                    'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                    
                    for i, (full_name, abbrev) in enumerate(zip(month_names, month_abbrevs)):
                        # Pattern 1: Handles both single date ("21 september", "21st september", "21st feb") and multiple dates
                        # Matches: one or more digits with optional ordinal suffix (st, nd, rd, th), optionally followed by (comma or "and" + more digits), then month name
                        pattern1 = rf'\b(\d{{1,2}}(?:st|nd|rd|th)?(?:\s*(?:,|\s+and\s+)\s*\d{{1,2}}(?:st|nd|rd|th)?)*)\s+({full_name}|{abbrev})\b'
                        # Pattern 2: "september 21" or "september 21st" or "feb 21st" or "september 21 and 29"
                        pattern2 = rf'\b({full_name}|{abbrev})\s+(\d{{1,2}}(?:st|nd|rd|th)?(?:\s*(?:,|\s+and\s+)\s*\d{{1,2}}(?:st|nd|rd|th)?)*)\b'
                        
                        match = re_module.search(pattern1, query_lower, re_module.IGNORECASE)
                        if not match:
                            match = re_module.search(pattern2, query_lower, re_module.IGNORECASE)
                        
                        if match:
                            print(f"[Chatbot] 📅 Date pattern matched: pattern1/pattern2 found '{full_name}' or '{abbrev}' in query")
                        
                        # Fuzzy matching for typos (e.g., "octomber" -> "october")
                        if not match and len(full_name) > 4:
                            # Try to find month-like words near numbers - matches single or multiple dates (handles ordinals like 1st, 2nd, 3rd)
                            potential_months = re_module.findall(r'\d{1,2}(?:st|nd|rd|th)?(?:\s*(?:,|\s+and\s+)\s*\d{1,2}(?:st|nd|rd|th)?)*\s+([a-z]{4,})', query_lower)
                            for pot_month in potential_months:
                                if pot_month[:3] == full_name[:3] and len(pot_month) >= len(full_name) - 2:
                                    # Extract all digits before the month word (handles ordinals like 1st, 2nd, 3rd)
                                    days_match = re_module.search(rf'(\d{{1,2}}(?:st|nd|rd|th)?(?:\s*(?:,|\s+and\s+)\s*\d{{1,2}}(?:st|nd|rd|th)?)*)\s+{re_module.escape(pot_month)}', query_lower, re_module.IGNORECASE)
                                    if days_match:
                                        class MockMatch:
                                            def __init__(self, days_str):
                                                self._days = days_str
                                            def group(self, n):
                                                return self._days if n == 1 else None
                                        match = MockMatch(days_match.group(1))
                                        print(f"[Chatbot] Detected typo: '{pot_month}' → '{full_name}'")
                                        break
                        
                        if match:
                            month_num = i + 1
                            # Extract days string - try group 1 first, then group 2
                            days_str = None
                            try:
                                if match.group(1) and (match.group(1)[0].isdigit() or match.group(1).replace(' ', '').replace(',', '').replace('and', '').isdigit()):
                                    days_str = match.group(1)
                                elif len(match.groups()) > 1 and match.group(2) and (match.group(2)[0].isdigit() or match.group(2).replace(' ', '').replace(',', '').replace('and', '').isdigit()):
                                    days_str = match.group(2)
                            except:
                                pass
                            
                            if days_str:
                                # Extract all numbers (handles both comma and "and" separators, and ordinal suffixes like 21st, 22nd)
                                # Remove ordinal suffixes (st, nd, rd, th) before extracting numbers
                                days_str_clean = re_module.sub(r'(st|nd|rd|th)\b', '', days_str, flags=re_module.IGNORECASE)
                                days = [int(d.strip()) for d in re_module.findall(r'\d+', days_str_clean)]
                                year = now.year
                                # If month is in the past (e.g., we're in March but query is for February), use next year
                                if month_num < now.month:
                                    year += 1
                                for day in days:
                                    try:
                                        parsed_date = datetime(year, month_num, day, tzinfo=timezone.utc)
                                        date_start = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                                        date_end = parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                                        target_date_ranges_for_sql.append((date_start, date_end))
                                        print(f"[Chatbot] SQL filtering for date: {day} {month_names[i]} {year}")
                                    except ValueError:
                                        print(f"[Chatbot] Invalid date: {day}/{month_num}")
                                if target_date_ranges_for_sql:
                                    break
                    
                    # If no month names found, try DD/MM or MM/DD format (single date only for now)
                    if not target_date_ranges_for_sql:
                        date_pattern = r'\b(\d{1,2})[/-](\d{1,2})\b'
                        match = re_module.search(date_pattern, query_lower)
                        if match:
                            num1, num2 = int(match.group(1)), int(match.group(2))
                            try:
                                if num1 <= 31 and num2 <= 12:
                                    day, month = num1, num2
                                elif num2 <= 31 and num1 <= 12:
                                    day, month = num2, num1
                                else:
                                    day, month = num1, num2
                                
                                year = now.year
                                try:
                                    parsed_date = datetime(year, month, day, tzinfo=timezone.utc)
                                    date_start = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                                    date_end = parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                                    target_date_ranges_for_sql.append((date_start, date_end))
                                    print(f"[Chatbot] SQL filtering for date: {day}/{month}/{year}")
                                except ValueError:
                                    print(f"[Chatbot] Invalid date: {day}/{month}")
                            except:
                                pass
                
                # Check if user is a student asking about coursework - use direct coursework query
                user_role = user_profile.get('role', '') if user_profile else None
                user_id = user_profile.get('user_id', '') if user_profile else None
                
                # Allow coursework access for any user (not just students) based on email/user_id
                # Only apply grade filtering if user is actually a student with a grade
                coursework_data_from_direct_query = False  # Flag to track if data came from get_student_coursework_data
                if is_coursework_query and user_id:
                    # Determine work_type filter based on query (homework vs assignments)
                    work_type_filter = None
                    if is_homework_query:
                        work_type_filter = 'HOMEWORK'  # Will filter for ASSIGNMENT type
                        print(f"[Chatbot] Homework query detected - filtering for homework")
                    elif is_assignment_query:
                        work_type_filter = 'ASSIGNMENT'
                        print(f"[Chatbot] Assignment query detected - filtering for assignments")
                    
                    if user_role == 'student':
                        print(f"[Chatbot] Student coursework query detected - querying coursework table directly")
                        # Get student's grade for filtering
                        student_grade = user_profile.get('grade', '') if user_profile else None
                        admin_data = get_student_coursework_data(user_id, student_email=user_email, limit_coursework=limit_coursework or 20, user_grade=student_grade, work_type_filter=work_type_filter)
                        coursework_data_from_direct_query = True
                    else:
                        # Non-student user (e.g., college ID connected) - access by email/user_id without grade filtering
                        print(f"[Chatbot] Coursework query detected for non-student user - accessing by email/user_id (no grade filtering)")
                        admin_data = get_student_coursework_data(user_id, student_email=user_email, limit_coursework=limit_coursework or 20, user_grade=None, work_type_filter=work_type_filter)
                        coursework_data_from_direct_query = True
                else:
                    # First try current user if they have admin privileges
                    admin_data = get_admin_data(user_email,
                                               load_teachers=should_load_teachers,
                                               load_students=should_load_students,
                                               load_announcements=should_load_announcements,
                                               load_coursework=should_load_coursework,
                                               load_calendar=should_load_calendar,
                                               announcement_date_ranges=target_date_ranges_for_sql if target_date_ranges_for_sql else None,
                                               limit_announcements=limit_announcements,
                                               limit_students=limit_students,
                                               limit_teachers=limit_teachers,
                                               limit_coursework=limit_coursework)
                
                # If no data found from current user, try to get from any admin who has synced data
                if not admin_data.get('classroom_data') and not admin_data.get('calendar_data'):
                    print("[Chatbot] No data from current user, trying to get from any admin with synced data...")
                    try:
                        from supabase_config import get_supabase_client
                        supabase = get_supabase_client()
                        
                        # Find any admin who has synced classroom data
                        # IMPORTANT: user_id in google_classroom_courses is auth.users.id, not user_profiles.id
                        # Note: calendar_event_data is global (no user_id), so we can't use it to find user_id
                        result = supabase.table('google_classroom_courses').select('user_id').limit(1).execute()
                        
                        if result.data and len(result.data) > 0:
                            user_with_data_id = result.data[0]['user_id']  # This is auth.users.id
                            # Get the user's email - user_profiles.user_id references auth.users.id
                            user_profile_result = supabase.table('user_profiles').select('email').eq('user_id', user_with_data_id).limit(1).execute()
                            if user_profile_result.data and len(user_profile_result.data) > 0:
                                user_email = user_profile_result.data[0]['email']
                                print(f"[Chatbot] Found user with synced data: {user_email} (auth_user_id: {user_with_data_id})")
                                admin_data = get_admin_data(user_email,
                                                           load_teachers=should_load_teachers,
                                                           load_students=should_load_students,
                                                           load_announcements=should_load_announcements,
                                                           load_coursework=should_load_coursework,
                                                           load_calendar=should_load_calendar,
                                                           announcement_date_ranges=target_date_ranges_for_sql if target_date_ranges_for_sql else None,
                                                           limit_announcements=limit_announcements,
                                                           limit_students=limit_students,
                                                           limit_teachers=limit_teachers,
                                                           limit_coursework=limit_coursework)
                            else:
                                # If no email found, just use the user_id directly (skip email lookup)
                                print(f"[Chatbot] Found synced data for user_id: {user_with_data_id}, but no email in user_profiles")
                                # Query directly using user_id
                                courses_result = supabase.table('google_classroom_courses').select('*').eq('user_id', user_with_data_id).execute()
                                if courses_result.data:
                                    print(f"[Chatbot] Direct query found {len(courses_result.data)} courses")
                                    admin_data = get_admin_data(None,  # Let get_admin_data find it via fallback
                                                               load_teachers=should_load_teachers,
                                                               load_students=should_load_students,
                                                               load_announcements=should_load_announcements,
                                                               load_coursework=should_load_coursework,
                                                               load_calendar=should_load_calendar,
                                                               announcement_date_ranges=target_date_ranges_for_sql if target_date_ranges_for_sql else None,
                                                               limit_announcements=limit_announcements,
                                                               limit_students=limit_students,
                                                               limit_teachers=limit_teachers,
                                                               limit_coursework=limit_coursework)
                    except Exception as e:
                        print(f"[Chatbot] Error getting reference data from other admin: {e}")

                if admin_data.get('classroom_data') or admin_data.get('calendar_data'):
                    print(f"[Chatbot] ✅ Reference data loaded: {len(admin_data.get('classroom_data', []))} courses, {len(admin_data.get('calendar_data', []))} events")
                else:
                    print(f"[Chatbot] ⚠️ No reference data available (no courses or events synced yet)")

                # Special handling for calendar queries with no events
                calendar_events = admin_data.get('calendar_data', [])
                if is_calendar_query and len(calendar_events) == 0:
                    print("[Chatbot] 📅 Calendar query with no events - providing clear 'no events' response")
                    # Create a direct response for calendar queries with no events
                    calendar_response = f"**School Calendar Events**\n\nI don't have any upcoming school events scheduled in the calendar at this time. The school calendar is regularly updated with important dates, holidays, and special events.\n\nIf you're looking for information about:\n- **Holidays**: Check the school's holiday calendar\n- **Exam schedules**: Contact your teacher or administration\n- **Sports events**: Check with the physical education department\n- **Cultural activities**: Look for announcements in your classroom\n\nFor the most current information, please check with your teachers or the school administration."

                    # Add holiday context if today is a holiday
                    if global_holiday_context:
                        calendar_response += f"\n\n**Holiday Note**: Today is {global_holiday_context['message']} - {global_holiday_context['context']}"

                    return calendar_response

                # Special handling for date-specific calendar queries with no events on that date
                if is_calendar_query and target_date_ranges_for_sql and len(calendar_events) > 0:
                    # Check if any events fall within the requested date range
                    events_on_date = []
                    print(f"[Chatbot] 🔍 Filtering {len(calendar_events)} events for date range: {target_date_ranges_for_sql[0][0].date()} to {target_date_ranges_for_sql[0][1].date()}")
                    for event in calendar_events:
                        # Try both 'startTime' (formatted) and 'start_time' (raw) field names
                        event_start = event.get('startTime') or event.get('start_time', '')
                        event_title = event.get('summary', 'Unknown')
                        if event_start:
                            try:
                                from datetime import datetime
                                # Handle both ISO format and date-only format
                                if 'T' in event_start:
                                    event_datetime = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                                else:
                                    # Date-only format, assume start of day
                                    event_datetime = datetime.fromisoformat(event_start).replace(hour=0, minute=0, second=0, microsecond=0)
                                
                                # Make timezone-aware if not already
                                if event_datetime.tzinfo is None:
                                    from datetime import timezone
                                    event_datetime = event_datetime.replace(tzinfo=timezone.utc)
                                
                                event_date = event_datetime.date()
                                print(f"[Chatbot] 📅 Checking event '{event_title}': {event_date}")
                                
                                for date_start, date_end in target_date_ranges_for_sql:
                                    # Compare dates (ignore time for date-only queries)
                                    range_start_date = date_start.date()
                                    range_end_date = date_end.date()
                                    
                                    print(f"[Chatbot]   Comparing: {event_date} with range {range_start_date} to {range_end_date}")
                                    
                                    if range_start_date <= event_date <= range_end_date:
                                        print(f"[Chatbot]   ✅ MATCH! Event '{event_title}' is on {event_date}")
                                        events_on_date.append(event)
                                        break
                                    else:
                                        print(f"[Chatbot]   ❌ No match: {event_date} not in range {range_start_date} to {range_end_date}")
                            except Exception as e:
                                print(f"[Chatbot] Error parsing event date '{event_start}' for event '{event_title}': {e}")
                                import traceback
                                traceback.print_exc()
                                continue

                    print(f"[Chatbot] 📊 Found {len(events_on_date)} events on requested date")
                    # If events found on the requested date, filter calendar_events to only show those events
                    if len(events_on_date) > 0:
                        print(f"[Chatbot] ✅ Filtering calendar events to show only {len(events_on_date)} event(s) on requested date")
                        # Update calendar_events to only include events on the requested date
                        admin_data['calendar_data'] = events_on_date
                        calendar_events = events_on_date  # Also update local variable for consistency
                    # If no events on the requested date, provide concise response
                    elif len(events_on_date) == 0:
                        print(f"[Chatbot] 📅 Date-specific calendar query with no events on requested date - providing concise 'no events' response")
                        calendar_response = f"**School Calendar Events**\n\nI don't see any events scheduled specifically for the date you requested. The school calendar is regularly updated with important dates, holidays, and special events.\n\nFor the most current information, please check with your teachers or the school administration."

                        # Only add holiday context if the requested date is today
                        if global_holiday_context and target_date_ranges_for_sql:
                            from datetime import datetime, timezone
                            today = datetime.now(timezone.utc).date()
                            # Check if any of the requested date ranges includes today
                            is_today_query = any(
                                date_start.date() == today or date_end.date() == today
                                for date_start, date_end in target_date_ranges_for_sql
                            )
                            if is_today_query:
                                calendar_response += f"\n\n**Holiday Note**: Today is {global_holiday_context['message']} - {global_holiday_context['context']}"

                        return calendar_response
        except Exception as e:
            print(f"[Chatbot] ❌ Error getting reference data: {e}")
            import traceback
            traceback.print_exc()
            admin_data = {"classroom_data": [], "calendar_data": []}
    elif should_use_web_crawling_first:
        # For person detail queries, we still load teacher data above to verify web crawler claims
        # (web crawler might claim someone is a teacher, we need to verify against Google Classroom data)
        # So this branch is only reached if ADMIN_FEATURES_AVAILABLE was False
        print(f"[Chatbot] Person detail query - web crawler used, but teacher data was loaded if available to verify claims")
        # admin_data should already be populated above if ADMIN_FEATURES_AVAILABLE was True
        if not admin_data.get('classroom_data'):
            admin_data = {"classroom_data": [], "calendar_data": []}
    else:
        print(f"[Chatbot] ⚠️ Admin features not available - cannot fetch reference data")

    # Step 2: Fallback to LLM with streaming approach
    print("=" * 80)
    print("[Chatbot] 🤖 MODEL SELECTION: Cost Optimization")
    print("[Chatbot] 📋 Strategy:")
    print("[Chatbot]   • GPT-4o-mini: Used for ALL queries (optimal cost-performance balance)")
    print("[Chatbot] 💰 Expected cost: ~80% reduction vs using GPT-3.5-turbo for all queries")
    print("=" * 80)
    
    # Try multiple approaches to get complete response
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Build personalized system prompt with enhanced role-based logic
            personalization = ""
            role_specific_guidelines = ""
            
            if user_profile:
                role = user_profile.get('role', '') or ''
                role = role.lower() if role else ''
                first_name = user_profile.get('first_name', '')
                grade = user_profile.get('grade', '')
                subjects = user_profile.get('subjects', [])
                learning_goals = user_profile.get('learning_goals', '')
                interests = user_profile.get('interests', [])
                learning_style = user_profile.get('learning_style', '')
                department = user_profile.get('department', '')
                subjects_taught = user_profile.get('subjects_taught', [])
                relationship = user_profile.get('relationship_to_student', '')
                
                personalization = f"""

## Current User Context:
- **Name**: {first_name}
- **Role**: {role.title()}
"""
                
                if role == 'student':
                    personalization += f"""- **Grade**: {grade}
- **Subjects**: {', '.join(subjects) if subjects else 'Not specified'}
- **Learning Goals**: {learning_goals if learning_goals else 'Not specified'}
- **Interests**: {', '.join(interests) if interests else 'Not specified'}
- **Learning Style**: {learning_style if learning_style else 'Not specified'}"""
                    
                    role_specific_guidelines = """
## Student-Specific Guidelines:
- Address them as a student and use encouraging, supportive language
- Focus on their learning journey, academic growth, and personal development
- Reference their specific grade level and subjects when relevant
- Provide study tips, learning strategies, and academic guidance
- Encourage curiosity, creativity, and self-expression
- Mention how Prakriti's "learning for happiness" philosophy applies to their studies
- Suggest activities, projects, or resources that align with their interests
- Use age-appropriate language and examples
- Emphasize growth mindset and learning from mistakes
- Connect their learning goals to Prakriti's holistic approach
- **CRITICAL for homework help**: If the user asks for help with homework/assignments but doesn't specify the subject or topic, ALWAYS ask them to provide:
  1. Which subject they need help with (e.g., Mathematics, Science, English, etc.)
  2. What specific topic or problem they're working on
- Only provide generic homework solutions if the user explicitly provides both subject and topic information"""
                    
                elif role == 'teacher':
                    personalization += f"""- **Department**: {department}
- **Subjects Taught**: {', '.join(subjects_taught) if subjects_taught else 'Not specified'}"""
                    
                    role_specific_guidelines = """
## Teacher-Specific Guidelines:
- Address them as a colleague and fellow educator
- Focus on teaching methodologies, curriculum, and educational best practices
- Discuss classroom management, student engagement, and assessment strategies
- Reference their specific subjects and department when relevant
- Provide resources, lesson ideas, and professional development suggestions
- Discuss how to implement Prakriti's progressive teaching philosophy
- Share insights about student-centered learning and experiential education
- Offer support for inclusive teaching and the Bridge Programme
- Discuss collaboration with other teachers and parent communication
- Use professional, respectful language appropriate for educators"""
                    
                elif role == 'parent':
                    personalization += f"""- **Relationship**: {relationship.title() if relationship else 'Not specified'}"""
                
                    role_specific_guidelines = """
## Parent-Specific Guidelines:
- Address them as a parent and partner in their child's education
- Focus on their child's development, well-being, and academic progress
- Discuss how to support their child's learning at home
- Explain Prakriti's educational philosophy and how it benefits their child
- Provide guidance on communication with teachers and school staff
- Discuss the Bridge Programme and inclusive education if relevant
- Share information about school activities, events, and opportunities
- Address concerns about their child's academic or social development
- Explain school policies, procedures, and how to get involved
- Use warm, understanding language that acknowledges their role as advocates for their child"""
                
                else:
                    # Default for unknown roles
                    role_specific_guidelines = """
## General Guidelines:
- Be welcoming and informative about Prakriti School
- Provide comprehensive information about our programs and philosophy
- Encourage questions and engagement
- Use warm, professional language
- Focus on how Prakriti can meet their educational needs"""
                
                personalization += f"""

{role_specific_guidelines}

## General Personalization Guidelines:
- Always address the user by their first name when appropriate
- Use respectful titles (Sir/Madam) based on their gender preference when appropriate
- Tailor your tone and content to their specific role and context
- Reference their specific details (grade, subjects, department) when relevant
- Consider their goals, interests, and needs when providing advice
- Use their preferred learning style when suggesting study methods
- Be more specific and targeted in your responses based on their profile
- Maintain Prakriti's warm, encouraging, and inclusive tone
- Be respectful of gender identity and use appropriate language"""

            # Build messages array with conversation history
            # Build concise system prompts (TOKEN OPTIMIZATION - reduced by ~60%)
            if user_profile:
                # Ultra-concise system prompt for authenticated users
                # Exclude assignment/coursework queries from the "ask for more info" instruction
                homework_instruction = "" if is_coursework_query else """ IMPORTANT: For homework/study help requests without subject/topic, always ask for both subject and specific topic before providing solutions."""
                coursework_instruction = """ CRITICAL: For assignment/coursework queries, you MUST extract assignments from the provided Data section and show them immediately. DO NOT create fake assignments or generate examples like 'Topic: Algebra'. Use ONLY the actual assignment titles, descriptions, due dates, and links from the Data section. DO NOT ask for more information - the data is already provided. START your response directly with the assignments from the data, not with greetings or fake examples.""" if is_coursework_query else ""
                system_content = """You are Prakriti School's AI assistant. Progressive K-12 school in Greater Noida. Philosophy: "Learning for happiness". Programs: Bridge Programme, IGCSE, AS/A Level. Address users by first name with titles (Sir/Madam for teachers/parents). Use Markdown (**bold**, ### headings). Never say "as an AI". Present data directly without disclaimers.""" + personalization + """ Use provided data to answer questions.""" + homework_instruction + coursework_instruction
            else:
                # Ultra-concise system prompt for guest users (TOKEN OPTIMIZATION)
                # Exclude assignment/coursework queries from the "ask for more info" instruction
                homework_instruction = "" if is_coursework_query else """ IMPORTANT: For homework/study help, remind guest users to sign in and connect Google Classroom for personalized help. Always ask for subject and topic if not provided."""
                coursework_instruction = """ CRITICAL: For assignment/coursework queries, you MUST extract assignments from the provided Data section and show them immediately. DO NOT create fake assignments or generate examples like 'Topic: Algebra'. Use ONLY the actual assignment titles, descriptions, due dates, and links from the Data section. DO NOT ask for more information - the data is already provided. START your response directly with the assignments from the data, not with greetings or fake examples.""" if is_coursework_query else ""
                system_content = """You are Prakriti School's AI assistant. Progressive K-12 school in Greater Noida. Philosophy: "Learning for happiness". Use Markdown. Never say "as an AI". Present data directly. Use provided data to answer questions.""" + homework_instruction + coursework_instruction

            # Detect query language for system prompt
            query_language = detect_query_language(user_query)

            # 🎄 ADD HOLIDAY CONTEXT TO SYSTEM PROMPT
            # Use the globally detected holiday context
            holiday_info_parts = []

            if global_holiday_context:
                holiday_info_parts.append(f"Today: {global_holiday_context['message']}")

            if yesterday_holiday_context:
                holiday_info_parts.append(f"Yesterday: {yesterday_holiday_context['message']}")

            if holiday_info_parts:
                holiday_summary = " | ".join(holiday_info_parts)
                system_content += f"\n\n🎄 DATE CONTEXT: {holiday_summary}. When responding about specific dates, reference these holidays appropriately and maintain a celebratory tone where relevant."

            # 🌍 ADD LANGUAGE CONTEXT TO SYSTEM PROMPT
            if query_language != 'english':
                system_content += f"\n\n🌍 LANGUAGE CONTEXT: The user asked in {query_language.upper()}. Respond in {query_language} language to match the user's preferred language. IMPORTANT: Start your response directly with the answer - DO NOT restate, repeat, or rephrase the user's question. Begin immediately with relevant information."

            messages = [{"role": "system", "content": system_content}]

            # Detect query intent first (needed for history optimization)
            query_lower = user_query.lower()
            # Detect announcement queries (including common typos like "annunce", "announc", etc.)
            announcement_keywords = ['announcement', 'announce', 'annunce', 'announc', 'notice', 'update', 'news']
            is_announcement_query = any(kw in query_lower for kw in announcement_keywords)
            # Enhanced student query detection: includes "want", "list", "check", "exists" patterns
            is_student_query = any(kw in query_lower for kw in ['student', 'classmate', 'roster', 'enrollment']) or \
                               (any(kw in query_lower for kw in ['want', 'show', 'list', 'check']) and any(kw in query_lower for kw in ['classmate', 'student']))
            # Enhanced teacher query detection: includes "want", "list", "check" patterns
            is_teacher_query = any(kw in query_lower for kw in ['teacher', 'instructor', 'faculty']) or \
                               (any(kw in query_lower for kw in ['want', 'show', 'list', 'check']) and any(kw in query_lower for kw in ['teacher', 'instructor']))
            # Distinguish between homework and assignments (different in Google Classroom)
            is_homework_query = any(kw in query_lower for kw in ['homework', 'my homework', 'homework help', 'show homework'])
            is_assignment_query = any(kw in query_lower for kw in ['assignment', 'assignments', 'my assignment', 'my assignments', 'assignment help', 'show assignment', 'show assignments'])
            is_coursework_query = is_homework_query or is_assignment_query or any(kw in query_lower for kw in ['coursework', 'task', 'due', 'submit'])
            is_course_query = any(kw in query_lower for kw in ['course', 'class', 'subject'])
            # Detect existence check queries
            is_existence_check_query = any(kw in query_lower for kw in ['exists', 'exist', 'check if', 'is there', 'is there a']) and \
                                       (is_student_query or is_teacher_query)
            is_today_query = any(kw in query_lower for kw in ['today', 'todays', "today's"])
            is_yesterday_query = any(kw in query_lower for kw in ['yesterday', "yesterday's"])
            calendar_keywords = ['event', 'events', 'calendar', 'schedule', 'meeting', 'holiday',
                               # Hindi calendar keywords (with common typos)
                               'ko kya hai', 'ko kya hota hai', 'ko kaya hai',
                               'ko kya hia', 'kya hai', 'kya hota hai', 'kya hia',
                               'mere school', 'school me', 'schoolm me', 'mere schoolm',
                               'merre schoolm', 'schoolm', 'mere', 'school']
            is_calendar_query = any(kw in query_lower for kw in calendar_keywords)

            # Detect translation/reference queries (need previous response context)
            translation_keywords = ['translate', 'translation', 'gujrati', 'gujarati', 'hindi', 'english', 'language', 'below response', 'previous response', 'that response', 'last response', 'above response', 'send me in', 'give me in']
            is_translation_query = any(keyword in query_lower for keyword in translation_keywords)

            # 🌍 LANGUAGE LOGGING - Language already detected above for system prompt
            print(f"[Chatbot] 🌍 DETECTED LANGUAGE: {query_language}")

    # Skip conversation history for data queries (TOKEN OPTIMIZATION - saves ~100-200 tokens)
            # BUT include history for translation/reference queries (they need previous context)
            recent_history = []
            if is_translation_query:
                # For translation queries, include last 3 messages to get previous response context
                recent_history = conversation_history[-3:] if conversation_history else []
                print(f"[Chatbot] 🔄 Translation/reference query detected - including {len(recent_history)} previous messages for context")
            elif not (is_announcement_query or is_coursework_query or is_student_query or is_teacher_query or is_calendar_query):
                recent_history = conversation_history[-1:] if conversation_history else []  # Max 1 message for conversational queries
            
            for msg in recent_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Get today's date for filtering
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Detect specific date(s) in query (supports multiple dates like "22, 24, 30 october")
            target_dates = []  # List of (date, start, end) tuples
            target_date_ranges = []  # List of (start, end) tuples for filtering
            
            # Pattern for DD/MM or MM/DD format
            date_pattern_1 = r'\b(\d{1,2})[/-](\d{1,2})\b'
            
            if is_yesterday_query:
                # Yesterday = 1 day before today
                yesterday = now - timedelta(days=1)
                target_date_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                target_date_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
                target_dates.append((yesterday.date(), target_date_start, target_date_end))
                target_date_ranges.append((target_date_start, target_date_end))
                print(f"[Chatbot] Detected 'yesterday' query - filtering for: {yesterday.date()}")
            elif is_today_query:
                target_date_start = today_start
                target_date_end = today_end
                target_dates.append((now.date(), target_date_start, target_date_end))
                target_date_ranges.append((target_date_start, target_date_end))
                print(f"[Chatbot] Detected 'today' query - filtering for: {now.date()}")
            else:
                # Check for month name patterns first (e.g., "22, 24, 30 October" or "October 22, 24, 30")
                month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                              'july', 'august', 'september', 'october', 'november', 'december']
                month_abbrevs = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                
                found_month = False
                for i, (full_name, abbrev) in enumerate(zip(month_names, month_abbrevs)):
                    # Pattern to match: "22, 24, 30 october" or "october 22, 24, 30" or "22 october, 24 october"
                    # Also handle common typos like "octomber" → "october"
                    pattern1 = rf'\b(\d{{1,2}}(?:\s*,\s*\d{{1,2}})*)\s+({full_name}|{abbrev})\b'
                    pattern2 = rf'\b({full_name}|{abbrev})\s+(\d{{1,2}}(?:\s*,\s*\d{{1,2}})*)\b'
                    pattern3 = rf'\b(\d{{1,2}})\s+({full_name}|{abbrev})(?:\s*,\s*\d{{1,2}}\s+({full_name}|{abbrev}))*\b'
                    
                    match = re_module.search(pattern1, query_lower, re_module.IGNORECASE)
                    if not match:
                        match = re_module.search(pattern2, query_lower, re_module.IGNORECASE)
                    if not match:
                        match = re_module.search(pattern3, query_lower, re_module.IGNORECASE)
                    
                    # If no match, try fuzzy matching for common typos like "octomber" → "october"
                    if not match and len(full_name) > 4:
                        # Simple approach: check if query contains something that looks like the month
                        # Extract potential month words from query (words after numbers)
                        potential_months = re_module.findall(r'\d+\s*,\s*\d+(?:\s*,\s*\d+)*\s+([a-z]{4,})', query_lower)
                        for pot_month in potential_months:
                            # Check if it's similar to current month name (first 3-4 chars match)
                            if pot_month[:3] == full_name[:3] and len(pot_month) >= len(full_name) - 2:
                                # Extract days from query
                                days_pattern = rf'(\d+(?:\s*,\s*\d+)*)\s+{re_module.escape(pot_month)}'
                                days_match = re_module.search(days_pattern, query_lower, re_module.IGNORECASE)
                                if days_match:
                                    # Create a mock match object
                                    class MockMatch:
                                        def __init__(self, days_str, month_str):
                                            self._days = days_str
                                            self._month = month_str
                                        def group(self, n):
                                            if n == 1:
                                                return self._days
                                            elif n == 2:
                                                return self._month
                                            return None
                                    match = MockMatch(days_match.group(1), full_name)
                                    print(f"[Chatbot] Detected typo: '{pot_month}' → '{full_name}'")
                                    break
                    
                    if match:
                        month_num = i + 1
                        # Extract day numbers from the match
                        days_str = match.group(1) if match.group(1) and match.group(1)[0].isdigit() else (match.group(2) if match.group(2) and match.group(2)[0].isdigit() else None)
                        
                        if not days_str:
                            # Try to extract from pattern3
                            days_str = match.group(1) if match else None
                        
                        if days_str:
                            # Parse comma-separated days
                            days = [int(d.strip()) for d in re_module.findall(r'\d+', days_str)]
                            year = now.year
                            
                            for day in days:
                                try:
                                    parsed_date = datetime(year, month_num, day, tzinfo=timezone.utc)
                                    date_start = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                                    date_end = parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                                    target_dates.append((parsed_date.date(), date_start, date_end))
                                    target_date_ranges.append((date_start, date_end))
                                    print(f"[Chatbot] Detected date: {day} {month_names[i]} {year}")
                                except ValueError:
                                    print(f"[Chatbot] Invalid date: {day}/{month_num}")
                            
                            if target_dates:
                                found_month = True
                                break
                
                # If no month names found, try DD/MM or MM/DD format (single date only for now)
                if not found_month:
                    match = re_module.search(date_pattern_1, user_query)
                    if match:
                        num1, num2 = int(match.group(1)), int(match.group(2))
                        try:
                            if num1 <= 31 and num2 <= 12:
                                day, month = num1, num2
                            elif num2 <= 31 and num1 <= 12:
                                day, month = num2, num1
                            else:
                                day, month = num1, num2
                            
                            year = now.year
                            try:
                                parsed_date = datetime(year, month, day, tzinfo=timezone.utc)
                                date_start = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                                date_end = parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                                target_dates.append((parsed_date.date(), date_start, date_end))
                                target_date_ranges.append((date_start, date_end))
                                print(f"[Chatbot] Detected specific date query: {day}/{month}/{year}")
                            except ValueError:
                                print(f"[Chatbot] Invalid date: {day}/{month}")
                        except:
                            pass
            
            # Add current user query - minimal format (TOKEN OPTIMIZATION)
            user_content = f"{user_query}\n"

            # Add teacher information if available from drive integration
            if 'teacher_enhanced_info' in locals() and teacher_enhanced_info:
                user_content += f"\n👨‍🏫 TEACHER INFORMATION: {teacher_enhanced_info}\n"
                user_content += "Provide a brief, friendly response introducing the teacher(s). Keep it concise and warm.\n"
                user_content += "Example: 'Your Science teachers are Mrs. Krishna and Mr. Mohit. They're wonderful educators at Prakriti School!'\n\n"
                # Skip web enhancement for teacher queries answered by drive integration
                web_enhanced_info = ""
            
            # CRITICAL: For coursework queries, add immediate instruction BEFORE data section
            if is_coursework_query:
                user_content += "\n🚨🚨🚨 IMMEDIATE ACTION REQUIRED - READ THIS FIRST! 🚨🚨🚨\n"
                user_content += "**THE USER IS ASKING FOR ASSIGNMENTS/COURSEWORK. YOU WILL RECEIVE THE DATA BELOW.**\n"
                user_content += "**YOUR JOB: Extract ALL matching assignments from the Data section and show them IMMEDIATELY.**\n"
                user_content += "**🚨 ABSOLUTELY FORBIDDEN: DO NOT CREATE FAKE ASSIGNMENTS! DO NOT GENERATE EXAMPLES! 🚨**\n"
                user_content += "**🚨 YOU MUST USE ONLY THE ASSIGNMENTS FROM THE DATA SECTION BELOW! 🚨**\n"
                user_content += "**🚨 IF THE DATA SECTION HAS ASSIGNMENTS, SHOW THOSE EXACT ASSIGNMENTS - NOT GENERIC EXAMPLES! 🚨**\n"
                user_content += "**FORBIDDEN RESPONSES:**\n"
                user_content += "- DO NOT say 'Topic: Algebra' or 'Topic: Literature Analysis'\n"
                user_content += "- DO NOT create example problems or generic assignments\n"
                user_content += "- DO NOT generate fake assignment titles\n"
                user_content += "- DO NOT make up topics, descriptions, or due dates\n"
                user_content += "**MANDATORY:** Use ONLY the assignment titles, descriptions, due dates, and links from the Data section below.\n"
                user_content += "**DO NOT ask for more information - the data is already provided below!**\n"
                user_content += "**DO NOT start with greetings - START DIRECTLY WITH THE ASSIGNMENTS FROM THE DATA!**\n"
                if 'english' in query_lower:
                    user_content += "**SPECIFIC INSTRUCTION: The user asked for 'English assignments'. Find ALL assignments with 'ENGLISH' or 'English' in the title from the Data section below and show them ALL with full details (title, description if available, due date, link). DO NOT create fake English assignments!**\n"
                elif 'math' in query_lower or 'maths' in query_lower:
                    user_content += "**SPECIFIC INSTRUCTION: The user asked for 'Math/Maths assignments'. Find ALL assignments with 'Math', 'Maths', 'Mathematics' in the title from the Data section below and show them ALL with full details (title, description if available, due date, link). DO NOT create fake Math assignments!**\n"
                user_content += "**START YOUR RESPONSE BY LISTING THE ACTUAL ASSIGNMENTS FROM THE DATA - NO GREETINGS, NO QUESTIONS, NO FAKE EXAMPLES!**\n\n"
            
            if web_enhanced_info:
                # TRUNCATE web info - TOKEN OPTIMIZATION (reduced to 300 chars for queries with classroom data)
                # EXCEPTION: For person queries, don't truncate - we need full person information
                if should_use_web_crawling_first:
                    # Person query - use full information (up to 2000 chars to be safe)
                    max_web_chars = 2000
                    print(f"[Chatbot] Person query detected - using full web info ({len(web_enhanced_info)} chars)")
                else:
                    # If classroom data exists, use less web info to prioritize classroom data
                    max_web_chars = 300 if admin_data.get('classroom_data') else 400
                
                truncated_web_info = web_enhanced_info[:max_web_chars] + ("..." if len(web_enhanced_info) > max_web_chars else "")
                user_content += f"Web:\n{truncated_web_info}\n"
                if len(web_enhanced_info) > max_web_chars:
                    print(f"[Chatbot] Truncated web_enhanced_info from {len(web_enhanced_info)} to {max_web_chars} chars to save tokens")
                
                # CRITICAL: For person queries, use the Web information to answer
                if should_use_web_crawling_first:
                    # Check if web info contains actual data or "Information Not Available"
                    if web_enhanced_info and "Information Not Available" not in web_enhanced_info and "not found" not in web_enhanced_info.lower() and "sorry" not in web_enhanced_info.lower():
                        user_content += "\n**IMPORTANT: This is a person/team member query. The Web section above contains structured information about the person (Name, Title, Description, Details). Format this information as a natural, conversational chatbot response - NOT as a search result or bullet points. Write it like you're having a friendly conversation, introducing the person naturally. Include their name, title, background, and key details in a flowing narrative style. Use proper formatting with **bold** for emphasis where appropriate, but make it sound like a helpful assistant explaining who this person is, not like a database search result.**\n"
                    else:
                        # Web info says "not available" but we should still try to extract what we can
                        user_content += "\n**IMPORTANT: This is a person detail query. If the Web section contains any information about the person (even partial), use it. If it says 'Information Not Available', check if there's any mention of the person in the Classroom data or provide a helpful response directing them to contact the school.**\n"
                
                # CRITICAL: If web info claims someone is a teacher AND we have Classroom data, verify against it
                # BUT skip verification for subject-related faculty queries (use team_member_data as primary source)
                if admin_data.get('classroom_data') and should_use_web_crawling_first and not is_subject_faculty_query:
                    user_content += "\n⚠️ VERIFICATION: Use Web data to provide general information about the person (role, background, etc.). However, if Web info claims they are a teacher, VERIFY against Classroom Data below. Only confirm they are CURRENTLY a teacher for the user's grade/course if their name appears in the Classroom teacher list. If Web says they're a teacher but they're NOT in Classroom Data, provide the general info from Web but clarify their current teaching status based on Classroom Data.\n"
                elif is_subject_faculty_query:
                    user_content += "\n✅ FACULTY QUERY: This is a query about a faculty member with a specific subject/role. Use team_member_data as the PRIMARY source. Do NOT check Classroom data for this - team_member_data contains the accurate information about faculty members and their roles/subjects. Provide information directly from team_member_data without mentioning Classroom data.\n"
            
            # Check again for guest classroom query and teacher connection requirements (re-check in this scope)
            is_guest_classroom_query_local = not user_profile and (is_announcement_query or is_coursework_query or is_student_query or is_teacher_query or is_course_query or is_calendar_query or is_holiday_query or any(kw in query_lower for kw in ['home', 'homework', 'my assignments', 'my coursework', 'my classes', 'my courses']))
            user_role_local = user_profile.get('role', '').lower() if user_profile else None
            is_submission_query_local = any(kw in query_lower for kw in ['submission', 'submitted', 'submitted work', 'student submission', 'check submission', 'grade submission', 'review submission', 'view submission'])
            is_grading_query_local = any(kw in query_lower for kw in ['grade', 'grading', 'assign grade', 'student grade', 'check grade', 'review grade'])
            is_teacher_classroom_query_local = is_submission_query_local or is_grading_query_local or (is_teacher_query and any(kw in query_lower for kw in ['my courses', 'my classes', 'my students', 'student work']))
            is_teacher_needing_connection_local = user_role_local == 'teacher' and is_teacher_classroom_query_local
            
            # For guest users: If asking about classroom/home, instruct to connect (data was not loaded)
            if is_guest_classroom_query_local:
                user_content += "\n⚠️⚠️⚠️ CLASSROOM CONNECTION REQUIRED: ⚠️⚠️⚠️\n"
                user_content += "**CRITICAL: You are a guest user asking about classroom/home-related information.**\n"
                user_content += "**DO NOT provide any classroom data or answer with classroom information.**\n"
                user_content += "**ONLY tell the user:** To access classroom information, announcements, assignments, or calendar events, you need to sign in and connect your Google Classroom account first.\n"
                user_content += "**RESPONSE FORMAT:** Please sign in to your account and connect Google Classroom to access this information.\n"
                user_content += "**DO NOT ATTEMPT TO ANSWER THE QUERY WITH CLASSROOM DATA - YOU DON'T HAVE ACCESS TO IT.**\n"
                user_content += f"**IMPORTANT: The user is asking: '{user_query}' - DO NOT answer this query. Instead, ONLY tell them they need to sign in and connect Google Classroom first.**\n\n"
            # For teachers: If asking about submissions/grading/their courses, they need their own connection
            elif is_teacher_needing_connection_local:
                user_content += "\n⚠️⚠️⚠️ TEACHER CLASSROOM CONNECTION REQUIRED: ⚠️⚠️⚠️\n"
                user_content += "**CRITICAL: You are a teacher asking about submissions, grading, or your own courses/students.**\n"
                user_content += "**DO NOT provide any classroom data or answer with classroom information.**\n"
                user_content += "**ONLY tell the user:** To access student submissions, grade assignments, view your courses, or check student work, you need to connect your Google Classroom account. This allows you to see submissions from your students and access teacher-specific features.\n"
                user_content += "**RESPONSE FORMAT:** Please connect your Google Classroom account to access submission data, grading features, and your courses.\n"
                user_content += "**DO NOT ATTEMPT TO ANSWER THE QUERY WITH CLASSROOM DATA - YOU DON'T HAVE ACCESS TO YOUR OWN CLASSROOM DATA YET.**\n"
                user_content += f"**IMPORTANT: The user is asking: '{user_query}' - DO NOT answer this query. Instead, ONLY tell them they need to connect their Google Classroom account to access teacher features.**\n\n"
            
            # Add admin data if available - MINIMAL HEADER to save tokens
            # BUT skip for guest users asking classroom/home queries OR teachers needing their own connection
            if not is_guest_classroom_query_local and not is_teacher_needing_connection_local and (admin_data.get('classroom_data') or (admin_data.get('calendar_data') and is_calendar_query)):
                user_content += "Data:\n"
                
                if admin_data.get('classroom_data'):
                    # ULTRA-AGGRESSIVE FILTERING: Only send exactly what's needed for this query type
                    filtered_courses = []
                    
                    # Filter courses by student's grade if user is a student
                    # BUT skip if data came from get_student_coursework_data (already handled grade filtering with fallback)
                    user_grade_num = None
                    
                    # Check if data came from direct coursework query (already handled grade filtering)
                    skip_grade_filter_for_coursework = coursework_data_from_direct_query and is_coursework_query
                    if skip_grade_filter_for_coursework:
                        print(f"[Chatbot] Coursework data from direct query - skipping grade filter (already handled with fallback logic)")
                    
                    if user_profile and not skip_grade_filter_for_coursework:
                        user_role = user_profile.get('role', '') or ''
                        user_role_lower = user_role.lower()
                        print(f"[Chatbot] User role: {user_role_lower}, Grade filter check...")
                        
                        if user_role_lower == 'student':
                            user_grade = user_profile.get('grade', '')
                            print(f"[Chatbot] Student grade from profile: '{user_grade}'")
                            if user_grade:
                                # Normalize grade format (e.g., "Grade 8", "G8", "8" -> extract "8")
                                grade_match = re_module.search(r'(\d+)', str(user_grade))
                                if grade_match:
                                    user_grade_num = grade_match.group(1)
                                    print(f"[Chatbot] ✅ Filtering ALL data (courses, teachers, announcements, coursework) for Grade {user_grade_num} student")
                                else:
                                    print(f"[Chatbot] ⚠️ Could not extract grade number from: '{user_grade}'")
                            else:
                                print(f"[Chatbot] ⚠️ No grade found in user profile")
                        else:
                            print(f"[Chatbot] User is not a student (role: {user_role_lower}), skipping grade filter")
                    
                    for course in admin_data['classroom_data']:
                        # If user is a student, filter ALL courses by grade (unless data came from direct coursework query)
                        if user_grade_num and not skip_grade_filter_for_coursework:
                            course_name = course.get('name', '')
                            # Check if course name contains the grade (e.g., "G8", "Grade 8", "(8)")
                            # Match patterns like: G8, G 8, Grade 8, (G8), (8), Grade-8, etc.
                            grade_patterns = [
                                rf'\bG{user_grade_num}\b',
                                rf'\bG\s*{user_grade_num}\b',
                                rf'\bGrade\s*{user_grade_num}\b',
                                rf'\(G{user_grade_num}\)',
                                rf'\(G\s*{user_grade_num}\)',
                                rf'\(Grade\s*{user_grade_num}\)',
                                rf'\({user_grade_num}\)',
                                rf'Grade-{user_grade_num}',
                            ]
                            matches_grade = any(re_module.search(pattern, course_name, re_module.IGNORECASE) for pattern in grade_patterns)
                            
                            if not matches_grade:
                                print(f"[Chatbot] Skipping course '{course_name}' - doesn't match Grade {user_grade_num}")
                                continue
                            else:
                                print(f"[Chatbot] Including course '{course_name}' - matches Grade {user_grade_num}")
                        
                        # Determine which query type is most specific (prioritize specific queries)
                        query_type_priority = []
                        if is_announcement_query:
                            query_type_priority.append('announcement')
                        if is_student_query:
                            query_type_priority.append('student')
                        if is_teacher_query:
                            query_type_priority.append('teacher')
                        if is_coursework_query:
                            query_type_priority.append('coursework')
                        
                        # If no specific query, default to general course info
                        if not query_type_priority:
                            query_type_priority = ['general']
                        
                        # Only include course name + link (minimal info for token optimization)
                        filtered_course = {
                            "name": course.get('name', ''),
                        }
                        
                        # Always include course_link if available (needed for coursework/announcement queries)
                        if course.get('course_link'):
                            filtered_course["course_link"] = course.get('course_link')
                        
                        # ONLY include data for the specific query type (cost optimization)
                        if 'announcement' in query_type_priority:
                            announcements = course.get('announcements', [])
                            if announcements:
                                if target_date_ranges:
                                    # Filter announcements for specific date(s)
                                    filtered_announcements = []
                                    for ann in announcements:
                                        update_time_str = ann.get('updateTime', '')
                                        if update_time_str:
                                            try:
                                                update_time = datetime.fromisoformat(update_time_str.replace('Z', '+00:00'))
                                                if update_time.tzinfo is None:
                                                    update_time = update_time.replace(tzinfo=timezone.utc)
                                                for date_start, date_end in target_date_ranges:
                                                    if date_start <= update_time <= date_end:
                                                        filtered_announcements.append({
                                                            "text": ann.get('text', ''),
                                                            "date": ann.get('updateTime', ''),
                                                            "url": ann.get('url', '')
                                                        })
                                                        break
                                            except:
                                                pass
                                    filtered_course["announcements"] = filtered_announcements
                                    filtered_course["has_announcements"] = len(filtered_announcements) > 0
                                else:
                                    # Limit to 10 most recent
                                    sorted_ann = sorted(announcements, key=lambda x: x.get('updateTime', ''), reverse=True)[:10]
                                    filtered_course["announcements"] = [{
                                        "text": ann.get('text', ''),
                                        "date": ann.get('updateTime', ''),
                                        "url": ann.get('url', '')
                                    } for ann in sorted_ann]
                                    filtered_course["has_announcements"] = len(sorted_ann) > 0
                            else:
                                filtered_course["announcements"] = []
                                filtered_course["has_announcements"] = False
                        
                        if 'student' in query_type_priority:
                            students = course.get('students', [])[:50]  # Limit from SQL already applied
                            filtered_students = []
                            for s in students:
                                student_info = {"id": s.get("studentId"), "name": s.get("studentName")}
                                profile = s.get("profile", {})
                                if profile and 'email' in user_query.lower():
                                    email = profile.get("emailAddress", "")
                                    if email:
                                        student_info["email"] = email
                                filtered_students.append(student_info)
                            filtered_course["students"] = filtered_students
                        
                        if 'teacher' in query_type_priority:
                            teachers = course.get('teachers', [])
                            filtered_teachers = []
                            for t in teachers:
                                teacher_info = {"id": t.get("teacherId"), "name": t.get("teacherName")}
                                profile = t.get("profile", {})
                                if profile and 'email' in user_query.lower():
                                    email = profile.get("emailAddress", "")
                                    if email:
                                        teacher_info["email"] = email
                                filtered_teachers.append(teacher_info)
                            filtered_course["teachers"] = filtered_teachers
                        
                        if 'coursework' in query_type_priority:
                            coursework = course.get('coursework', [])[:20]  # Limit from SQL already applied
                            if coursework:
                                # Pre-filter coursework by subject if query is subject-specific
                                # Extract subject keywords from query (e.g., "BME", "OOPU", "ENGLISH", "MATHS")
                                query_upper = user_query.upper()
                                subject_keywords = []
                                
                                # Common subject patterns - using word boundaries to avoid false matches
                                # (e.g., "ES" matching inside "assignment")
                                if re.search(r'\b(BME|BIOMEDICAL|BIOMED)\b', query_upper):
                                    subject_keywords.extend(['BME'])
                                if re.search(r'\b(OOPU|OOP-U|OOP\s+U)\b', query_upper):
                                    subject_keywords.extend(['OOPU', 'OOP-U', 'OOP U'])
                                if re.search(r'\b(ENGLISH|ENG)\b', query_upper):
                                    subject_keywords.extend(['ENGLISH', 'ENG'])
                                if re.search(r'\b(MATH|MATHS|MATHEMATICS)\b', query_upper):
                                    subject_keywords.extend(['MATH', 'MATHS', 'MATHEMATICS', 'MATHEMATICS-1', 'MATHS-1'])
                                if re.search(r'\b(PPS|PROGRAMMING)\b', query_upper):
                                    subject_keywords.extend(['PPS'])
                                if re.search(r'\b(BE|BASIC\s+ENGINEERING)\b', query_upper):
                                    subject_keywords.extend(['BE'])
                                # ES must be a standalone word, not part of "assignment" or other words
                                if re.search(r'\b(ES|ENVIRONMENTAL)\b', query_upper):
                                    subject_keywords.extend(['ES'])
                                
                                # If subject keywords found, filter coursework to only matching assignments
                                if subject_keywords:
                                    print(f"[Chatbot] Subject-specific query detected. Filtering for: {subject_keywords}")
                                    filtered_coursework = []
                                    for c in coursework:
                                        title_upper = c.get("title", "").upper()
                                        # Check if assignment title contains any of the subject keywords
                                        if any(kw in title_upper for kw in subject_keywords):
                                            filtered_coursework.append(c)
                                    coursework = filtered_coursework
                                    print(f"[Chatbot] Filtered to {len(coursework)} matching assignments (from {len(course.get('coursework', []))} total)")
                                
                                # Apply date filtering if date is specified in query
                                if target_date_ranges and len(coursework) > 0:
                                    print(f"[Chatbot] Date filtering detected - filtering coursework by date")
                                    from datetime import datetime, timezone
                                    date_filtered_coursework = []
                                    for c in coursework:
                                        due_date_str = c.get("dueDate") or c.get("due_date") or c.get("due")
                                        if due_date_str:
                                            try:
                                                # Parse the due date
                                                if isinstance(due_date_str, str):
                                                    # Try parsing ISO format
                                                    if 'T' in due_date_str:
                                                        due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                                                    else:
                                                        # Try date only format
                                                        due_date = datetime.strptime(due_date_str.split('T')[0], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                                                else:
                                                    continue
                                                
                                                # Check if due date falls within any of the target date ranges
                                                matches_date = False
                                                for date_start, date_end in target_date_ranges:
                                                    if date_start <= due_date <= date_end:
                                                        matches_date = True
                                                        break
                                                
                                                if matches_date:
                                                    date_filtered_coursework.append(c)
                                            except Exception as e:
                                                print(f"[Chatbot] Error parsing due date '{due_date_str}': {e}")
                                                # If we can't parse, include it (better to show than hide)
                                                date_filtered_coursework.append(c)
                                        else:
                                            # No due date - include it if no date filter is strict
                                            pass
                                    
                                    coursework = date_filtered_coursework
                                    print(f"[Chatbot] After date filtering: {len(coursework)} assignments match the date(s)")
                                
                                # Apply "latest" filter if query asks for latest assignment(s)
                                is_latest_query = any(kw in query_lower for kw in ['latest', 'recent', 'newest', 'last'])
                                latest_count = 1  # Default to 1 if "latest" is mentioned
                                if is_latest_query:
                                    # Try to extract number (e.g., "latest 3", "latest 5 assignments")
                                    import re as re_module
                                    latest_match = re_module.search(r'latest\s+(\d+)|recent\s+(\d+)|newest\s+(\d+)|last\s+(\d+)', query_lower)
                                    if latest_match:
                                        latest_count = int(latest_match.group(1) or latest_match.group(2) or latest_match.group(3) or latest_match.group(4) or 1)
                                    
                                    if len(coursework) > latest_count:
                                        print(f"[Chatbot] Latest query detected - showing only {latest_count} most recent assignment(s)")
                                        # Sort by due date (most recent first) and take latest_count
                                        try:
                                            coursework_with_dates = []
                                            for c in coursework:
                                                due_date_str = c.get("dueDate") or c.get("due_date") or c.get("due")
                                                if due_date_str:
                                                    try:
                                                        if isinstance(due_date_str, str):
                                                            if 'T' in due_date_str:
                                                                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                                                            else:
                                                                due_date = datetime.strptime(due_date_str.split('T')[0], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                                                        else:
                                                            due_date = None
                                                        coursework_with_dates.append((c, due_date))
                                                    except:
                                                        coursework_with_dates.append((c, None))
                                                else:
                                                    coursework_with_dates.append((c, None))
                                            
                                            # Sort by due date (most recent first, None last)
                                            coursework_with_dates.sort(key=lambda x: x[1] if x[1] else datetime.min.replace(tzinfo=timezone.utc), reverse=True)
                                            coursework = [c for c, _ in coursework_with_dates[:latest_count]]
                                        except Exception as e:
                                            print(f"[Chatbot] Error sorting by date for latest query: {e}")
                                            # Fallback: just take first latest_count
                                            coursework = coursework[:latest_count]
                                
                                # If coursework data exists, include it
                                # Handle both data structures: from get_admin_data (has courseWorkId) and from get_student_coursework_data (has alternate_link directly)
                                filtered_course["coursework"] = []
                                for c in coursework:
                                    cw_item = {
                                        "title": c.get("title", ""),
                                    }
                                    # Include alternate_link if available (from get_student_coursework_data)
                                    if c.get("alternate_link"):
                                        cw_item["alternate_link"] = c.get("alternate_link")
                                    # Include other fields if available
                                    if c.get("courseWorkId"):
                                        cw_item["id"] = c.get("courseWorkId")
                                    if c.get("dueDate"):
                                        cw_item["due"] = c.get("dueDate")
                                    elif c.get("due_date"):
                                        cw_item["due"] = c.get("due_date")
                                    if c.get("state"):
                                        cw_item["status"] = c.get("state")
                                    if c.get("description"):
                                        cw_item["description"] = c.get("description")
                                    if c.get("work_type"):
                                        cw_item["work_type"] = c.get("work_type")
                                    filtered_course["coursework"].append(cw_item)
                            else:
                                # If no coursework data (restricted by Google), include course link for user to check
                                if course.get('course_link'):
                                    filtered_course["course_link"] = course.get('course_link')
                                filtered_course["coursework"] = []  # Empty array to indicate no data available
                                filtered_course["coursework_restricted"] = True  # Flag that data is restricted
                        
                        # Only add course if it has the requested data type
                        has_requested_data = False
                        if 'announcement' in query_type_priority and filtered_course.get('announcements'):
                            has_requested_data = True
                        elif 'student' in query_type_priority and filtered_course.get('students'):
                            has_requested_data = True
                        elif 'teacher' in query_type_priority and filtered_course.get('teachers'):
                            has_requested_data = True
                        elif 'coursework' in query_type_priority:
                            # Include course even if coursework is empty (will provide link/instructions)
                            has_requested_data = True
                        elif 'general' in query_type_priority:
                            has_requested_data = True  # General queries can include all
                        
                        if has_requested_data:
                            filtered_courses.append(filtered_course)
                    
                    # For coursework queries, add explicit assignment-to-link mapping FIRST (before JSON)
                    if is_coursework_query and filtered_courses:
                        user_content += "\n"
                        user_content += "=" * 80 + "\n"
                        user_content += "📋 CRITICAL: ASSIGNMENT-TO-LINK MAPPING - USE THESE EXACT LINKS!\n"
                        user_content += "=" * 80 + "\n"
                        user_content += "🚨 EACH ASSIGNMENT HAS A DIFFERENT LINK - DO NOT REUSE THE SAME LINK! 🚨\n\n"
                        user_content += "When you write about an assignment in your response, you MUST:\n"
                        user_content += "1. Find the assignment title in the list below\n"
                        user_content += "2. Copy the EXACT link shown next to that title\n"
                        user_content += "3. Use that link ONLY for that specific assignment\n"
                        user_content += "4. For the next assignment, find its title and use its DIFFERENT link\n\n"
                        user_content += "ASSIGNMENT MAPPING:\n"
                        user_content += "-" * 80 + "\n"
                        assignment_map = {}  # Store for validation
                        assignment_count = 0
                        for course in filtered_courses:
                            coursework_list = course.get('coursework', [])
                            if coursework_list:
                                user_content += f"\nCourse: {course.get('name', 'Unknown')}\n"
                                for cw in coursework_list:
                                    assignment_count += 1
                                    title = cw.get('title', 'Unknown').strip()
                                    alt_link = cw.get('alternate_link', '').strip()
                                    if alt_link:
                                        # Store for later reference
                                        assignment_map[title] = alt_link
                                        user_content += f"\n[{assignment_count}] ASSIGNMENT TITLE: \"{title}\"\n"
                                        user_content += f"    → ASSIGNMENT LINK: {alt_link}\n"
                                        user_content += f"    → WHEN YOU WRITE ABOUT \"{title}\", USE THIS EXACT LINK: {alt_link}\n"
                                    else:
                                        user_content += f"\n[{assignment_count}] ASSIGNMENT TITLE: \"{title}\"\n"
                                        user_content += f"    → ⚠️ WARNING: No link available\n"
                        user_content += "\n" + "-" * 80 + "\n"
                        user_content += "=" * 80 + "\n"
                        user_content += "⚠️ CRITICAL REMINDER:\n"
                        user_content += "- Assignment #1 uses Link #1 (shown above)\n"
                        user_content += "- Assignment #2 uses Link #2 (DIFFERENT from Link #1)\n"
                        user_content += "- Assignment #3 uses Link #3 (DIFFERENT from Link #1 and #2)\n"
                        user_content += "- And so on... EACH assignment gets its OWN unique link!\n"
                        user_content += "=" * 80 + "\n\n"
                    
                    # Check if there are any assignments in the data (before sending to LLM)
                    has_assignments = False
                    total_assignments = 0
                    if filtered_courses:
                        for course in filtered_courses:
                            coursework_list = course.get('coursework', [])
                            if coursework_list:
                                has_assignments = True
                                total_assignments += len(coursework_list)
                    
                    # Use compact JSON format to save tokens (minimal whitespace)
                    user_content += "Data:\n"
                    data_json = json.dumps(filtered_courses, separators=(',', ':'))
                    user_content += f"{data_json}\n"  # Compact format, no indentation
                    
                    # DEBUG: Log what data is being sent to LLM for coursework queries
                    if is_coursework_query:
                        print(f"[Chatbot] 🔍 DEBUG: Data being sent to LLM for coursework query:")
                        print(f"[Chatbot] 🔍 Number of courses: {len(filtered_courses)}")
                        print(f"[Chatbot] 🔍 Total assignments in data: {total_assignments}")
                        for idx, course in enumerate(filtered_courses):
                            coursework_list = course.get('coursework', [])
                            print(f"[Chatbot] 🔍 Course {idx + 1}: {course.get('name', 'Unknown')} - {len(coursework_list)} assignments")
                            for cw_idx, cw in enumerate(coursework_list[:5], 1):  # Show first 5
                                print(f"[Chatbot] 🔍   Assignment {cw_idx}: {cw.get('title', 'No title')}")
                                if cw.get('alternate_link'):
                                    print(f"[Chatbot] 🔍     Link: {cw.get('alternate_link')[:80]}...")
                        if len(filtered_courses) > 0 and len(filtered_courses[0].get('coursework', [])) > 5:
                            print(f"[Chatbot] 🔍   ... and {len(filtered_courses[0].get('coursework', [])) - 5} more assignments")
                        print(f"[Chatbot] 🔍 Data JSON length: {len(data_json)} characters")
                        print(f"[Chatbot] 🔍 First 500 chars of JSON: {data_json[:500]}...")
                    
                    # Add detailed instructions for coursework queries
                    if is_coursework_query:
                        if filtered_courses:
                            # If no assignments found after filtering, add explicit instruction
                            if not has_assignments or total_assignments == 0:
                                user_content += "\n" + "=" * 80 + "\n"
                                user_content += "🚨🚨🚨 CRITICAL: NO MATCHING ASSIGNMENTS FOUND! 🚨🚨🚨\n"
                                user_content += "=" * 80 + "\n"
                                user_content += "**THE DATA SECTION ABOVE HAS NO ASSIGNMENTS THAT MATCH THE USER'S QUERY.**\n"
                                user_content += "**YOU MUST TELL THE USER THAT NO MATCHING ASSIGNMENTS WERE FOUND.**\n"
                                user_content += "**🚨 ABSOLUTELY FORBIDDEN: DO NOT CREATE FAKE ASSIGNMENTS! 🚨**\n"
                                user_content += "**🚨 DO NOT SAY 'Here are your assignments' OR CREATE EXAMPLE ASSIGNMENTS! 🚨**\n"
                                user_content += "**YOU MUST SAY: 'I couldn't find any [subject] assignments in your courses.'**\n"
                                user_content += "=" * 80 + "\n\n"
                            else:
                                # Extract actual assignment titles from the data to show as examples
                                actual_assignment_titles = []
                                for course in filtered_courses:
                                    coursework_list = course.get('coursework', [])
                                    for cw in coursework_list:
                                        title = cw.get('title', '').strip()
                                        if title:
                                            actual_assignment_titles.append(title)
                                
                                # Add a section showing the actual assignment titles that MUST be used
                                if actual_assignment_titles:
                                    user_content += "\n" + "=" * 80 + "\n"
                                    user_content += "🚨🚨🚨 ACTUAL ASSIGNMENT TITLES FROM DATA - USE THESE EXACT TITLES! 🚨🚨🚨\n"
                                    user_content += "=" * 80 + "\n"
                                    user_content += "**THE FOLLOWING ARE THE ACTUAL ASSIGNMENT TITLES IN THE DATA ABOVE:**\n\n"
                                    for idx, title in enumerate(actual_assignment_titles[:10], 1):  # Show first 10
                                        user_content += f"{idx}. \"{title}\"\n"
                                    if len(actual_assignment_titles) > 10:
                                        user_content += f"... and {len(actual_assignment_titles) - 10} more assignments\n"
                                    user_content += "\n**🚨 YOU MUST USE THESE EXACT TITLES IN YOUR RESPONSE! 🚨**\n"
                                    user_content += "**🚨 DO NOT CREATE NEW TITLES LIKE 'Topic: Algebra' OR 'Topic: Geometry'! 🚨**\n"
                                    user_content += "**🚨 IF THE USER ASKS FOR 'MATHS' ASSIGNMENTS, FIND ALL TITLES CONTAINING 'Math', 'Maths', OR 'Mathematics' FROM THE LIST ABOVE! 🚨**\n"
                                    user_content += "**🚨 IF THE USER ASKS FOR 'ENGLISH' ASSIGNMENTS, FIND ALL TITLES CONTAINING 'ENGLISH' OR 'English' FROM THE LIST ABOVE! 🚨**\n"
                                    user_content += "=" * 80 + "\n\n"
                            user_content += "\n⚠️⚠️⚠️ COURSEWORK FORMATTING - CRITICAL INSTRUCTIONS: ⚠️⚠️⚠️\n"
                            user_content += "**ABSOLUTELY CRITICAL - READ CAREFULLY:**\n\n"
                            user_content += "**🚨🚨🚨 ABSOLUTELY FORBIDDEN: DO NOT CREATE FAKE ASSIGNMENTS! 🚨🚨🚨**\n"
                            user_content += "**🚨🚨🚨 YOU MUST USE ONLY THE ASSIGNMENTS FROM THE DATA SECTION ABOVE! 🚨🚨🚨**\n"
                            user_content += "**🚨🚨🚨 DO NOT GENERATE EXAMPLES LIKE 'Topic: Algebra' OR 'Topic: Literature Analysis'! 🚨🚨🚨**\n\n"
                            user_content += "**WHAT IS FORBIDDEN:**\n"
                            user_content += "- ❌ DO NOT create fake assignment titles like 'Solve equations' or 'Write an essay'\n"
                            user_content += "- ❌ DO NOT generate topics like 'Topic: Algebra', 'Topic: Literature Analysis'\n"
                            user_content += "- ❌ DO NOT create example problems or generic assignments\n"
                            user_content += "- ❌ DO NOT make up descriptions, due dates, or links\n"
                            user_content += "- ❌ DO NOT say 'Here are some example assignments' or 'I can help you with'\n\n"
                            user_content += "**WHAT IS MANDATORY:**\n"
                            user_content += "- ✅ Extract assignments from the 'coursework' array in the Data section above\n"
                            user_content += "- ✅ Use the EXACT 'title' field from each assignment object\n"
                            user_content += "- ✅ Use the EXACT 'description' field if available (do not make up descriptions)\n"
                            user_content += "- ✅ Use the EXACT 'due' or 'dueDate' field for due dates\n"
                            user_content += "- ✅ Use the EXACT 'alternate_link' field for each assignment's link\n"
                            user_content += "- ✅ Show ALL assignments that match the user's query (e.g., all English assignments if they ask for English)\n\n"
                            user_content += "**EXAMPLE OF CORRECT RESPONSE:**\n"
                            user_content += "If the Data section has: `{\"title\":\"CE-1 : ENGLISH : 16/12/2020 Wednesday till 03.00 pm\",\"alternate_link\":\"https://classroom.google.com/c/.../a/.../details\"}`\n"
                            user_content += "Then show: **CE-1 : ENGLISH : 16/12/2020 Wednesday till 03.00 pm**\n"
                            user_content += "Due: 16/12/2020, 03:00 PM\n"
                            user_content += "[View Assignment](https://classroom.google.com/c/.../a/.../details)\n\n"
                            user_content += "**EXAMPLE OF FORBIDDEN RESPONSE:**\n"
                            user_content += "❌ DO NOT show: 'Topic: Literature Analysis - Write an essay about...'\n"
                            user_content += "❌ DO NOT show: '1. Topic: Grammar - Identify errors...'\n\n"
                            user_content += "**🚨 USE THE DATA PROVIDED ABOVE - DO NOT ASK FOR MORE INFORMATION! 🚨**\n"
                            user_content += "**CRITICAL:** The user's assignments are ALREADY in the 'Data:' section above. You MUST use this data to answer their query. DO NOT ask them for more information - the data is already there!\n"
                            user_content += "**FORBIDDEN:** DO NOT say 'I would need more specific information' or 'Could you please provide' - the data is already provided above!\n"
                            user_content += "**MANDATORY:** Extract the assignments from the Data section and show them to the user immediately using ONLY the data from above.\n\n"
                            user_content += "**🚨 SHOW ALL ASSIGNMENTS - DO NOT LIMIT TO ONE! 🚨**\n"
                            user_content += "**MANDATORY:** You MUST list ALL assignments that match the user's query. If they ask for 'English assignments', show ALL English assignments from the data above. If they ask for 'my assignments', show ALL assignments available in the data. Only limit to one assignment if the user explicitly asks for 'one assignment' or 'latest 1 assignment'.\n\n"
                            user_content += "**🚨 CRITICAL RULE: EACH ASSIGNMENT HAS A DIFFERENT 'alternate_link' - DO NOT USE THE SAME URL FOR ALL ASSIGNMENTS! 🚨**\n\n"
                            user_content += "**EACH ASSIGNMENT IN THE 'coursework' ARRAY HAS ITS OWN UNIQUE 'alternate_link' FIELD!**\n"
                            user_content += "**YOU MUST MATCH EACH ASSIGNMENT TITLE WITH ITS CORRESPONDING 'alternate_link' FROM THE DATA JSON ABOVE!**\n"
                            user_content += "**DO NOT USE THE SAME URL FOR MULTIPLE ASSIGNMENTS - EACH ONE HAS A DIFFERENT LINK!**\n\n"
                            user_content += "**HOW TO EXTRACT THE LINK - MATCH BY TITLE:**\n"
                            user_content += "1. When you are about to write an assignment (e.g., 'CE-4 : Maths-1'), FIRST find that assignment in the 'Data:' section\n"
                            user_content += "2. Look for the assignment object where 'title' matches the assignment you're writing about\n"
                            user_content += "3. Once you find that specific assignment object, extract its EXACT 'alternate_link' value\n"
                            user_content += "4. Use that EXACT URL for THAT assignment only\n"
                            user_content += "5. When you move to the NEXT assignment, repeat steps 1-4 - find THAT assignment's alternate_link (which will be different!)\n"
                            user_content += "6. NEVER reuse a link from one assignment for another assignment!\n\n"
                            user_content += "**EXAMPLE DATA STRUCTURE (for reference only - use actual data from above):**\n"
                            user_content += "The data above shows assignments like:\n"
                            user_content += "{\"name\":\"Course\",\"coursework\":[{\"title\":\"Assignment 1\",\"alternate_link\":\"https://classroom.google.com/c/ABC123/a/XYZ789/details\"}]}\n\n"
                            user_content += "**FOR EACH ASSIGNMENT IN THE RESPONSE:**\n"
                            user_content += "1. **MANDATORY:** Look at the actual 'alternate_link' field in the assignment object from the Data section above\n"
                            user_content += "2. **MANDATORY:** Copy that EXACT URL value - do not modify it, do not create a new URL\n"
                            user_content += "3. **FORBIDDEN:** DO NOT use 'course_link' from the course object\n"
                            user_content += "4. **FORBIDDEN:** DO NOT create URLs with placeholder text like 'ASSIGNMENT_ID' or 'COURSE_ID'\n"
                            user_content += "5. **FORBIDDEN:** DO NOT use example URLs from these instructions\n\n"
                            user_content += "**CORRECT PROCESS:**\n"
                            user_content += "- If assignment data shows: `{\"title\":\"Math\",\"alternate_link\":\"https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjE5/details\"}`\n"
                            user_content += "- Then use: `[View Assignment](https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjE5/details)`\n"
                            user_content += "- Use the EXACT URL from the data, nothing else!\n\n"
                            user_content += "4. **Format each assignment with full details:**\n"
                            user_content += "   - Title (bold)\n"
                            user_content += "   - Description (if available)\n"
                            user_content += "   - Due Date and Time (format dates nicely)\n"
                            user_content += "   - Max Points (if available)\n"
                            user_content += "   - Work Type (ASSIGNMENT, MATERIAL, etc.)\n"
                            user_content += "   - Submission Status (if submission_state is available: NEW, TURNED_IN, RETURNED, etc.)\n"
                            user_content += "   - Grade (if assigned_grade or draft_grade is available)\n"
                            user_content += "   - **Direct Assignment Link** using the assignment's `alternate_link` field\n\n"
                            user_content += "6. **Format Template:**\n"
                            user_content += "   ### [Course Name]\n\n"
                            user_content += "   #### 📋 [Assignment Title]\n"
                            user_content += "   **Description:** [description]\n"
                            user_content += "   **Due Date:** [due_date] at [due_time]\n"
                            user_content += "   **Points:** [max_points]\n"
                            user_content += "   **Type:** [work_type]\n"
                            user_content += "   **Status:** [submission_state] | **Grade:** [assigned_grade or draft_grade]\n"
                            user_content += "   **[View Assignment](COPY_THE_EXACT_alternate_link_VALUE_FROM_THIS_SPECIFIC_ASSIGNMENT_OBJECT)**\n"
                            user_content += "   ⚠️ CRITICAL: For the assignment title above, find that EXACT assignment in the Data section and use ITS 'alternate_link'.\n"
                            user_content += "   ⚠️ DO NOT reuse the same link for different assignments - each assignment has its own unique alternate_link!\n\n"
                            user_content += "7. **If coursework is empty for a course:** Only then use course_link with instructions\n"
                            user_content += "8. **Group assignments by course** and show all available details\n"
                            user_content += "9. **For 'latest assignment' queries:** Show the most recent assignment first (sorted by due_date)\n"
                            user_content += "10. **CRITICAL - SHOW ALL ASSIGNMENTS:** When user asks for assignments (e.g., 'English assignments', 'my assignments'), you MUST show ALL matching assignments from the data, not just one. List every assignment that matches the query criteria. If user asks for 'English assignments', show ALL assignments with 'ENGLISH' or 'English' in the title. If user asks for 'my assignments', show ALL assignments available in the coursework data.\n"
                            user_content += "11. **DO NOT LIMIT TO ONE ASSIGNMENT:** Unless the user specifically asks for 'latest 1 assignment' or 'one assignment', always show all available assignments that match their query.\n"
                            user_content += "12. **START YOUR RESPONSE IMMEDIATELY WITH THE ASSIGNMENTS:** Do NOT start with greetings or asking for more information. If the Data section contains assignments, START your response by listing those assignments. The user's assignments are in the Data section - use them NOW!\n\n"
                            user_content += "**CRITICAL - MATCHING EACH ASSIGNMENT WITH ITS LINK:**\n"
                            user_content += "**EACH ASSIGNMENT HAS A DIFFERENT 'alternate_link' - YOU MUST MATCH THEM CORRECTLY!**\n\n"
                            user_content += "**STEP-BY-STEP PROCESS FOR EACH ASSIGNMENT:**\n"
                            user_content += "1. Look at the 'ASSIGNMENT-TO-LINK MAPPING' section at the TOP of this prompt (before the Data section)\n"
                            user_content += "2. When you write an assignment title (e.g., 'CE-4 : Maths-1'), find that EXACT title in the mapping\n"
                            user_content += "3. Copy the EXACT link shown next to that title (it will say 'USE THIS LINK: ...')\n"
                            user_content += "4. Use that EXACT link for THAT assignment only\n"
                            user_content += "5. When you write the next assignment (e.g., 'Final Assignment: ES'), find THAT title in the mapping\n"
                            user_content += "6. Copy the EXACT link shown next to THAT title (it will be DIFFERENT from the previous one!)\n"
                            user_content += "7. Use that EXACT link for THAT assignment only\n"
                            user_content += "8. NEVER reuse a link - each assignment has its own unique link in the mapping!\n\n"
                            user_content += "**EXAMPLE OF CORRECT BEHAVIOR:**\n"
                            user_content += "If the mapping shows:\n"
                            user_content += "  1. Title: 'Assignment A' → Link: https://classroom.google.com/c/123/a/AAA/details\n"
                            user_content += "  2. Title: 'Assignment B' → Link: https://classroom.google.com/c/123/a/BBB/details\n"
                            user_content += "  3. Title: 'Assignment C' → Link: https://classroom.google.com/c/123/a/CCC/details\n\n"
                            user_content += "Then in your response:\n"
                            user_content += "- When you write 'Assignment A', use: https://classroom.google.com/c/123/a/AAA/details\n"
                            user_content += "- When you write 'Assignment B', use: https://classroom.google.com/c/123/a/BBB/details\n"
                            user_content += "- When you write 'Assignment C', use: https://classroom.google.com/c/123/a/CCC/details\n\n"
                            user_content += "**WRONG:** Using https://classroom.google.com/c/123/a/AAA/details for all assignments\n"
                            user_content += "**RIGHT:** Each assignment gets its own matching link from the mapping above\n\n"
                            
                            # Final explicit instruction with actual examples
                            if actual_assignment_titles:
                                user_content += "\n" + "=" * 80 + "\n"
                                user_content += "🚨🚨🚨 FINAL INSTRUCTION - YOUR RESPONSE MUST LOOK LIKE THIS: 🚨🚨🚨\n"
                                user_content += "=" * 80 + "\n"
                                user_content += "**IF USER ASKS FOR MATHS ASSIGNMENTS, YOUR RESPONSE MUST START WITH:**\n\n"
                                # Find math assignments from actual titles
                                math_titles = [t for t in actual_assignment_titles if any(kw in t.upper() for kw in ['MATH', 'MATHS', 'MATHEMATICS'])]
                                if math_titles:
                                    user_content += "### Maths Assignments:\n\n"
                                    for idx, title in enumerate(math_titles[:3], 1):
                                        user_content += f"{idx}. **{title}**\n"
                                        user_content += "   [View Assignment](USE_THE_EXACT_alternate_link_FROM_DATA_FOR_THIS_TITLE)\n\n"
                                    user_content += "**NOT LIKE THIS (FORBIDDEN):**\n"
                                    user_content += "❌ 1. **Topic: Geometry Shapes**\n"
                                    user_content += "❌ 2. **Topic: Fractions and Decimals**\n\n"
                                user_content += "**IF USER ASKS FOR ENGLISH ASSIGNMENTS, YOUR RESPONSE MUST START WITH:**\n\n"
                                # Find English assignments from actual titles
                                english_titles = [t for t in actual_assignment_titles if 'ENGLISH' in t.upper()]
                                if english_titles:
                                    user_content += "### English Assignments:\n\n"
                                    for idx, title in enumerate(english_titles[:3], 1):
                                        user_content += f"{idx}. **{title}**\n"
                                        user_content += "   [View Assignment](USE_THE_EXACT_alternate_link_FROM_DATA_FOR_THIS_TITLE)\n\n"
                                    user_content += "**NOT LIKE THIS (FORBIDDEN):**\n"
                                    user_content += "❌ 1. **Topic: Literature Analysis**\n"
                                    user_content += "❌ 2. **Topic: Grammar**\n\n"
                                user_content += "**IF USER ASKS FOR BME ASSIGNMENTS, YOUR RESPONSE MUST START WITH:**\n\n"
                                # Find BME assignments from actual titles
                                bme_titles = [t for t in actual_assignment_titles if 'BME' in t.upper()]
                                if bme_titles:
                                    user_content += "### BME Assignments:\n\n"
                                    for idx, title in enumerate(bme_titles[:3], 1):
                                        user_content += f"{idx}. **{title}**\n"
                                        user_content += "   [View Assignment](USE_THE_EXACT_alternate_link_FROM_DATA_FOR_THIS_TITLE)\n\n"
                                    user_content += "**NOT LIKE THIS (FORBIDDEN):**\n"
                                    user_content += "❌ 1. **Assignment 1: Human Anatomy Project**\n"
                                    user_content += "❌ 2. **Assignment 2: Health and Wellness Essay**\n\n"
                                user_content += "**IF USER ASKS FOR OOPU ASSIGNMENTS, YOUR RESPONSE MUST START WITH:**\n\n"
                                # Find OOPU assignments from actual titles
                                oopu_titles = [t for t in actual_assignment_titles if any(kw in t.upper() for kw in ['OOPU', 'OOP-U', 'OOP U'])]
                                if oopu_titles:
                                    user_content += "### OOPU Assignments:\n\n"
                                    for idx, title in enumerate(oopu_titles[:3], 1):
                                        user_content += f"{idx}. **{title}**\n"
                                        user_content += "   [View Assignment](USE_THE_EXACT_alternate_link_FROM_DATA_FOR_THIS_TITLE)\n\n"
                                    user_content += "**NOT LIKE THIS (FORBIDDEN):**\n"
                                    user_content += "❌ 1. **Topic: Object-Oriented Programming**\n"
                                    user_content += "❌ 2. **Assignment: Classes and Objects**\n\n"
                                user_content += "**🚨 REMEMBER: Use the EXACT titles from the 'ACTUAL ASSIGNMENT TITLES' section above! 🚨**\n"
                                user_content += "**🚨 DO NOT create new titles or topics! 🚨**\n"
                                user_content += "**🚨 FOR ANY SUBJECT (BME, OOPU, PPS, BE, ES, etc.), USE ONLY THE EXACT TITLES FROM THE DATA! 🚨**\n"
                                user_content += "=" * 80 + "\n\n"
                        else:
                            user_content += "\n⚠️ NO COURSES FOUND: Say user has no courses matching their grade, suggest contacting teacher.\n\n"
                    
                    # Add specific instructions for teacher/student queries with email requests
                    if (is_teacher_query or is_student_query) and ('email' in user_query.lower() or 'emails' in user_query.lower()):
                        user_content += "\n⚠️⚠️⚠️ CRITICAL INSTRUCTIONS FOR TEACHER/STUDENT EMAILS: ⚠️⚠️⚠️\n"
                        user_content += "**ABSOLUTELY FORBIDDEN:**\n"
                        user_content += "- DO NOT say 'as an AI', 'I'm sorry but as an AI', 'for privacy reasons', 'I'm committed to respecting privacy', or any similar AI disclaimers\n"
                        user_content += "- DO NOT mention that you are an AI assistant in this context\n"
                        user_content += "- Respond as if you are directly accessing the school's database\n\n"
                        user_content += "**REQUIRED ACTIONS:**\n"
                        user_content += "1. Check each teacher/student object above for an 'email' field.\n"
                        user_content += "2. If the 'email' field exists and has a value, YOU MUST INCLUDE IT in your response.\n"
                        user_content += "3. If no 'email' field exists or it's empty for a specific person, simply write 'N/A' in the email column.\n"
                        user_content += "4. **ALWAYS format teacher/student lists as Markdown tables** for better readability:\n"
                        user_content += "   - Use: | Name | ID | Email |\n"
                        user_content += "   - Separate header with: |---|---|---|\n"
                        user_content += "   - Each row: | Teacher/Student Name | ID | Email (or 'N/A' if not available) |\n"
                        user_content += "5. Start your response directly with the table - no apologies, no disclaimers, just the information.\n"
                        user_content += "6. Example format:\n"
                        user_content += "   Here are the teachers for [Course Name]:\n\n"
                        user_content += "   | Name | ID | Email |\n"
                        user_content += "   |---|---|---|\n"
                        user_content += "   | Teacher Name | 123456 | teacher@example.com |\n\n\n"
                    elif is_teacher_query or is_student_query:
                        # Even without email request, format as table for better presentation
                        user_content += "\n⚠️⚠️⚠️ CRITICAL INSTRUCTIONS FOR TEACHER/STUDENT QUERIES: ⚠️⚠️⚠️\n"
                        user_content += "**ABSOLUTELY FORBIDDEN:**\n"
                        user_content += "- DO NOT send greetings like 'I see that you are a student in Grade X' when user asks for data\n"
                        user_content += "- DO NOT say 'How can I assist you today?' when user asks for specific data (lists, existence checks)\n"
                        user_content += "- DO NOT provide general responses when user asks for specific classroom data\n\n"
                        user_content += "**REQUIRED ACTIONS:**\n"
                        user_content += "1. **For list queries** (e.g., 'I want my classmate list', 'show me teachers'):\n"
                        user_content += "   - IMMEDIATELY check the Data section above for student/teacher lists\n"
                        user_content += "   - Extract ALL students/teachers from the data\n"
                        user_content += "   - Format as Markdown table: | Name | ID |\n"
                        user_content += "   - Start your response directly with the table - NO greetings, NO introductions\n"
                        user_content += "   - If no data found, say 'No students/teachers found in your courses.'\n\n"
                        user_content += "2. **For existence check queries** (e.g., 'check if student X exists', 'does Y exist'):\n"
                        user_content += "   - IMMEDIATELY search the Data section above for the specific name\n"
                        user_content += "   - Check ALL student/teacher lists in ALL courses\n"
                        user_content += "   - If found: Respond with 'YES, [Name] exists as a [student/teacher] in [Course Name].'\n"
                        user_content += "   - If NOT found: Respond with 'NO, [Name] does not exist in your courses.'\n"
                        user_content += "   - Start your response directly with YES/NO - NO greetings, NO introductions\n\n"
                        user_content += "3. **ALWAYS format teacher/student lists as Markdown tables** for better readability.\n"
                        user_content += "   - Use format: | Name | ID |\n"
                        user_content += "   - Separate header with: |---|---|\n"
                        user_content += "   - Each row: | Teacher/Student Name | ID |\n"
                        user_content += "   - If email was not requested, don't include it in the table.\n\n"
                        user_content += "**EXAMPLES OF CORRECT BEHAVIOR:**\n"
                        user_content += "- User: 'I want my classmate list'\n"
                        user_content += "  Response: | Name | ID |\n|---|---|\n| Student 1 | 123 |\n| Student 2 | 456 |\n\n"
                        user_content += "- User: 'Check if John exists'\n"
                        user_content += "  Response: YES, John exists as a student in Math Class.\n\n"
                        user_content += "- User: 'I want my teacher list'\n"
                        user_content += "  Response: | Name | ID |\n|---|---|\n| Teacher 1 | 789 |\n| Teacher 2 | 012 |\n\n"
                    
                    # Add concise formatting instructions for announcements (TOKEN OPTIMIZATION - reduced from ~60 lines to ~5 lines)
                    if is_announcement_query:
                        user_content += "\n⚠️ ANNOUNCEMENTS:\n"
                        user_content += "Format: ### [Date]\n**Announcement:** [text]\nSchedule:\n- [time] to [time]: [activity]\n[View Full Announcement](url)\n"
                        user_content += "Fix time ranges (add 'to' between times), grammar, use Markdown. Process data, don't copy-paste.\n"
                        user_content += "If empty: Say 'No announcements for requested date(s)'.\nDO NOT say 'no access'!\n\n"
                    
                if admin_data.get('calendar_data') and (is_calendar_query or is_event_query):
                    # Include calendar for both calendar and event queries
                    calendar_events = admin_data.get('calendar_data', [])[:20]
                    print(f"[Chatbot] 📋 Formatting {len(calendar_events)} calendar events for AI prompt")
                    for idx, e in enumerate(calendar_events):
                        print(f"[Chatbot]   Event {idx+1}: {e.get('summary', 'Unknown')} on {e.get('startTime', 'No date')}")
                    if calendar_events:
                        # Format events with clear date information
                        user_content += "\n📅 **UPCOMING CALENDAR EVENTS (REAL DATA FROM SCHOOL CALENDAR):**\n"
                        user_content += "⚠️ CRITICAL: The events listed below are ALREADY filtered for the user's requested date/query.\n"
                        user_content += "If you see events listed below, they MATCH the user's query and you MUST mention them in your response!\n"
                        user_content += "DO NOT say 'no events' if events are listed below - they ARE the answer to the user's question!\n\n"
                        for e in calendar_events:
                            title = e.get("summary", "")
                            start_time = e.get("startTime", "")
                            
                            # Parse date from ISO format (e.g., "2026-02-21T00:00:00")
                            event_date_str = ""
                            event_date_obj = None
                            if start_time:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                    # Format as readable date
                                    event_date_str = dt.strftime("%B %d, %Y")  # e.g., "February 21, 2026"
                                    event_date_obj = dt.date()
                                except:
                                    event_date_str = start_time.split('T')[0]  # Fallback to YYYY-MM-DD
                            
                            # Also include day of week and week number for better filtering
                            day_of_week = ""
                            week_info = ""
                            if event_date_obj:
                                try:
                                    day_of_week = event_date_obj.strftime("%A")  # Monday, Tuesday, etc.
                                    # Calculate week of month (1st week = days 1-7, 2nd week = 8-14, etc.)
                                    week_num = (event_date_obj.day - 1) // 7 + 1
                                    week_names = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
                                    week_info = f" ({week_names.get(week_num, '')} week of {event_date_obj.strftime('%B')})"
                                except:
                                    pass
                            
                            user_content += f"- **{title}**: {event_date_str}{day_of_week and f' ({day_of_week})' or ''}{week_info}\n"
                        user_content += "\n⚠️ CRITICAL RULES:\n"
                        user_content += "1. ONLY list events from the calendar above. DO NOT invent, make up, or generate fake events!\n"
                        user_content += "2. When asked about specific dates (e.g., 'when is sports day', 'events on 21st feb'), you MUST list ALL events shown above that match that date.\n"
                        user_content += "3. The events listed above are ALREADY filtered for the requested date - if you see events above, they ARE on the requested date!\n"
                        user_content += "4. When asked about weeks (e.g., 'first week of April'), only show events that actually fall in that week from the calendar above.\n"
                        user_content += "5. If the calendar above shows events, you MUST mention them in your response. Do NOT say 'no events' if events are listed above!\n"
                        user_content += "6. Do NOT say 'the date can vary' or 'check with your teacher' - provide the actual date from the calendar data.\n"
                        user_content += "7. Do NOT include event type (sports, festival, upcoming) in your response - just show the event name and date.\n\n"
            
            # Add detailed data processing instructions for coursework
            if is_coursework_query:
                user_content += "\n⚠️ FORMATTING REQUIREMENTS FOR COURSEWORK:\n"
                user_content += "1. **Always format dates** in readable format (e.g., 'January 15, 2024' or '15 Jan 2024')\n"
                user_content += "2. **Always format times** in readable format (e.g., '3:30 PM')\n"
                user_content += "3. **Use proper Markdown** for headings, bold text, and links\n"
                user_content += "4. **Include all available information** - don't skip fields\n"
                user_content += "5. **Make it visually appealing** with proper spacing and structure\n"
                user_content += "6. **CRITICAL: For each assignment, use the assignment's 'alternate_link' field** - NOT the course_link!\n"
                user_content += "   - Assignment links look like: https://classroom.google.com/c/COURSE_ID/a/ASSIGNMENT_ID/details\n"
                user_content += "   - Course links look like: https://classroom.google.com/c/COURSE_ID (DO NOT USE THIS FOR ASSIGNMENTS!)\n\n"
            elif is_announcement_query:
                user_content += "\n⚠️ FORMATTING: Process data intelligently. Fix time ranges, grammar, use Markdown. Make readable.\n\n"
            
            # CRITICAL: For person queries, verify against actual teacher/student lists but still provide web data
            if should_use_web_crawling_first or (is_person_detail_query and admin_data.get('classroom_data')):
                user_content += "\n⚠️ PERSON INFORMATION - STRICT RULES:\n"
                user_content += "1. Provide general information about the person from Web data (background, role at school, etc.).\n"
                user_content += "2. For CURRENT teacher/student status: ONLY confirm if their name EXACTLY appears in the Classroom Data teacher/student lists.\n"
                user_content += "3. DO NOT make assumptions like 'based on the current classroom data, X is associated with course Y' unless X is explicitly listed in the teacher list for that course.\n"
                user_content += "4. DO NOT infer teacher status from course names, course associations, or any indirect references.\n"
                user_content += "5. If Web data provides general information but the person is NOT in the current Classroom teacher list, provide the general info from Web and add: 'However, they are not currently listed as a teacher for your grade/course in the Classroom data.'\n"
                user_content += "6. NEVER say 'based on the current classroom data, X is associated with...' unless X's name appears in the teacher list.\n\n"
            
            # Add special instructions for translation/reference queries
            if is_translation_query:
                user_content += "\n⚠️ TRANSLATION/REFERENCE QUERY:\n"
                user_content += "- User wants to translate or get a previous response in a different language.\n"
                user_content += "- If they said 'below response', 'previous response', 'that response', or 'last response', they mean the LAST ASSISTANT RESPONSE in the conversation history above.\n"
                user_content += "- Find that previous response in the conversation history and translate it to the requested language (Gujarati/Hindi/etc).\n"
                user_content += "- If you can't find a clear previous response, ask for clarification.\n\n"
            
            user_content += "Provide a complete, helpful answer."
            
            # Estimate token count (rough: 1 token ≈ 4 characters)
            estimated_tokens = len(user_content) // 4 + sum(len(msg["content"]) // 4 for msg in messages)
            print(f"[Chatbot] 📊 Estimated token count: ~{estimated_tokens} tokens")
            print(f"[Chatbot] 📊 User content length: {len(user_content)} chars | Messages count: {len(messages)}")
            
            # If too large, use a more compact format
            if estimated_tokens > 6000:  # Leave room for response
                print("[Chatbot] Token count too high, using compact format...")
                # Create a more compact version
                compact_content = f"Question: {user_query}\n\n"
                if admin_data.get('classroom_data'):
                    # Only include essential data
                    # First, collect all announcements across all courses to check if any exist
                    all_announcements_found = False
                    courses_with_announcements = []
                    
                    for course in admin_data['classroom_data']:
                        if is_announcement_query:
                            announcements = course.get('announcements', [])
                            if target_date_ranges:
                                # Filter for specific date(s) (today, yesterday, or specific dates)
                                filtered_ann = []
                                for ann in announcements:
                                    update_time_str = ann.get('updateTime', '')
                                    if update_time_str:
                                        try:
                                            update_time = datetime.fromisoformat(update_time_str.replace('Z', '+00:00'))
                                            if update_time.tzinfo is None:
                                                update_time = update_time.replace(tzinfo=timezone.utc)
                                            # Check if announcement matches any of the target dates
                                            for date_start, date_end in target_date_ranges:
                                                if date_start <= update_time <= date_end:
                                                    filtered_ann.append(ann)
                                                    break
                                        except:
                                            pass
                                announcements = filtered_ann
                            else:
                                announcements = sorted(announcements, key=lambda x: x.get('updateTime', ''), reverse=True)[:5]
                            
                            if announcements:
                                all_announcements_found = True
                                courses_with_announcements.append({
                                    'name': course.get('name', ''),
                                    'announcements': announcements
                                })
                    
                    # Now build compact_content - only include courses with announcements
                    # If no announcements found, don't add "No announcements" here - let LLM decide
                    for course_data in courses_with_announcements:
                        compact_content += f"\nCourse: {course_data['name']}\n"
                        compact_content += "Announcements:\n"
                        for ann in course_data['announcements']:
                            url = ann.get('url') or ann.get('alternateLink', '')
                            compact_content += f"- {ann.get('text', '')[:150]} (Updated: {ann.get('updateTime', '')[:10]})"
                            if url:
                                compact_content += f" [URL: {url}]\n"
                            else:
                                compact_content += "\n"
                compact_content += "\nUse the data above to answer the question."
                messages.append({"role": "user", "content": compact_content})
            else:
                messages.append({"role": "user", "content": user_content})
            
            # MODEL SELECTION: Always use GPT-3.5-turbo for all queries to reduce costs
            # GPT-3.5-turbo: Used for all queries (data-enhanced and general queries) for cost optimization
            has_structured_data = False
            data_sources = []
            
            # Check if we have structured data to work with
            if admin_data.get('classroom_data') and len(admin_data.get('classroom_data', [])) > 0:
                has_structured_data = True
                data_sources.append("Classroom")
            
            if admin_data.get('calendar_data') and len(admin_data.get('calendar_data', [])) > 0:
                has_structured_data = True
                data_sources.append("Calendar")
            
            if web_enhanced_info and len(web_enhanced_info.strip()) > 50:  # Meaningful web data
                has_structured_data = True
                data_sources.append("Web")
            
            # Use GPT-4o-mini as the default model (better performance than GPT-3.5-turbo)
            model_name = get_default_gpt_model()  # Using GPT-4o-mini for better performance
            model_display_name = "GPT-4o-mini" if model_name == "gpt-4o-mini" else model_name

            if has_structured_data:
                print(f"[Chatbot] 🤖 MODEL SELECTION: {model_display_name} (Data-Enhanced Query)")
                print(f"[Chatbot] 📊 Data sources available: {', '.join(data_sources)}")
                print(f"[Chatbot] 💰 Cost: ~$0.0015-0.002 per query (GPT-4o-mini provides excellent performance)")
            else:
                print(f"[Chatbot] 🤖 MODEL SELECTION: {model_display_name} (General Query)")
                print(f"[Chatbot] 💰 Cost: ~$0.0015-0.002 per query (GPT-4o-mini for all queries)")

            # Model selection already logged at function level - proceeding with response generation

            if model_name == "gpt-4o-mini":
                print(f"[Chatbot] 💰 COST: GPT-4o-mini pricing - Input: $0.00015/1K tokens, Output: $0.0006/1K tokens")
                print(f"[Chatbot] ⚡ PERFORMANCE: High-quality responses with 80% cost savings vs GPT-3.5-turbo")
            elif model_name == "gpt-3.5-turbo":
                print(f"[Chatbot] 💰 COST: GPT-3.5-turbo pricing - Input: $0.0015/1K tokens, Output: $0.002/1K tokens")
                print(f"[Chatbot] ⚡ PERFORMANCE: Standard responses (fallback mode)")
            else:
                print(f"[Chatbot] 💰 COST: GPT-4 pricing - Input: $0.03/1K tokens, Output: $0.06/1K tokens")
                print(f"[Chatbot] ⚡ PERFORMANCE: Maximum quality responses")

            response = openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,
            )

            # ✅ RESPONSE CONFIRMATION LOGGING
            print(f"[Chatbot] ✅ RESPONSE GENERATED: Successfully used {model_name.upper()}")
            if hasattr(response, 'model') and response.model:
                actual_model = response.model.upper()
                print(f"[Chatbot] 🎯 OPENAI CONFIRMED: Response generated with {actual_model}")
                # Check if actual model starts with requested model (handles version suffixes like gpt-4o-mini-2024-07-18)
                if not actual_model.startswith(model_name.upper()):
                    print(f"[Chatbot] ⚠️ MODEL MISMATCH: Requested {model_name.upper()} but OpenAI used {actual_model}")
                else:
                    print(f"[Chatbot] ✅ MODEL VERIFIED: OpenAI confirmed using {actual_model} (matches {model_name.upper()})")
            else:
                print(f"[Chatbot] 📝 RESPONSE: Generated with model {model_name.upper()} (confirmation not available)")
            
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            # Calculate token usage from response (approximate)
            input_tokens_approx = sum(len(msg["content"]) // 4 for msg in messages)
            output_tokens_approx = len(content) // 4 if content else 0
            
            # Calculate cost based on model used
            if model_name == "gpt-4o-mini":
                estimated_cost = (input_tokens_approx * 0.00015 / 1000) + (output_tokens_approx * 0.0006 / 1000)
                cost_model = "GPT-4o-mini"
            elif model_name == "gpt-3.5-turbo":
                estimated_cost = (input_tokens_approx * 0.0015 / 1000) + (output_tokens_approx * 0.002 / 1000)
                cost_model = "GPT-3.5-turbo"
            else:  # GPT-4
                estimated_cost = (input_tokens_approx * 0.03 / 1000) + (output_tokens_approx * 0.06 / 1000)
                cost_model = "GPT-4"
            
            print(f"[Chatbot] 📊 Attempt {attempt + 1} - Response generated")
            print(f"[Chatbot] 📏 Response length: {len(content) if content else 0} characters")
            print(f"[Chatbot] 📏 Estimated tokens: ~{input_tokens_approx} input + ~{output_tokens_approx} output = ~{input_tokens_approx + output_tokens_approx} total")
            print(f"[Chatbot] 💰 Estimated cost: ~${estimated_cost:.4f} ({cost_model})")
            # Show cost comparison and savings
            if model_name == "gpt-4o-mini":
                gpt35_cost = (input_tokens_approx * 0.0015 / 1000) + (output_tokens_approx * 0.002 / 1000)
                savings = gpt35_cost - estimated_cost
                print(f"[Chatbot] 💵 SAVINGS: ~${savings:.4f} vs GPT-3.5-turbo (${gpt35_cost:.4f})")
            elif model_name == "gpt-3.5-turbo":
                gpt4o_mini_cost = (input_tokens_approx * 0.00015 / 1000) + (output_tokens_approx * 0.0006 / 1000)
                savings = estimated_cost - gpt4o_mini_cost
                print(f"[Chatbot] 💡 UPGRADE OPPORTUNITY: Save ~${savings:.4f} by using GPT-4o-mini (${gpt4o_mini_cost:.4f})")

            print(f"[Chatbot] 🤖 FINAL CONFIRMATION: Response generated using {model_name.upper()}")
            print(f"[Chatbot] ✅ Finish reason: {finish_reason}")
            print(f"[Chatbot] 🎯 MODEL VERIFICATION COMPLETE")
            
            # Log model confirmation
            if hasattr(response, 'model') and response.model:
                print(f"[Chatbot] ✅ DEBUG: OpenAI confirmed model used: {response.model}")
            
            # Check if response is complete
            if content and finish_reason == "stop" and not content.strip().endswith(("of", "and", "the", "in", "to", "for", "with", "by")):
                print(f"[Chatbot] Complete response received on attempt {attempt + 1}")
                
                # VALIDATION: For coursework queries, check if response contains actual assignment titles
                if is_coursework_query and admin_data.get('classroom_data'):
                    print(f"[Chatbot] 🔍 VALIDATION: Checking response for actual assignment titles...")
                    
                    # Re-apply subject filtering to match what was sent to LLM
                    query_upper = user_query.upper()
                    subject_keywords = []
                    
                    # Common subject patterns (same as pre-filtering logic) - using word boundaries
                    if re.search(r'\b(BME|BIOMEDICAL|BIOMED)\b', query_upper):
                        subject_keywords.extend(['BME'])
                    if re.search(r'\b(OOPU|OOP-U|OOP\s+U)\b', query_upper):
                        subject_keywords.extend(['OOPU', 'OOP-U', 'OOP U'])
                    if re.search(r'\b(ENGLISH|ENG)\b', query_upper):
                        subject_keywords.extend(['ENGLISH', 'ENG'])
                    if re.search(r'\b(MATH|MATHS|MATHEMATICS)\b', query_upper):
                        subject_keywords.extend(['MATH', 'MATHS', 'MATHEMATICS', 'MATHEMATICS-1', 'MATHS-1'])
                    if re.search(r'\b(PPS|PROGRAMMING)\b', query_upper):
                        subject_keywords.extend(['PPS'])
                    if re.search(r'\b(BE|BASIC\s+ENGINEERING)\b', query_upper):
                        subject_keywords.extend(['BE'])
                    # ES must be a standalone word, not part of "assignment" or other words
                    if re.search(r'\b(ES|ENVIRONMENTAL)\b', query_upper):
                        subject_keywords.extend(['ES'])
                    
                    # Extract filtered assignment titles (only matching subject, date, and latest)
                    actual_titles = []
                    assignment_map = {}  # title -> alternate_link
                    filtered_coursework_for_validation = []
                    
                    # Detect "latest" query
                    is_latest_query = any(kw in query_lower for kw in ['latest', 'recent', 'newest', 'last'])
                    latest_count = 1  # Default to 1 if "latest" is mentioned
                    if is_latest_query:
                        import re as re_module
                        latest_match = re_module.search(r'latest\s+(\d+)|recent\s+(\d+)|newest\s+(\d+)|last\s+(\d+)', query_lower)
                        if latest_match:
                            latest_count = int(latest_match.group(1) or latest_match.group(2) or latest_match.group(3) or latest_match.group(4) or 1)
                    
                    for course in admin_data.get('classroom_data', []):
                        coursework_list = course.get('coursework', [])
                        temp_filtered = []
                        
                        # First filter by subject
                        if subject_keywords:
                            for cw in coursework_list:
                                title = cw.get('title', '').strip()
                                title_upper = title.upper()
                                if any(kw in title_upper for kw in subject_keywords):
                                    temp_filtered.append(cw)
                        else:
                            temp_filtered = coursework_list
                        
                        # Then filter by date if specified
                        if target_date_ranges and len(temp_filtered) > 0:
                            from datetime import datetime, timezone
                            date_filtered = []
                            for cw in temp_filtered:
                                due_date_str = cw.get("dueDate") or cw.get("due_date") or cw.get("due")
                                if due_date_str:
                                    try:
                                        if isinstance(due_date_str, str):
                                            if 'T' in due_date_str:
                                                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                                            else:
                                                due_date = datetime.strptime(due_date_str.split('T')[0], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                                        else:
                                            continue
                                        
                                        matches_date = False
                                        for date_start, date_end in target_date_ranges:
                                            if date_start <= due_date <= date_end:
                                                matches_date = True
                                                break
                                        
                                        if matches_date:
                                            date_filtered.append(cw)
                                    except:
                                        pass
                            temp_filtered = date_filtered
                        
                        # Then apply "latest" filter if specified
                        if is_latest_query and len(temp_filtered) > latest_count:
                            from datetime import datetime, timezone
                            try:
                                coursework_with_dates = []
                                for cw in temp_filtered:
                                    due_date_str = cw.get("dueDate") or cw.get("due_date") or cw.get("due")
                                    if due_date_str:
                                        try:
                                            if isinstance(due_date_str, str):
                                                if 'T' in due_date_str:
                                                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                                                else:
                                                    due_date = datetime.strptime(due_date_str.split('T')[0], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                                            else:
                                                due_date = None
                                            coursework_with_dates.append((cw, due_date))
                                        except:
                                            coursework_with_dates.append((cw, None))
                                    else:
                                        coursework_with_dates.append((cw, None))
                                
                                coursework_with_dates.sort(key=lambda x: x[1] if x[1] else datetime.min.replace(tzinfo=timezone.utc), reverse=True)
                                temp_filtered = [c for c, _ in coursework_with_dates[:latest_count]]
                            except:
                                temp_filtered = temp_filtered[:latest_count]
                        
                        # Add to final list
                        for cw in temp_filtered:
                            title = cw.get('title', '').strip()
                            if title:
                                actual_titles.append(title)
                                filtered_coursework_for_validation.append(cw)
                                if cw.get('alternate_link'):
                                    assignment_map[title] = cw.get('alternate_link')
                    
                    print(f"[Chatbot] 🔍 VALIDATION: Found {len(actual_titles)} actual assignment titles in data")
                    print(f"[Chatbot] 🔍 VALIDATION: Sample titles: {actual_titles[:3]}")
                    
                    # Check if response contains any actual assignment titles
                    content_upper = content.upper()
                    has_actual_title = any(title.upper() in content_upper for title in actual_titles)
                    print(f"[Chatbot] 🔍 VALIDATION: Response contains actual title: {has_actual_title}")
                    
                    # Check for forbidden patterns (generic assignments)
                    forbidden_patterns = ['TOPIC:', 'TOPIC :', 'ASSIGNMENT 1:', 'ASSIGNMENT 2:', 'GEOMETRY SHAPES', 
                                        'FRACTIONS AND DECIMALS', 'LITERATURE ANALYSIS', 'HUMAN ANATOMY PROJECT',
                                        'HEALTH AND WELLNESS ESSAY', 'ASSIGNMENT_LINK', '(ASSIGNMENT_LINK)', '[ASSIGNMENT_LINK]', '(LINK)', '[LINK]']
                    has_forbidden = any(pattern in content_upper for pattern in forbidden_patterns)
                    print(f"[Chatbot] 🔍 VALIDATION: Response has forbidden patterns: {has_forbidden}")
                    if has_forbidden:
                        found_patterns = [p for p in forbidden_patterns if p in content_upper]
                        print(f"[Chatbot] 🔍 VALIDATION: Found forbidden patterns: {found_patterns}")
                    
                    # If response has forbidden patterns or doesn't contain actual titles, format it ourselves
                    if has_forbidden or (actual_titles and not has_actual_title):
                        print(f"[Chatbot] ⚠️ Response contains generic assignments - formatting with actual data")
                        print(f"[Chatbot] ⚠️ Reason: has_forbidden={has_forbidden}, has_actual_title={has_actual_title}, actual_titles_count={len(actual_titles)}")
                        
                        # Determine subject name for heading
                        subject_name = "Assignments"
                        if subject_keywords:
                            if any('MATH' in kw for kw in subject_keywords):
                                subject_name = "Maths Assignments"
                            elif any('ENGLISH' in kw for kw in subject_keywords):
                                subject_name = "English Assignments"
                            elif any('BME' in kw for kw in subject_keywords):
                                subject_name = "BME Assignments"
                            elif any('OOPU' in kw for kw in subject_keywords):
                                subject_name = "OOPU Assignments"
                            elif any('PPS' in kw for kw in subject_keywords):
                                subject_name = "PPS Assignments"
                            elif any('BE' in kw for kw in subject_keywords):
                                subject_name = "BE Assignments"
                            elif any('ES' in kw for kw in subject_keywords):
                                subject_name = "ES Assignments"
                        
                        formatted_response = f"### {subject_name}:\n\n"
                        
                        # Use filtered coursework (only matching subject assignments)
                        assignment_count = 0
                        for cw in filtered_coursework_for_validation:
                            assignment_count += 1
                            title = cw.get('title', '').strip()
                            if title:
                                formatted_response += f"{assignment_count}. **{title}**\n"
                                if cw.get('description'):
                                    formatted_response += f"   **Description:** {cw.get('description')}\n"
                                if cw.get('due') or cw.get('dueDate'):
                                    due = cw.get('due') or cw.get('dueDate', '')
                                    formatted_response += f"   **Due Date:** {due}\n"
                                if cw.get('status'):
                                    formatted_response += f"   **Status:** {cw.get('status')}\n"
                                if cw.get('alternate_link'):
                                    formatted_response += f"   **[View Assignment]({cw.get('alternate_link')})**\n"
                                formatted_response += "\n"
                        
                        if assignment_count > 0:
                            print(f"[Chatbot] ✅ Auto-formatted response with {assignment_count} filtered assignments")
                            return formatted_response.strip()
                        else:
                            return f"I couldn't find any {subject_name.lower()} in your courses."
                
                # Post-process response to remove repeated questions for Hindi queries
                final_content = content.strip()
                if query_language != 'english' and final_content:
                    # Check if response starts with a rephrased question (common issue with Hindi responses)
                    lines = final_content.split('\n')
                    if len(lines) > 0:
                        first_line = lines[0].strip()
                        # Look for patterns like "**[date] को क्या है?**" or "**[date] ko kya hai**"
                        question_pattern = r'^\*\*[^*]*\s+(को\s+क्या\s+है|ko\s+kya\s+hai|को\s+क्या\s+होता\s+है|ko\s+kya\s+hot.*hai)\?\*\*$'
                        if re.match(question_pattern, first_line, re.IGNORECASE | re.UNICODE):
                            # Remove the repeated question line
                            final_content = '\n'.join(lines[1:]).strip()
                            print(f"[Chatbot] Removed repeated question from Hindi response")

                return final_content
            elif content and finish_reason == "length":
                print(f"[Chatbot] Response truncated due to length on attempt {attempt + 1}")
                # Try with a more focused prompt
                continue
            else:
                print(f"[Chatbot] Incomplete response on attempt {attempt + 1}, trying again...")
                continue
                
        except Exception as e:
            print(f"[Chatbot] Error on attempt {attempt + 1}: {e}")
            if attempt == max_attempts - 1:
                return "Sorry, I encountered an error while generating a response."
            continue
    
    # If all attempts failed, return a basic response
    return "I apologize, but I'm having trouble generating a complete response at the moment. Please try rephrasing your question or ask for more specific information."



    # Step 0.10: Intent-based Q&A for "What are the fees for different grades?"

    fees_intents = [

        "what are the fees for different grades",

        "prakriti fee structure",

        "school fees",

        "What is the school fees",

        "prakriti fees",

        "grade wise fees",

        "admission charges",

        "fee for nursery",

        "fee for grade 1",

        "fee for grade 12",

        "prakriti admission fee",

        "prakriti tuition",

        "prakriti security deposit",

        "prakriti monthly fee",

        "prakriti one time charges",

        "prakriti payment",

        "prakriti fee breakdown",

        "prakriti fee details",

        "prakriti fee for 2024",

        "prakriti fee for 2025",

    ]

    if any(kw in user_query.lower() for kw in fees_intents):

        canonical_answer = (

            '(2024–25 fee structure)\n'

            '| Grade | Monthly Fee (₹) | Security Deposit (₹, refundable) |\n'

            '|---|---|---|\n'

            '| Pre-Nursery–KG | 21,000 | 60,000 |\n'

            '| Grade I–V | 25,400 | 75,000 |\n'

            '| Grade VI–VIII | 28,000 | 90,000 |\n'

            '| Grade IX | 31,200 | 100,000 |\n'

            '| Grade X | 32,400 | 100,000 |\n'

            '| Grade XI–XII | 35,000 | 100,000 |\n'

            '| Admission charges (one-time, non-refundable) | – | 125,000'

        )

        prompt = (

            f"A user asked about the fees for different grades. Here is the official answer (including a table):\n{canonical_answer}\n"

            "Please explain this in your own words, summarize the fee structure, and mention the admission charges."

        )

        response = openai_client.chat.completions.create(

            model=get_default_gpt_model(),

            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],

            temperature=0.3,

        )

        content = response.choices[0].message.content

        return content.strip() if content else canonical_answer



    # Step 0.11: Intent-based Q&A for "Where is Prakriti School located?" with Google Map embed

    location_intents = [

        "where is prakriti school located",

        "prakriti school location",

        "prakriti address",

        "prakriti location",

        "school address",

        "prakriti map",

        "how to reach prakriti",

        "prakriti school directions",

        "prakriti school google map",

        "prakriti school route",

        "prakriti school navigation",

        "prakriti school in greater noida",

        "prakriti school on expressway",

        "prakriti school ncr",

    ]

    if any(kw in user_query.lower() for kw in location_intents):

        canonical_answer = (

            'Prakriti is located on the Noida Expressway in Greater Noida, NCR.'

        )

        prompt = (

            f"A user asked about the location of Prakriti School. Here is the official answer: {canonical_answer}\n"

            "Please explain this in your own words, elaborate, or summarize as needed."

        )

        response = openai_client.chat.completions.create(

            model=get_default_gpt_model(),

            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],

            temperature=0.3,

        )

        content = response.choices[0].message.content

        # Google Maps embed URL for Prakriti School

        map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3502.123456789!2d77.123456!3d28.123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce4b123456789:0xabcdefabcdefabcd!2sPrakriti%20School!5e0!3m2!1sen!2sin!4v1710000000000!5m2!1sen!2sin"

        return [content.strip() if content else canonical_answer, {"type": "map", "url": map_url}]



    # Step 0.12: YouTube Video Intent Detection (only for clear video requests)
    # Explicit video request keywords - user is asking for a video
    explicit_video_keywords = [
        "show me a video", "show me video", "watch a video", "watch video", "see a video", "see video",
        "video about", "video of", "video on", "videos about", "videos of", "videos on",
        "play video", "play a video", "demonstration video", "video demonstration"
    ]
    
    # School activity keywords - these are specific to school events/activities that have videos
    school_activity_keywords = [
        "gardening program", "art exhibition", "sports day", "campus tour", "school tour",
        "facilities tour", "science fair", "music performance", "dance performance",
        "workshop video", "school activity", "school program", "school event"
    ]
    
    # Educational concept keywords that should NOT trigger video intent
    educational_concept_keywords = [
        "explain", "what is", "how does", "describe", "tell me about", "define", "meaning of",
        "concept", "theory", "principle", "detail", "details", "example", "examples",
        "magnetic field", "electric field", "gravity", "force", "energy", "molecule", "atom"
    ]
    
    query_lower = user_query.lower()
    
    # Check for explicit video requests
    is_explicit_video_query = any(kw in query_lower for kw in explicit_video_keywords)
    
    # Check for school activity queries
    is_school_activity_query = any(kw in query_lower for kw in school_activity_keywords)
    
    # Check if it's an educational concept query (should NOT trigger video)
    is_educational_concept_query = any(kw in query_lower for kw in educational_concept_keywords)
    
    # Only detect video intent for explicit video requests or school activities, NOT for educational concepts
    is_article_query = any(word in query_lower for word in ["article", "articles", "substack", "blog", "news", "text", "read"])
    is_video_query = (is_explicit_video_query or is_school_activity_query) and not is_educational_concept_query

    if is_video_query and not is_article_query:
        print("[Chatbot] Detected video intent, processing with LangGraph...")

        try:

            video_result = process_video_query(user_query)

            if video_result["videos"]:

                # Return mixed response with text and videos

                response_text = video_result["response"]

                videos = video_result["videos"]

                return [response_text, {"type": "videos", "videos": videos}]

            else:

                # Fall through to regular LLM response

                pass

        except Exception as e:

            print(f"[Chatbot] Error processing video query: {e}")

            # Fall through to regular LLM response



    # Step 2: Fallback to LLM with streaming approach

    print("=" * 80)
    print("[Chatbot] 🤖 MODEL SELECTION: Cost Optimization")
    print("[Chatbot] 📋 Strategy:")
    print("[Chatbot]   • GPT-4o-mini: Used for ALL queries (optimal cost-performance balance)")
    print("[Chatbot] 💰 Expected cost: ~80% reduction vs using GPT-3.5-turbo for all queries")
    print("=" * 80)

    

    # Try multiple approaches to get complete response

    max_attempts = 3

    for attempt in range(max_attempts):

        try:

            # Build personalized system prompt
            personalization = ""

            if user_profile:

                role = user_profile.get('role', '')
                first_name = user_profile.get('first_name', '')

                grade = user_profile.get('grade', '')

                subjects = user_profile.get('subjects', [])

                learning_goals = user_profile.get('learning_goals', '')

                interests = user_profile.get('interests', [])

                learning_style = user_profile.get('learning_style', '')

                department = user_profile.get('department', '')

                subjects_taught = user_profile.get('subjects_taught', [])

                relationship = user_profile.get('relationship_to_student', '')

                

                personalization = f"""



## Current User Context:

- **Name**: {first_name}

- **Role**: {role.title()}

"""

                

                if role == 'student':

                    personalization += f"""- **Grade**: {grade}

- **Subjects**: {', '.join(subjects) if subjects else 'Not specified'}

- **Learning Goals**: {learning_goals if learning_goals else 'Not specified'}

- **Interests**: {', '.join(interests) if interests else 'Not specified'}

- **Learning Style**: {learning_style if learning_style else 'Not specified'}"""

                elif role == 'teacher':

                    personalization += f"""- **Department**: {department}

- **Subjects Taught**: {', '.join(subjects_taught) if subjects_taught else 'Not specified'}"""

                elif role == 'parent':

                    personalization += f"""- **Relationship**: {relationship.title() if relationship else 'Not specified'}"""

                

                personalization += """

## Personalization Guidelines:
- Address the user by their first name when appropriate
- Tailor responses to their specific role (student/teacher/parent)
- Reference their grade, subjects, or department when relevant
- Consider their learning goals and interests when providing advice
- Use their preferred learning style when suggesting study methods

- Be more specific and targeted in your responses based on their profile"""


            # Check if we have exam response from drive integration
            print(f"[Chatbot] 🔍 FINAL CHECK - exam_response: {len(exam_response) if exam_response else 0} characters")
            print(f"[Chatbot] 🔍 exam_response content: {exam_response[:100] if exam_response else 'EMPTY'}")
            if exam_response:
                print(f"[Chatbot] 📚 RETURNING DRIVE RESPONSE NOW")
                return exam_response
            else:
                print(f"[Chatbot] ⚠️ No exam response, continuing to OpenAI")

            # Build messages array with conversation history

            messages = [

                {"role": "system", "content": f"""You are Prakriti School's official AI assistant chatbot. You represent Prakriti, an alternative/progressive K-12 school located on the Noida Expressway in Greater Noida, NCR, India.



## About Prakriti School:

- **Type**: Alternative/progressive K-12 school

- **Location**: Noida Expressway, Greater Noida, NCR, India

- **Philosophy**: "Learning for happiness" through deep experiential education

- **Approach**: Compassionate, learner-centric model based on reconnecting with inner nature ("prakriti")

- **Focus**: Joy, self-expression, and holistic development



## Key Features:

- **Bridge Programme**: Inclusive curriculum for children with diverse needs, supported by special educators, therapists, and parent support systems

- **Curriculum**: IGCSE (Grades 9-10) and AS/A Level (Grades 11-12) with subjects including Design & Tech, History, Computer Science, Enterprise, Art & Design, Physics, Chemistry, Biology, Combined Sciences, English First & Second Language, French, and Math

- **Activities**: Sports, visual & performing arts, music, theater, STEM/design labs, farm outings, meditation/mindfulness, and maker projects

- **Fee Structure**: Monthly fees range from ₹21,000 (Pre-Nursery-KG) to ₹35,000 (Grade XI-XII), with one-time admission charges of ₹125,000""" + personalization + """



## Your Role:

- Always contextualize your responses specifically for Prakriti School

- When discussing education, learning, or school-related topics, relate them to Prakriti's progressive, experiential approach

- Emphasize Prakriti's unique philosophy of "learning for happiness" and holistic development

- When appropriate, mention Prakriti's specific programs, activities, or features

- Be warm, encouraging, and aligned with Prakriti's compassionate, learner-centric values

- Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points)

- End responses with proper conclusions that reinforce Prakriti's educational philosophy



Remember: Every response should reflect Prakriti School's unique identity and educational approach."""}
            ]

            

            # Add conversation history (limit to last 10 messages to avoid token limits)

            recent_history = conversation_history[-10:] if conversation_history else []

            for msg in recent_history:

                messages.append({"role": msg["role"], "content": msg["content"]})

            

            # Add current user query

            messages.append({"role": "user", "content": f"Question: {user_query}\n\nPlease provide a complete answer that fully addresses this question. Make sure to end with a proper conclusion and do not cut off mid-sentence."})

            

            # Using GPT-3.5-turbo for testing (much cheaper)
            model_name = "gpt-3.5-turbo"  # TEST MODE: Using GPT-3.5-turbo for cost savings
            print(f"[Chatbot] 🤖 DEBUG: Using model: {model_name}")
            print(f"[Chatbot] 🤖 DEBUG: Model pricing - Input: $0.0015/1K tokens, Output: $0.002/1K tokens")
            
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,

            )

            

            content = response.choices[0].message.content

            finish_reason = response.choices[0].finish_reason

            

            print(f"[Chatbot] Attempt {attempt + 1} - Response length: {len(content) if content else 0} characters")

            print(f"[Chatbot] Finish reason: {finish_reason}")

            

            # Check if response is complete

            if content and finish_reason == "stop" and not content.strip().endswith(("of", "and", "the", "in", "to", "for", "with", "by")):

                print(f"[Chatbot] Complete response received on attempt {attempt + 1}")

                # Post-process response to remove repeated questions for Hindi queries
                final_content = content.strip()
                if query_language != 'english' and final_content:
                    # Check if response starts with a rephrased question (common issue with Hindi responses)
                    lines = final_content.split('\n')
                    if len(lines) > 0:
                        first_line = lines[0].strip()
                        # Look for patterns like "**[date] को क्या है?**" or "**[date] ko kya hai**"
                        question_pattern = r'^\*\*[^*]*\s+(को\s+क्या\s+है|ko\s+kya\s+hai|को\s+क्या\s+होता\s+है|ko\s+kya\s+hot.*hai)\?\*\*$'
                        if re.match(question_pattern, first_line, re.IGNORECASE | re.UNICODE):
                            # Remove the repeated question line
                            final_content = '\n'.join(lines[1:]).strip()
                            print(f"[Chatbot] Removed repeated question from Hindi response")

                return final_content

            elif content and finish_reason == "length":

                print(f"[Chatbot] Response truncated due to length on attempt {attempt + 1}")

                # Try with a more focused prompt

                continue

            else:

                print(f"[Chatbot] Incomplete response on attempt {attempt + 1}, trying again...")

                continue

                

        except Exception as e:

            print(f"[Chatbot] Error on attempt {attempt + 1}: {e}")

            if attempt == max_attempts - 1:

                return "Sorry, I encountered an error while generating a response."

            continue

    

    # If all attempts failed, return a basic response

    return "I apologize, but I'm having trouble generating a complete response at the moment. Please try rephrasing your question or ask for more specific information."



    # Step 0.10: Intent-based Q&A for "What are the fees for different grades?"

    fees_intents = [

        "what are the fees for different grades",

        "prakriti fee structure",

        "school fees",

        "What is the school fees",

        "prakriti fees",

        "grade wise fees",

        "admission charges",

        "fee for nursery",

        "fee for grade 1",

        "fee for grade 12",

        "prakriti admission fee",

        "prakriti tuition",

        "prakriti security deposit",

        "prakriti monthly fee",

        "prakriti one time charges",

        "prakriti payment",

        "prakriti fee breakdown",

        "prakriti fee details",

        "prakriti fee for 2024",

        "prakriti fee for 2025",

    ]

    if any(kw in user_query.lower() for kw in fees_intents):

        canonical_answer = (

            '(2024–25 fee structure)\n'

            '| Grade | Monthly Fee (₹) | Security Deposit (₹, refundable) |\n'

            '|---|---|---|\n'

            '| Pre-Nursery–KG | 21,000 | 60,000 |\n'

            '| Grade I–V | 25,400 | 75,000 |\n'

            '| Grade VI–VIII | 28,000 | 90,000 |\n'

            '| Grade IX | 31,200 | 100,000 |\n'

            '| Grade X | 32,400 | 100,000 |\n'

            '| Grade XI–XII | 35,000 | 100,000 |\n'

            '| Admission charges (one-time, non-refundable) | – | 125,000'

        )

        prompt = (

            f"A user asked about the fees for different grades. Here is the official answer (including a table):\n{canonical_answer}\n"

            "Please explain this in your own words, summarize the fee structure, and mention the admission charges."

        )

        response = openai_client.chat.completions.create(

            model=get_default_gpt_model(),

            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],

            temperature=0.3,

        )

        content = response.choices[0].message.content

        return content.strip() if content else canonical_answer



    # Step 0.11: Intent-based Q&A for "Where is Prakriti School located?" with Google Map embed

    location_intents = [

        "where is prakriti school located",

        "prakriti school location",

        "prakriti address",

        "prakriti location",

        "school address",

        "prakriti map",

        "how to reach prakriti",

        "prakriti school directions",

        "prakriti school google map",

        "prakriti school route",

        "prakriti school navigation",

        "prakriti school in greater noida",

        "prakriti school on expressway",

        "prakriti school ncr",

    ]

    if any(kw in user_query.lower() for kw in location_intents):

        canonical_answer = (

            'Prakriti is located on the Noida Expressway in Greater Noida, NCR.'

        )

        prompt = (

            f"A user asked about the location of Prakriti School. Here is the official answer: {canonical_answer}\n"

            "Please explain this in your own words, elaborate, or summarize as needed."

        )

        response = openai_client.chat.completions.create(

            model=get_default_gpt_model(),

            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],

            temperature=0.3,

        )

        content = response.choices[0].message.content

        # Google Maps embed URL for Prakriti School

        map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3502.123456789!2d77.123456!3d28.123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce4b123456789:0xabcdefabcdefabcd!2sPrakriti%20School!5e0!3m2!1sen!2sin!4v1710000000000!5m2!1sen!2sin"

        return [content.strip() if content else canonical_answer, {"type": "map", "url": map_url}]



    # Step 0.12: YouTube Video Intent Detection (only for clear video requests)
    # Explicit video request keywords - user is asking for a video
    explicit_video_keywords = [
        "show me a video", "show me video", "watch a video", "watch video", "see a video", "see video",
        "video about", "video of", "video on", "videos about", "videos of", "videos on",
        "play video", "play a video", "demonstration video", "video demonstration"
    ]
    
    # School activity keywords - these are specific to school events/activities that have videos
    school_activity_keywords = [
        "gardening program", "art exhibition", "sports day", "campus tour", "school tour",
        "facilities tour", "science fair", "music performance", "dance performance",
        "workshop video", "school activity", "school program", "school event"
    ]
    
    # Educational concept keywords that should NOT trigger video intent
    educational_concept_keywords = [
        "explain", "what is", "how does", "describe", "tell me about", "define", "meaning of",
        "concept", "theory", "principle", "detail", "details", "example", "examples",
        "magnetic field", "electric field", "gravity", "force", "energy", "molecule", "atom"
    ]
    
    query_lower = user_query.lower()
    
    # Check for explicit video requests
    is_explicit_video_query = any(kw in query_lower for kw in explicit_video_keywords)
    
    # Check for school activity queries
    is_school_activity_query = any(kw in query_lower for kw in school_activity_keywords)
    
    # Check if it's an educational concept query (should NOT trigger video)
    is_educational_concept_query = any(kw in query_lower for kw in educational_concept_keywords)
    
    # Only detect video intent for explicit video requests or school activities, NOT for educational concepts
    is_article_query = any(word in query_lower for word in ["article", "articles", "substack", "blog", "news", "text", "read"])
    is_video_query = (is_explicit_video_query or is_school_activity_query) and not is_educational_concept_query

    if is_video_query and not is_article_query:
        print("[Chatbot] Detected video intent, processing with LangGraph...")

        try:

            video_result = process_video_query(user_query)

            if video_result["videos"]:

                # Return mixed response with text and videos

                response_text = video_result["response"]

                videos = video_result["videos"]

                return [response_text, {"type": "videos", "videos": videos}]

            else:

                # Fall through to regular LLM response

                pass

        except Exception as e:

            print(f"[Chatbot] Error processing video query: {e}")

            # Fall through to regular LLM response



    # Step 2: Fallback to LLM with streaming approach

    print("=" * 80)
    print("[Chatbot] 🤖 MODEL SELECTION: Cost Optimization")
    print("[Chatbot] 📋 Strategy:")
    print("[Chatbot]   • GPT-4o-mini: Used for ALL queries (optimal cost-performance balance)")
    print("[Chatbot] 💰 Expected cost: ~80% reduction vs using GPT-3.5-turbo for all queries")
    print("=" * 80)

    

    # Try multiple approaches to get complete response

    max_attempts = 3

    for attempt in range(max_attempts):

        try:

            # Build personalized system prompt
            personalization = ""

            if user_profile:

                role = user_profile.get('role', '')
                first_name = user_profile.get('first_name', '')

                grade = user_profile.get('grade', '')

                subjects = user_profile.get('subjects', [])

                learning_goals = user_profile.get('learning_goals', '')

                interests = user_profile.get('interests', [])

                learning_style = user_profile.get('learning_style', '')

                department = user_profile.get('department', '')

                subjects_taught = user_profile.get('subjects_taught', [])

                relationship = user_profile.get('relationship_to_student', '')

                

                personalization = f"""



## Current User Context:

- **Name**: {first_name}

- **Role**: {role.title()}

"""

                

                if role == 'student':

                    personalization += f"""- **Grade**: {grade}

- **Subjects**: {', '.join(subjects) if subjects else 'Not specified'}

- **Learning Goals**: {learning_goals if learning_goals else 'Not specified'}

- **Interests**: {', '.join(interests) if interests else 'Not specified'}

- **Learning Style**: {learning_style if learning_style else 'Not specified'}"""

                elif role == 'teacher':

                    personalization += f"""- **Department**: {department}

- **Subjects Taught**: {', '.join(subjects_taught) if subjects_taught else 'Not specified'}"""

                elif role == 'parent':

                    personalization += f"""- **Relationship**: {relationship.title() if relationship else 'Not specified'}"""

                

                personalization += """

## Personalization Guidelines:
- Address the user by their first name when appropriate
- Tailor responses to their specific role (student/teacher/parent)
- Reference their grade, subjects, or department when relevant
- Consider their learning goals and interests when providing advice
- Use their preferred learning style when suggesting study methods

- Be more specific and targeted in your responses based on their profile"""


            # Check if we have exam response from drive integration
            print(f"[Chatbot] 🔍 FINAL CHECK - exam_response: {len(exam_response) if exam_response else 0} characters")
            print(f"[Chatbot] 🔍 exam_response content: {exam_response[:100] if exam_response else 'EMPTY'}")
            if exam_response:
                print(f"[Chatbot] 📚 RETURNING DRIVE RESPONSE NOW")
                return exam_response
            else:
                print(f"[Chatbot] ⚠️ No exam response, continuing to OpenAI")

            # Build messages array with conversation history

            messages = [

                {"role": "system", "content": f"""You are Prakriti School's official AI assistant chatbot. You represent Prakriti, an alternative/progressive K-12 school located on the Noida Expressway in Greater Noida, NCR, India.



## About Prakriti School:

- **Type**: Alternative/progressive K-12 school

- **Location**: Noida Expressway, Greater Noida, NCR, India

- **Philosophy**: "Learning for happiness" through deep experiential education

- **Approach**: Compassionate, learner-centric model based on reconnecting with inner nature ("prakriti")

- **Focus**: Joy, self-expression, and holistic development



## Key Features:

- **Bridge Programme**: Inclusive curriculum for children with diverse needs, supported by special educators, therapists, and parent support systems

- **Curriculum**: IGCSE (Grades 9-10) and AS/A Level (Grades 11-12) with subjects including Design & Tech, History, Computer Science, Enterprise, Art & Design, Physics, Chemistry, Biology, Combined Sciences, English First & Second Language, French, and Math

- **Activities**: Sports, visual & performing arts, music, theater, STEM/design labs, farm outings, meditation/mindfulness, and maker projects

- **Fee Structure**: Monthly fees range from ₹21,000 (Pre-Nursery-KG) to ₹35,000 (Grade XI-XII), with one-time admission charges of ₹125,000""" + personalization + """



## Your Role:

- Always contextualize your responses specifically for Prakriti School

- When discussing education, learning, or school-related topics, relate them to Prakriti's progressive, experiential approach

- Emphasize Prakriti's unique philosophy of "learning for happiness" and holistic development

- When appropriate, mention Prakriti's specific programs, activities, or features

- Be warm, encouraging, and aligned with Prakriti's compassionate, learner-centric values

- Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points)

- End responses with proper conclusions that reinforce Prakriti's educational philosophy



Remember: Every response should reflect Prakriti School's unique identity and educational approach."""}
            ]

            

            # Add conversation history (limit to last 10 messages to avoid token limits)

            recent_history = conversation_history[-10:] if conversation_history else []

            for msg in recent_history:

                messages.append({"role": msg["role"], "content": msg["content"]})

            

            # Add current user query

            messages.append({"role": "user", "content": f"Question: {user_query}\n\nPlease provide a complete answer that fully addresses this question. Make sure to end with a proper conclusion and do not cut off mid-sentence."})

            

            # Using GPT-3.5-turbo for testing (much cheaper)
            model_name = "gpt-3.5-turbo"  # TEST MODE: Using GPT-3.5-turbo for cost savings
            print(f"[Chatbot] 🤖 DEBUG: Using model: {model_name}")
            print(f"[Chatbot] 🤖 DEBUG: Model pricing - Input: $0.0015/1K tokens, Output: $0.002/1K tokens")
            
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,

            )

            

            content = response.choices[0].message.content

            finish_reason = response.choices[0].finish_reason

            

            print(f"[Chatbot] Attempt {attempt + 1} - Response length: {len(content) if content else 0} characters")

            print(f"[Chatbot] Finish reason: {finish_reason}")

            

            # Check if response is complete

            if content and finish_reason == "stop" and not content.strip().endswith(("of", "and", "the", "in", "to", "for", "with", "by")):

                print(f"[Chatbot] Complete response received on attempt {attempt + 1}")

                # Post-process response to remove repeated questions for Hindi queries
                final_content = content.strip()
                if query_language != 'english' and final_content:
                    # Check if response starts with a rephrased question (common issue with Hindi responses)
                    lines = final_content.split('\n')
                    if len(lines) > 0:
                        first_line = lines[0].strip()
                        # Look for patterns like "**[date] को क्या है?**" or "**[date] ko kya hai**"
                        question_pattern = r'^\*\*[^*]*\s+(को\s+क्या\s+है|ko\s+kya\s+hai|को\s+क्या\s+होता\s+है|ko\s+kya\s+hot.*hai)\?\*\*$'
                        if re.match(question_pattern, first_line, re.IGNORECASE | re.UNICODE):
                            # Remove the repeated question line
                            final_content = '\n'.join(lines[1:]).strip()
                            print(f"[Chatbot] Removed repeated question from Hindi response")

                return final_content

            elif content and finish_reason == "length":

                print(f"[Chatbot] Response truncated due to length on attempt {attempt + 1}")

                # Try with a more focused prompt

                continue

            else:

                print(f"[Chatbot] Incomplete response on attempt {attempt + 1}, trying again...")

                continue

                

        except Exception as e:

            print(f"[Chatbot] Error on attempt {attempt + 1}: {e}")

            if attempt == max_attempts - 1:

                return "Sorry, I encountered an error while generating a response."

            continue

    

    # If all attempts failed, return a basic response

    return "I apologize, but I'm having trouble generating a complete response at the moment. Please try rephrasing your question or ask for more specific information." 