import os
import json
from app.core.openai_client import get_openai_client
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
                calendar_check = supabase.table('google_calendar_events').select('user_id').limit(1).execute()
                if calendar_check.data and len(calendar_check.data) > 0:
                    user_id = calendar_check.data[0]['user_id']
            
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
            
        # Get calendar data (upcoming events) from normalized table - only if requested
        formatted_calendar_data = []
        calendar_events = []  # Initialize to empty list
        if load_calendar:
            now = datetime.utcnow().isoformat()
            events_result = supabase.table('google_calendar_events').select('*').eq('user_id', user_id).gte('start_time', now).order('start_time', desc=False).limit(10).execute()
            calendar_events = events_result.data if events_result.data else []
            
            print(f"[Chatbot] Found {len(calendar_events)} upcoming calendar events")
            
            # Format calendar data
            for event in calendar_events:
                formatted_calendar_data.append({
                        "eventId": event.get('event_id', ''),
                        "summary": event.get('summary', ''),
                        "description": event.get('description', ''),
                        "startTime": event.get('start_time', ''),
                        "endTime": event.get('end_time', ''),
                        "location": event.get('location', ''),
                        "hangoutLink": event.get('hangout_link', '')
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

def generate_chatbot_response(request):
    """
    Use OpenAI GPT-4 to generate a chatbot response with RAG logic and fuzzy matching.
    """
    openai_client = get_openai_client()
    user_query = request.message
    conversation_history = getattr(request, 'conversation_history', [])
    user_profile = getattr(request, 'user_profile', None)

    
    # Step 0: Check if this is a greeting and provide role-specific greeting (PRIORITY)
    import re
    greeting_patterns = [
        r'\bhi\b', r'\bhello\b', r'\bhey\b', 
        r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b', 
        r'\bgreetings\b'
    ]
    is_greeting = any(re.search(pattern, user_query.lower()) for pattern in greeting_patterns)
    
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        # Google Maps embed URL for Prakriti School
        map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3502.123456789!2d77.123456!3d28.123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce4b123456789:0xabcdefabcdefabcd!2sPrakriti%20School!5e0!3m2!1sen!2sin!4v1710000000000!5m2!1sen!2sin"
        return [content.strip() if content else canonical_answer, {"type": "map", "url": map_url}]

    # Step 0.12: YouTube Video Intent Detection (only for clear video requests)
    video_keywords = [
        "video", "show me", "watch", "see", "demonstration", "example", "gardening", "art", "sports", 
        "science", "mindfulness", "meditation", "campus", "facilities", "tour", "performance", 
        "exhibition", "workshop", "activity", "program", "class", "lesson"
    ]
    
    # Only detect video intent for clear video-related queries, not for article/text queries
    is_article_query = any(word in user_query.lower() for word in ["article", "articles", "substack", "blog", "news", "text", "read"])
    is_video_query = any(kw in user_query.lower() for kw in video_keywords)
    
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
    
    # Check if this is a person introduction/detail query (should use web crawler, NOT classroom data)
    person_detail_keywords = ['introduction', 'detail', 'details', 'who is', 'about', 'little bit about', 
                             'information about', 'tell me about', 'profile', 'biography']
    is_person_detail_query = any(kw in query_lower for kw in person_detail_keywords)
    
    # Check if query mentions a specific person name (capitalized words or known names)
    import re
    # Try both original query (for capitalized names) and lowercase (for case-insensitive detection)
    person_name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
    potential_names = re.findall(person_name_pattern, user_query)
    # If no capitalized names found, try case-insensitive pattern on lowercase query
    if not potential_names:
        # First, try to extract name after common question patterns (e.g., "who is X", "tell me about X")
        question_patterns = [
            r'(?:who\s+is|who\'?s|what\s+is|what\'?s|tell\s+me\s+about|information\s+about|details?\s+about|introduction\s+to|profile\s+of|biography\s+of|about)\s+(?:the\s+)?([a-z]+\s+[a-z]+(?:\s+[a-z]+)?)',
            r'(?:who\s+is|who\'?s|what\s+is|what\'?s|tell\s+me\s+about|information\s+about|details?\s+about|introduction\s+to|profile\s+of|biography\s+of|about)\s+([a-z]+\s+[a-z]+(?:\s+[a-z]+)?)',
        ]
        
        extracted_name = None
        for pattern in question_patterns:
            match = re.search(pattern, query_lower)
            if match:
                extracted_name = match.group(1).strip()
                # Remove trailing punctuation and question marks
                extracted_name = re.sub(r'[?.,!]+$', '', extracted_name).strip()
                if len(extracted_name) > 5:
                    potential_names = [extracted_name.title()]
                    break
        
        # Fallback: Pattern for lowercase names (2-3 words, each starting with a letter)
        if not potential_names:
            person_name_pattern_lower = r'\b[a-z]+\s+[a-z]+(?:\s+[a-z]+)?\b'
            # Extract potential names (exclude common words like "the", "is", "who", etc.)
            excluded_words = {'the', 'is', 'who', 'what', 'when', 'where', 'why', 'how', 'about', 'tell', 'me', 
                             'information', 'detail', 'details', 'introduction', 'profile', 'biography', 'little', 'bit'}
            all_words = re.findall(person_name_pattern_lower, query_lower)
            # Filter out phrases that contain excluded words or are too short/common
            potential_names_lower = [name for name in all_words if not any(word in excluded_words for word in name.split()) and len(name) > 5]
            if potential_names_lower:
                # Convert to title case for consistency
                potential_names = [name.title() for name in potential_names_lower[:3]]  # Limit to first 3 matches
    
    has_person_name = len(potential_names) > 0 and not any(name.lower() in ['Prakriti', 'School', 'Google', 'Classroom', 'Calendar'] for name in potential_names)
    
    # Check if person query might be about a teacher (so we can verify with Classroom data)
    # If query mentions teacher-related terms, we should load teacher data to verify web crawler claims
    teacher_context_in_query = any(kw in query_lower for kw in ['teacher', 'teachers', 'homeroom', 'instructor', 'faculty', 'staff'])
    
    # If person detail query, use web crawler (even if name detection is imperfect)
    # Web crawler can search by the query itself, and we'll verify against Classroom data
    # BUT prioritize web crawler if we found a name (more specific search)
    should_use_web_crawling_first = is_person_detail_query  # Run web crawler for person queries regardless of name detection
    
    # Detect specific classroom data intent for optimized loading
    is_announcement_query = any(kw in query_lower for kw in ['announcement', 'announce', 'notice', 'update', 'news'])
    is_student_query = any(kw in query_lower for kw in ['student', 'students', 'classmate', 'classmates', 'roster', 'enrollment'])
    is_teacher_query = any(kw in query_lower for kw in ['teacher', 'teachers', 'faculty', 'instructor', 'instructors', 'staff member', 'staff'])
    is_coursework_query = any(kw in query_lower for kw in ['assignment', 'homework', 'coursework', 'task', 'due', 'submit'])
    is_course_query = any(kw in query_lower for kw in ['course', 'courses', 'class', 'classes', 'subject', 'subjects'])
    is_calendar_query = any(kw in query_lower for kw in ['event', 'events', 'calendar', 'schedule', 'meeting', 'holiday'])
    
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
    
    # For person detail queries, use web crawler first (team page)
    web_enhanced_info = ""
    should_use_web_crawling = False  # Initialize to avoid UnboundLocalError
    
    # Define web enhancement keywords outside if/else to avoid UnboundLocalError
    web_enhancement_keywords = [
        'latest', 'recent', 'news', 'update', 'current', 'new', 'recently',
        'prakriti school', 'prakrit school', 'progressive education',
        'alternative school', 'igcse', 'a level', 'bridge programme',
        'admission', 'fees', 'curriculum', 'activities', 'facilities',
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
        is_classroom_related_query = is_announcement_query or is_coursework_query or is_student_query or is_teacher_query or is_course_query or is_calendar_query
        
        should_use_web_crawling = any(keyword in user_query.lower() for keyword in web_enhancement_keywords) and not is_pure_academic_query and not is_translation_query and not is_classroom_related_query
        
        # Log why web crawling was skipped for classroom queries
        if is_classroom_related_query and any(keyword in user_query.lower() for keyword in web_enhancement_keywords):
            print(f"[Chatbot] ⚠️ Web crawling skipped - Classroom-related query detected. Using Classroom/Calendar data instead.")
    
    # Check if frontend provided cached web data
    cached_web_data = getattr(request, 'cached_web_data', None)
    
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

    # Get admin data for enhanced responses - BUT only if not a person detail query OR web-only query
    # IMPORTANT: Use admin data (synced Google Classroom/Calendar) as REFERENCE for ALL users
    # This data is a shared knowledge base - not restricted to admins only
    admin_data = {"classroom_data": [], "calendar_data": []}
    
    # Skip classroom data for web-only queries (PERFORMANCE OPTIMIZATION)
    is_web_only_query = should_use_web_crawling and not (is_announcement_query or is_coursework_query or is_student_query or is_teacher_query or is_course_query or is_calendar_query)
    
    if is_web_only_query:
        print(f"[Chatbot] ⚡ Skipping classroom data fetch - web-only query detected (faster response)")
    elif ADMIN_FEATURES_AVAILABLE:
        try:
            print("[Chatbot] Getting reference data from Supabase (Google Classroom/Calendar sync)...")
            print(f"[Chatbot] User: {user_profile.get('email', 'Anonymous') if user_profile else 'Anonymous'}")
            
            # Try to get data from current user if they're admin, otherwise get from first available admin
            # This is REFERENCE data, not user-specific - anyone can use it
            user_email = user_profile.get('email', '') if user_profile else ''
            
            # Determine what to load based on query intent (optimize for speed and cost)
            # Only load what's needed: if asking about teachers, only load teachers; if students, only students; etc.
            # CRITICAL: For person detail queries, always load teachers to verify web crawler claims (web might say someone is a teacher)
            should_load_teachers = is_teacher_query or should_use_web_crawling_first or not (is_student_query or is_announcement_query or is_coursework_query)
            should_load_students = is_student_query or not (is_teacher_query or is_announcement_query or is_coursework_query)
            should_load_announcements = is_announcement_query or not (is_student_query or is_teacher_query or is_coursework_query)
            should_load_coursework = is_coursework_query or not (is_student_query or is_announcement_query or is_teacher_query)
            should_load_calendar = is_calendar_query
            
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
            import re
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Detect specific date(s) in query for SQL filtering
            target_date_ranges_for_sql = []  # List of (start, end) tuples for SQL filtering
            
            if is_yesterday_query:
                yesterday = now - timedelta(days=1)
                target_date_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                target_date_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
                target_date_ranges_for_sql.append((target_date_start, target_date_end))
                print(f"[Chatbot] SQL filtering for 'yesterday': {yesterday.date()}")
            elif is_today_query:
                target_date_ranges_for_sql.append((today_start, today_end))
                print(f"[Chatbot] SQL filtering for 'today': {now.date()}")
            else:
                # Check for specific dates in query - handle "21 and 29 september" or "21, 24, 29 september"
                month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                              'july', 'august', 'september', 'october', 'november', 'december']
                month_abbrevs = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                
                for i, (full_name, abbrev) in enumerate(zip(month_names, month_abbrevs)):
                    # Pattern 1: Handles both single date ("21 september") and multiple dates ("21 and 29 september" or "21, 24, 29 september")
                    # Matches: one or more digits, optionally followed by (comma or "and" + more digits), then month name
                    pattern1 = rf'\b(\d{{1,2}}(?:\s*(?:,|\s+and\s+)\s*\d{{1,2}})*)\s+({full_name}|{abbrev})\b'
                    # Pattern 2: "september 21" or "september 21 and 29" or "september 21, 24, 29"
                    pattern2 = rf'\b({full_name}|{abbrev})\s+(\d{{1,2}}(?:\s*(?:,|\s+and\s+)\s*\d{{1,2}})*)\b'
                    
                    match = re.search(pattern1, query_lower, re.IGNORECASE)
                    if not match:
                        match = re.search(pattern2, query_lower, re.IGNORECASE)
                    
                    # Fuzzy matching for typos (e.g., "octomber" -> "october")
                    if not match and len(full_name) > 4:
                        # Try to find month-like words near numbers - matches single or multiple dates
                        potential_months = re.findall(r'\d{1,2}(?:\s*(?:,|\s+and\s+)\s*\d{1,2})*\s+([a-z]{4,})', query_lower)
                        for pot_month in potential_months:
                            if pot_month[:3] == full_name[:3] and len(pot_month) >= len(full_name) - 2:
                                # Extract all digits before the month word (handles both single and multiple dates)
                                days_match = re.search(rf'(\d{{1,2}}(?:\s*(?:,|\s+and\s+)\s*\d{{1,2}})*)\s+{re.escape(pot_month)}', query_lower, re.IGNORECASE)
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
                            # Extract all numbers (handles both comma and "and" separators)
                            days = [int(d.strip()) for d in re.findall(r'\d+', days_str)]
                            year = now.year
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
                    match = re.search(date_pattern, query_lower)
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
                    
                    # Find any admin who has synced classroom or calendar data
                    # IMPORTANT: user_id in google_classroom_courses is auth.users.id, not user_profiles.id
                    result = supabase.table('google_classroom_courses').select('user_id').limit(1).execute()
                    if not result.data or len(result.data) == 0:
                        result = supabase.table('google_calendar_events').select('user_id').limit(1).execute()
                    
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
    print("[Chatbot] 🤖 HYBRID MODEL SELECTION: Intelligent cost optimization")
    print("[Chatbot] 📋 Strategy:")
    print("[Chatbot]   • GPT-3.5-turbo: Queries with structured data (Classroom/Calendar/Web)")
    print("[Chatbot]   • GPT-4: Complex queries without structured data (reasoning/generation)")
    print("[Chatbot] 💰 Expected cost: ~70-90% reduction vs using GPT-4 for all queries")
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
- Connect their learning goals to Prakriti's holistic approach"""
                    
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
                system_content = """You are Prakriti School's AI assistant. Progressive K-12 school in Greater Noida. Philosophy: "Learning for happiness". Programs: Bridge Programme, IGCSE, AS/A Level. Address users by first name with titles (Sir/Madam for teachers/parents). Use Markdown (**bold**, ### headings). Never say "as an AI". Present data directly without disclaimers.""" + personalization + """ Use provided data to answer questions."""
            else:
                # Ultra-concise system prompt for guest users (TOKEN OPTIMIZATION)
                system_content = """You are Prakriti School's AI assistant. Progressive K-12 school in Greater Noida. Philosophy: "Learning for happiness". Use Markdown. Never say "as an AI". Present data directly. Use provided data to answer questions."""
            
            messages = [{"role": "system", "content": system_content}]
            
            # Detect query intent first (needed for history optimization)
            query_lower = user_query.lower()
            # Detect announcement queries (including common typos like "annunce", "announc", etc.)
            announcement_keywords = ['announcement', 'announce', 'annunce', 'announc', 'notice', 'update', 'news']
            is_announcement_query = any(kw in query_lower for kw in announcement_keywords)
            is_student_query = any(kw in query_lower for kw in ['student', 'classmate', 'roster', 'enrollment'])
            is_teacher_query = any(kw in query_lower for kw in ['teacher', 'instructor', 'faculty'])
            is_coursework_query = any(kw in query_lower for kw in ['assignment', 'homework', 'coursework', 'task', 'due', 'submit'])
            is_course_query = any(kw in query_lower for kw in ['course', 'class', 'subject'])
            is_today_query = any(kw in query_lower for kw in ['today', 'todays', "today's"])
            is_yesterday_query = any(kw in query_lower for kw in ['yesterday', "yesterday's"])
            is_calendar_query = any(kw in query_lower for kw in ['event', 'events', 'calendar', 'schedule', 'meeting', 'holiday'])
            
            # Detect translation/reference queries (need previous response context)
            translation_keywords = ['translate', 'translation', 'gujrati', 'gujarati', 'hindi', 'english', 'language', 'below response', 'previous response', 'that response', 'last response', 'above response', 'send me in', 'give me in']
            is_translation_query = any(keyword in query_lower for keyword in translation_keywords)
            
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
            import re
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
                    
                    match = re.search(pattern1, query_lower, re.IGNORECASE)
                    if not match:
                        match = re.search(pattern2, query_lower, re.IGNORECASE)
                    if not match:
                        match = re.search(pattern3, query_lower, re.IGNORECASE)
                    
                    # If no match, try fuzzy matching for common typos like "octomber" → "october"
                    if not match and len(full_name) > 4:
                        # Simple approach: check if query contains something that looks like the month
                        # Extract potential month words from query (words after numbers)
                        potential_months = re.findall(r'\d+\s*,\s*\d+(?:\s*,\s*\d+)*\s+([a-z]{4,})', query_lower)
                        for pot_month in potential_months:
                            # Check if it's similar to current month name (first 3-4 chars match)
                            if pot_month[:3] == full_name[:3] and len(pot_month) >= len(full_name) - 2:
                                # Extract days from query
                                days_pattern = rf'(\d+(?:\s*,\s*\d+)*)\s+{re.escape(pot_month)}'
                                days_match = re.search(days_pattern, query_lower, re.IGNORECASE)
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
                            days = [int(d.strip()) for d in re.findall(r'\d+', days_str)]
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
                    match = re.search(date_pattern_1, user_query)
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
            if web_enhanced_info:
                # TRUNCATE web info - TOKEN OPTIMIZATION (reduced to 300 chars for queries with classroom data)
                # If classroom data exists, use less web info to prioritize classroom data
                max_web_chars = 300 if admin_data.get('classroom_data') else 400
                truncated_web_info = web_enhanced_info[:max_web_chars] + ("..." if len(web_enhanced_info) > max_web_chars else "")
                user_content += f"Web:\n{truncated_web_info}\n"
                if len(web_enhanced_info) > max_web_chars:
                    print(f"[Chatbot] Truncated web_enhanced_info from {len(web_enhanced_info)} to {max_web_chars} chars to save tokens")
                
                # CRITICAL: If web info claims someone is a teacher AND we have Classroom data, verify against it
                if admin_data.get('classroom_data') and should_use_web_crawling_first:
                    user_content += "\n⚠️ VERIFICATION: Use Web data to provide general information about the person (role, background, etc.). However, if Web info claims they are a teacher, VERIFY against Classroom Data below. Only confirm they are CURRENTLY a teacher for the user's grade/course if their name appears in the Classroom teacher list. If Web says they're a teacher but they're NOT in Classroom Data, provide the general info from Web but clarify their current teaching status based on Classroom Data.\n"
            
            # Add admin data if available - MINIMAL HEADER to save tokens
            if admin_data.get('classroom_data') or (admin_data.get('calendar_data') and is_calendar_query):
                user_content += "Data:\n"
                
                if admin_data.get('classroom_data'):
                    # ULTRA-AGGRESSIVE FILTERING: Only send exactly what's needed for this query type
                    filtered_courses = []
                    
                    # Filter courses by student's grade if user is a student
                    user_grade_num = None
                    if user_profile:
                        user_role = user_profile.get('role', '') or ''
                        user_role_lower = user_role.lower()
                        print(f"[Chatbot] User role: {user_role_lower}, Grade filter check...")
                        
                        if user_role_lower == 'student':
                            user_grade = user_profile.get('grade', '')
                            print(f"[Chatbot] Student grade from profile: '{user_grade}'")
                            if user_grade:
                                # Normalize grade format (e.g., "Grade 8", "G8", "8" -> extract "8" or "G8")
                                import re
                                grade_match = re.search(r'(\d+)', str(user_grade))
                                if grade_match:
                                    user_grade_num = grade_match.group(1)
                                    print(f"[Chatbot] ✅ Filtering courses for Grade {user_grade_num} student")
                                else:
                                    print(f"[Chatbot] ⚠️ Could not extract grade number from: '{user_grade}'")
                            else:
                                print(f"[Chatbot] ⚠️ No grade found in user profile")
                        else:
                            print(f"[Chatbot] User is not a student (role: {user_role_lower}), skipping grade filter")
                    
                    for course in admin_data['classroom_data']:
                        # If user is a student, filter courses by grade
                        if user_grade_num:
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
                            matches_grade = any(re.search(pattern, course_name, re.IGNORECASE) for pattern in grade_patterns)
                            
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
                                # If coursework data exists, include it
                                filtered_course["coursework"] = [{
                                    "id": c.get("courseWorkId"),
                                    "title": c.get("title"),
                                    "due": c.get("dueDate"),
                                    "status": c.get("state")
                                } for c in coursework]
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
                    
                    # Use compact JSON format to save tokens (minimal whitespace)
                    user_content += "Data:\n"
                    user_content += f"{json.dumps(filtered_courses, separators=(',', ':'))}\n"  # Compact format, no indentation
                    
                    # Add concise instructions for coursework queries (TOKEN OPTIMIZATION)
                    if is_coursework_query:
                        if filtered_courses:
                            user_content += "\n⚠️ COURSEWORK: If coursework empty, PROVIDE course_link. Format: ### [Course Name]\n[View Assignments](course_link)\nSteps: 1) Click 2) Classwork tab 3) View\nDO NOT say 'no access'!\n\n"
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
                        user_content += "\n⚠️⚠️⚠️ FORMATTING INSTRUCTIONS FOR TEACHER/STUDENT LISTS: ⚠️⚠️⚠️\n"
                        user_content += "1. **ALWAYS format teacher/student lists as Markdown tables** for better readability.\n"
                        user_content += "2. Use format: | Name | ID |\n"
                        user_content += "3. Separate header with: |---|---|\n"
                        user_content += "4. Each row: | Teacher/Student Name | ID |\n"
                        user_content += "5. If email was not requested, don't include it in the table.\n\n"
                    
                    # Add concise formatting instructions for announcements (TOKEN OPTIMIZATION - reduced from ~60 lines to ~5 lines)
                    if is_announcement_query:
                        user_content += "\n⚠️ ANNOUNCEMENTS:\n"
                        user_content += "Format: ### [Date]\n**Announcement:** [text]\nSchedule:\n- [time] to [time]: [activity]\n[View Full Announcement](url)\n"
                        user_content += "Fix time ranges (add 'to' between times), grammar, use Markdown. Process data, don't copy-paste.\n"
                        user_content += "If empty: Say 'No announcements for requested date(s)'.\nDO NOT say 'no access'!\n\n"
                    
                if admin_data.get('calendar_data') and is_calendar_query:
                    # Only include calendar if explicitly requested
                    calendar_events = admin_data.get('calendar_data', [])[:10]
                    # Compact format: only essential fields
                    compact_events = [{
                        "title": e.get("summary", ""),
                        "start": e.get("startTime", ""),
                        "end": e.get("endTime", ""),
                        "location": e.get("location", "")
                    } for e in calendar_events]
                    user_content += f"Calendar Events:\n{json.dumps(compact_events, separators=(',', ':'))}\n\n"
            
            # Add concise data processing instructions (TOKEN OPTIMIZATION - only for queries that need it)
            if is_announcement_query or is_coursework_query:
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
            
            # HYBRID MODEL SELECTION: Choose model based on query type and available data
            # GPT-3.5-turbo: For queries with structured data (classroom/calendar/web) - can format/enhance data well at low cost
            # GPT-4: For complex queries without structured data - needs reasoning/generation
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
            
            # Use GPT-3.5 for data-rich queries (95% cheaper), GPT-4 for complex reasoning queries
            if has_structured_data:
                model_name = "gpt-3.5-turbo"  # Data formatting/enhancement - GPT-3.5 is sufficient and much cheaper
                print(f"[Chatbot] 🤖 MODEL SELECTION: GPT-3.5-turbo (Data-Enhanced Query)")
                print(f"[Chatbot] 📊 Data sources available: {', '.join(data_sources)}")
                print(f"[Chatbot] 💰 Cost: ~$0.002-0.003 per query (GPT-3.5 can format existing data efficiently)")
            else:
                model_name = "gpt-4"  # Complex reasoning/generation - needs GPT-4
                print(f"[Chatbot] 🤖 MODEL SELECTION: GPT-4 (Complex Query - No Structured Data)")
                print(f"[Chatbot] 💰 Cost: ~$0.064 per query (GPT-4 needed for reasoning/generation)")
            
            print(f"[Chatbot] 🤖 DEBUG: Using model: {model_name}")
            if model_name == "gpt-3.5-turbo":
                print(f"[Chatbot] 💵 Pricing - Input: $0.0015/1K tokens, Output: $0.002/1K tokens")
            else:
                print(f"[Chatbot] 💵 Pricing - Input: $0.03/1K tokens, Output: $0.06/1K tokens")
            
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,
            )
            
            # Log model used in response
            print(f"[Chatbot] ✅ DEBUG: Response generated successfully using model: {model_name}")
            if hasattr(response, 'model') and response.model:
                print(f"[Chatbot] ✅ DEBUG: OpenAI confirmed model used: {response.model}")
            
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            # Calculate token usage from response (approximate)
            input_tokens_approx = sum(len(msg["content"]) // 4 for msg in messages)
            output_tokens_approx = len(content) // 4 if content else 0
            
            # Calculate cost based on model used
            if model_name == "gpt-3.5-turbo":
                estimated_cost = (input_tokens_approx * 0.0015 / 1000) + (output_tokens_approx * 0.002 / 1000)
                cost_model = "GPT-3.5-turbo"
            else:  # GPT-4
                estimated_cost = (input_tokens_approx * 0.03 / 1000) + (output_tokens_approx * 0.06 / 1000)
                cost_model = "GPT-4"
            
            print(f"[Chatbot] 📊 Attempt {attempt + 1} - Response generated")
            print(f"[Chatbot] 📏 Response length: {len(content) if content else 0} characters")
            print(f"[Chatbot] 📏 Estimated tokens: ~{input_tokens_approx} input + ~{output_tokens_approx} output = ~{input_tokens_approx + output_tokens_approx} total")
            print(f"[Chatbot] 💰 Estimated cost: ~${estimated_cost:.4f} ({cost_model})")
            if has_structured_data and model_name == "gpt-3.5-turbo":
                gpt4_estimated_cost = (input_tokens_approx * 0.03 / 1000) + (output_tokens_approx * 0.06 / 1000)
                savings = gpt4_estimated_cost - estimated_cost
                print(f"[Chatbot] 💵 Cost savings: ~${savings:.4f} (vs GPT-4 would cost ~${gpt4_estimated_cost:.4f})")
            print(f"[Chatbot] ✅ Finish reason: {finish_reason}")
            
            # Log model confirmation
            if hasattr(response, 'model') and response.model:
                print(f"[Chatbot] ✅ DEBUG: OpenAI confirmed model used: {response.model}")
            
            # Check if response is complete
            if content and finish_reason == "stop" and not content.strip().endswith(("of", "and", "the", "in", "to", "for", "with", "by")):
                print(f"[Chatbot] Complete response received on attempt {attempt + 1}")
                return content.strip()
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

            model="gpt-3.5-turbo",

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

            model="gpt-3.5-turbo",

            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],

            temperature=0.3,

        )

        content = response.choices[0].message.content

        # Google Maps embed URL for Prakriti School

        map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3502.123456789!2d77.123456!3d28.123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce4b123456789:0xabcdefabcdefabcd!2sPrakriti%20School!5e0!3m2!1sen!2sin!4v1710000000000!5m2!1sen!2sin"

        return [content.strip() if content else canonical_answer, {"type": "map", "url": map_url}]



    # Step 0.12: YouTube Video Intent Detection

    video_keywords = [

        "video", "show me", "watch", "see", "demonstration", "example", "gardening", "art", "sports", 

        "science", "mindfulness", "meditation", "campus", "facilities", "tour", "performance", 

        "exhibition", "workshop", "activity", "program", "class", "lesson"

    ]

    if any(kw in user_query.lower() for kw in video_keywords):

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
    print("[Chatbot] 🤖 HYBRID MODEL SELECTION: Intelligent cost optimization")
    print("[Chatbot] 📋 Strategy:")
    print("[Chatbot]   • GPT-3.5-turbo: Queries with structured data (Classroom/Calendar/Web)")
    print("[Chatbot]   • GPT-4: Complex queries without structured data (reasoning/generation)")
    print("[Chatbot] 💰 Expected cost: ~70-90% reduction vs using GPT-4 for all queries")
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

                return content.strip()

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

            model="gpt-3.5-turbo",

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

            model="gpt-3.5-turbo",

            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],

            temperature=0.3,

        )

        content = response.choices[0].message.content

        # Google Maps embed URL for Prakriti School

        map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3502.123456789!2d77.123456!3d28.123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce4b123456789:0xabcdefabcdefabcd!2sPrakriti%20School!5e0!3m2!1sen!2sin!4v1710000000000!5m2!1sen!2sin"

        return [content.strip() if content else canonical_answer, {"type": "map", "url": map_url}]



    # Step 0.12: YouTube Video Intent Detection

    video_keywords = [

        "video", "show me", "watch", "see", "demonstration", "example", "gardening", "art", "sports", 

        "science", "mindfulness", "meditation", "campus", "facilities", "tour", "performance", 

        "exhibition", "workshop", "activity", "program", "class", "lesson"

    ]

    if any(kw in user_query.lower() for kw in video_keywords):

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
    print("[Chatbot] 🤖 HYBRID MODEL SELECTION: Intelligent cost optimization")
    print("[Chatbot] 📋 Strategy:")
    print("[Chatbot]   • GPT-3.5-turbo: Queries with structured data (Classroom/Calendar/Web)")
    print("[Chatbot]   • GPT-4: Complex queries without structured data (reasoning/generation)")
    print("[Chatbot] 💰 Expected cost: ~70-90% reduction vs using GPT-4 for all queries")
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

                return content.strip()

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