from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import json
import asyncio
from datetime import datetime, timedelta, timezone
import os

from ..core.database import get_db
from ..models.admin import Admin, GoogleIntegration, ClassroomData, CalendarData
# Auth functions removed - using Supabase authentication in frontend
from ..services.supabase_admin import SupabaseAdminService
from ..services.google_dwd_service import get_dwd_service
from ..services.embedding_generator import get_embedding_generator
from ..services.auto_sync_scheduler import get_auto_sync_scheduler
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Sync status tracking for bulk sync operations
_sync_status = {
    "is_running": False,
    "started_at": None,
    "completed_at": None,
    "total_users": 0,
    "users_synced": 0,
    "users_failed": 0,
    "error": None
}

# Pydantic models for request/response
class AdminLogin(BaseModel):
    email: str
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str
    admin: dict

# Admin login endpoint removed - using Supabase authentication in frontend
# @router.post("/login", response_model=AdminLoginResponse)
# async def admin_login(login_data: AdminLogin, db: Session = Depends(get_db)):
#     """Login endpoint for admin users."""
#     admin = authenticate_admin(login_data.email, login_data.password, db)
#     if not admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid email or password"
#         )
#     
#     access_token = create_access_token(data={"sub": admin.email})
#     
#     return AdminLoginResponse(
#         access_token=access_token,
#         token_type="bearer",
#         admin={
#             "id": admin.id,
#             "email": admin.email,
#             "name": admin.name,
#             "role": admin.role,
#             "is_active": admin.is_active
#         }
#     )

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# IMPORTANT: Redirect URI MUST point to FRONTEND Next.js page, NOT backend API
# Google redirects here, then the Next.js page calls /api/admin/callback with user's email
# DO NOT use http://localhost:8000/api/admin/callback - that's the backend route
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/admin/callback")

# Ensure redirect URI always points to frontend, never backend
if GOOGLE_REDIRECT_URI and "localhost:8000" in GOOGLE_REDIRECT_URI:
    print(f"⚠️ WARNING: GOOGLE_REDIRECT_URI points to backend ({GOOGLE_REDIRECT_URI})")
    print(f"⚠️ This will cause OAuth to fail. Setting to frontend URL instead.")
    GOOGLE_REDIRECT_URI = "http://localhost:3000/admin/callback"

# Google API scopes - VALID scopes only (some scopes like coursework.readonly are deprecated)
GOOGLE_CLASSROOM_SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",  # Required: Course list and details
    "https://www.googleapis.com/auth/classroom.rosters.readonly",  # Required: Students & teachers
    # NOTE: classroom.coursework.readonly is INVALID - Google has deprecated this scope
    # Coursework data may still be accessible via classroom.courses.readonly in some cases
    # NOTE: classroom.student-submissions.readonly is INVALID - Google has deprecated this scope
    # Submissions may require alternative approach or different permissions
    "https://www.googleapis.com/auth/classroom.announcements.readonly",  # Required: Course announcements
]

GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly"
]




# Sync functions removed - using Supabase authentication in frontend
# @router.post("/sync/classroom")
# async def sync_classroom_data(
#     db: Session = Depends(get_db),
#     current_user: Admin = Depends(get_current_user)
# ):
#     """Sync Google Classroom data"""
#     if not current_user.role or current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required")
#     
#     admin = db.query(Admin).filter(Admin.email == current_user.email).first()
#     if not admin or not admin.google_classroom_enabled:
#         raise HTTPException(status_code=400, detail="Google Classroom not integrated")
#     
#     integration = db.query(GoogleIntegration).filter(
#         GoogleIntegration.admin_id == admin.id,
#         GoogleIntegration.service_type == "classroom",
#         GoogleIntegration.is_active == True
#     ).first()
#     
#     if not integration:
#         raise HTTPException(status_code=400, detail="No active Classroom integration found")
#     
#     try:
#         # Refresh token if needed
#         if integration.token_expires_at <= datetime.utcnow():
#             await refresh_google_token(integration, db)
#         
#         # Fetch courses from Google Classroom API
#         async with httpx.AsyncClient() as client:
#             headers = {"Authorization": f"Bearer {integration.access_token}"}
#             response = await client.get(
#                 "https://classroom.googleapis.com/v1/courses",
#                 headers=headers
#             )
#             response.raise_for_status()
#             courses_data = response.json()
#         
#         # Store/update courses in database
#         courses_synced = 0
#         for course in courses_data.get("courses", []):
#             existing_course = db.query(ClassroomData).filter(
#                 ClassroomData.admin_id == admin.id,
#                 ClassroomData.course_id == course["id"]
#             ).first()
#             
#             if existing_course:
#                 # Update existing course
#                 existing_course.course_name = course.get("name", "")
#                 existing_course.course_description = course.get("description", "")
#                 existing_course.course_room = course.get("room", "")
#                 existing_course.course_section = course.get("section", "")
#                 existing_course.course_state = course.get("courseState", "")
#                 existing_course.teacher_email = course.get("teacherEmail", "")
#                 existing_course.raw_data = course
#                 existing_course.last_synced = datetime.utcnow()
#             else:
#                 # Create new course
#                 new_course = ClassroomData(
#                     admin_id=admin.id,
#                     course_id=course["id"],
#                     course_name=course.get("name", ""),
#                     course_description=course.get("description", ""),
#                     course_room=course.get("room", ""),
#                     course_section=course.get("section", ""),
#                     course_state=course.get("courseState", ""),
#                     teacher_email=course.get("teacherEmail", ""),
#                     raw_data=course
#                 )
#                 db.add(new_course)
#             
#             courses_synced += 1
#         
#         db.commit()
#         
#         return {
#             "success": True,
#             "message": f"Synced {courses_synced} courses from Google Classroom",
#             "courses_synced": courses_synced
#         }
#         
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=400, detail=f"Google Classroom API error: {e.response.text}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

# @router.post("/sync/calendar")
# async def sync_calendar_data(
#     db: Session = Depends(get_db),
#     current_user: Admin = Depends(get_current_user)
# ):
#     """Sync Google Calendar data"""
#     if not current_user.role or current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required")
#     
#     admin = db.query(Admin).filter(Admin.email == current_user.email).first()
#     if not admin or not admin.google_calendar_enabled:
#         raise HTTPException(status_code=400, detail="Google Calendar not integrated")
#     
#     integration = db.query(GoogleIntegration).filter(
#         GoogleIntegration.admin_id == admin.id,
#         GoogleIntegration.service_type == "calendar",
#         GoogleIntegration.is_active == True
#     ).first()
#     
#     if not integration:
#         raise HTTPException(status_code=400, detail="No active Calendar integration found")
#     
#     try:
#         # Refresh token if needed
#         if integration.token_expires_at <= datetime.utcnow():
#             await refresh_google_token(integration, db)
#         
#         # Fetch events from Google Calendar API
#         time_min = datetime.utcnow().isoformat() + "Z"
#         time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
#         
#         async with httpx.AsyncClient() as client:
#             headers = {"Authorization": f"Bearer {integration.access_token}"}
#             response = await client.get(
#                 f"https://www.googleapis.com/calendar/v3/calendars/primary/events",
#                 headers=headers,
#                 params={
#                     "timeMin": time_min,
#                     "timeMax": time_max,
#                     "singleEvents": True,
#                     "orderBy": "startTime"
#                 }
#             )
#             response.raise_for_status()
#             events_data = response.json()
#         
#         # Store/update events in database
#         events_synced = 0
#         for event in events_data.get("items", []):
#             existing_event = db.query(CalendarData).filter(
#                 CalendarData.admin_id == admin.id,
#                 CalendarData.event_id == event["id"]
#             ).first()
#             
#             start_time = datetime.fromisoformat(
#                 event["start"].get("dateTime", event["start"].get("date", "")).replace("Z", "+00:00")
#             )
#             end_time = datetime.fromisoformat(
#                 event["end"].get("dateTime", event["end"].get("date", "")).replace("Z", "+00:00")
#             )
#             
#             if existing_event:
#                 # Update existing event
#                 existing_event.event_title = event.get("summary", "")
#                 existing_event.event_description = event.get("description", "")
#                 existing_event.event_start = start_time
#                 existing_event.event_end = end_time
#                 existing_event.event_location = event.get("location", "")
#                 existing_event.event_status = event.get("status", "")
#                 existing_event.raw_data = event
#                 existing_event.last_synced = datetime.utcnow()
#             else:
#                 # Create new event
#                 new_event = CalendarData(
#                     admin_id=admin.id,
#                     event_id=event["id"],
#                     event_title=event.get("summary", ""),
#                     event_description=event.get("description", ""),
#                     event_start=start_time,
#                     event_end=end_time,
#                     event_location=event.get("location", ""),
#                     event_status=event.get("status", ""),
#                     calendar_id="primary",
#                     raw_data=event
#                 )
#                 db.add(new_event)
#             
#             events_synced += 1
#         
#         db.commit()
#         
#         return {
#             "success": True,
#             "message": f"Synced {events_synced} events from Google Calendar",
#             "events_synced": events_synced
#         }
#         
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=400, detail=f"Google Calendar API error: {e.response.text}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

@router.get("/data/classroom")
async def get_classroom_data(email: Optional[str] = None):
    """Get synced classroom data for chatbot"""
    try:
        admin_service = SupabaseAdminService()
        admin = None
        if email:
            admin = admin_service.get_admin(email)
        
        if not admin:
            admin = admin_service.get_first_admin()
        
        if not admin:
            print("No admin profile found for classroom data")
            return {"courses": []}
        
        courses = admin_service.get_classroom_data(admin['id'])
        
        return {
            "courses": [
                {
                    "id": course.get('course_id', ''),
                    "name": course.get('course_name', ''),
                    "description": course.get('course_description', ''),
                    "room": course.get('course_room', ''),
                    "section": course.get('course_section', ''),
                    "state": course.get('course_state', ''),
                    "teacher_email": course.get('teacher_email', ''),
                    "student_count": course.get('student_count', 0),
                    "last_synced": course.get('last_synced', '')
                }
                for course in courses
            ]
        }
    except Exception as e:
        print(f"Error getting classroom data: {e}")
        return {"courses": []}

@router.post("/sync/website")
async def sync_website_data(email: Optional[str] = None):
    """Sync website data by running daily_crawl_essential.py to update all essential pages"""
    try:
        import sys
        import os
        from datetime import datetime, timedelta
        
        # Add backend directory to path to import daily_crawl_essential
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        
        from daily_crawl_essential import crawl_essential_pages
        from supabase_config import get_supabase_client
        
        print(f"[Admin] Website sync requested by: {email or 'unknown'}")
        
        supabase = get_supabase_client()
        
        if not supabase:
            return {
                "success": False,
                "message": "Supabase not available",
                "stats": {}
            }
        
        # Clear old cache entries (older than 1 hour) to force fresh crawl
        cutoff_date = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        # Mark old cache entries as inactive
        try:
            supabase.table('web_crawler_data').update({'is_active': False}).lt('crawled_at', cutoff_date).execute()
            supabase.table('search_cache').update({'is_active': False}).lt('expires_at', datetime.utcnow().isoformat()).execute()
            print(f"[Admin] ✅ Cleared old cache entries")
        except Exception as e:
            print(f"[Admin] Warning: Error clearing cache: {e}")
        
        # Run the daily crawl essential script
        try:
            print(f"[Admin] Running daily_crawl_essential.py to crawl all essential pages...")
            crawl_essential_pages()
            print(f"[Admin] ✅ Daily crawl completed successfully")
            
            # Count pages crawled (check web_crawler_data updated in last hour)
            pages_result = supabase.table('web_crawler_data').select('id').eq('is_active', True).gte('crawled_at', cutoff_date).execute()
            pages_count = len(pages_result.data) if pages_result.data else 0
            
            # Count team members updated
            team_members_result = supabase.table('team_member_data').select('id').eq('is_active', True).gte('crawled_at', cutoff_date).execute()
            team_members_count = len(team_members_result.data) if team_members_result.data else 0
            
            return {
                "success": True,
                "message": f"Website data synced successfully. {pages_count} pages and {team_members_count} team members updated.",
                "stats": {
                    "pages_crawled": pages_count,
                    "team_members": team_members_count,
                    "cache_cleared": True
                },
                "summary": {
                    "pages": pages_count,
                    "team_members": team_members_count
                }
            }
        except Exception as e:
            print(f"[Admin] Error during crawl: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error during crawl: {str(e)}",
                "stats": {}
            }
            
    except Exception as e:
        print(f"[Admin] Error syncing website data: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Sync error: {str(e)}",
            "stats": {}
        }

@router.get("/data/website")
async def get_website_page_data(url: Optional[str] = None):
    """Get synced website page data"""
    try:
        from supabase_config import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            return {"title": "", "crawled_at": None}
        
        if not url:
            return {"title": "", "crawled_at": None}
        
        # Get most recent active record for this URL
        result = supabase.table('web_crawler_data').select('title, crawled_at').eq('url', url).eq('is_active', True).order('crawled_at', desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return {
                "title": result.data[0].get('title', ''),
                "crawled_at": result.data[0].get('crawled_at')
            }
        
        return {"title": "", "crawled_at": None}
    except Exception as e:
        print(f"Error getting website page data: {e}")
        return {"title": "", "crawled_at": None}

@router.get("/data/calendar")
async def get_calendar_data(email: Optional[str] = None):
    """Get synced calendar data for chatbot"""
    try:
        admin_service = SupabaseAdminService()
        admin = None
        if email:
            admin = admin_service.get_admin(email)
        
        if not admin:
            admin = admin_service.get_first_admin()
        
        if not admin:
            print("No admin profile found for calendar data")
            return {"events": []}
        
        events = admin_service.get_calendar_data(admin['id'])
        
        return {
            "events": [
                {
                    "id": event.get('event_id', ''),
                    "title": event.get('event_title', ''),
                    "description": event.get('event_description', ''),
                    "start": event.get('event_start', ''),
                    "end": event.get('event_end', ''),
                    "location": event.get('event_location', ''),
                    "status": event.get('event_status', ''),
                    "last_synced": event.get('last_synced', '')
                }
                for event in events
            ]
        }
    except Exception as e:
        print(f"Error getting calendar data: {e}")
        return {"events": []}

async def refresh_google_token(integration: GoogleIntegration, db: Session):
    """Refresh Google OAuth token"""
    try:
        token_data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": integration.refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data
            )
            response.raise_for_status()
            tokens = response.json()
        
        # Update tokens
        integration.access_token = tokens["access_token"]
        integration.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
        
        db.commit()
        
    except Exception as e:
        # Mark integration as inactive if refresh fails
        integration.is_active = False
        db.commit()
        raise e
# DWD Status Endpoint
@router.get("/dwd/status")
async def get_dwd_status():
    """Check if DWD service is available and configured"""
    try:
        dwd_service = get_dwd_service()
        if not dwd_service:
            return {
                "available": False,
                "workspace_domain": os.getenv('GOOGLE_WORKSPACE_DOMAIN', 'not configured'),
                "service_account_path": os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'not configured'),
                "error": "DWD service not available. Check GOOGLE_APPLICATION_CREDENTIALS path and service account file."
            }
        
        # Read service account file to get Client ID
        client_id = None
        service_account_email = None
        project_id = None
        try:
            import json
            service_account_path = dwd_service.service_account_path
            if os.path.exists(service_account_path):
                with open(service_account_path, 'r') as f:
                    service_account_info = json.load(f)
                    client_id = service_account_info.get('client_id')
                    service_account_email = service_account_info.get('client_email')
                    project_id = service_account_info.get('project_id')
        except Exception as e:
            print(f"Warning: Could not read service account file: {e}")
        
        # Check workspace domain
        workspace_domain = dwd_service.workspace_domain
        expected_domain = "learners.prakriti.org.in"
        domain_matches = workspace_domain == expected_domain
        
        return {
            "available": True,
            "workspace_domain": workspace_domain,
            "workspace_domain_correct": domain_matches,
            "expected_domain": expected_domain,
            "service_account_path": dwd_service.service_account_path,
            "client_id": client_id,
            "service_account_email": service_account_email,
            "project_id": project_id,
            "message": "DWD service is configured and ready",
            "warnings": [
                f"Workspace domain mismatch: Configured as '{workspace_domain}' but expected '{expected_domain}'. Set GOOGLE_WORKSPACE_DOMAIN=learners.prakriti.org.in" if not domain_matches else None
            ],
            "note": f"Verify Client ID '{client_id}' is authorized in Google Admin Console with the required scopes."
        }
    except Exception as e:
        return {
            "available": False,
            "workspace_domain": os.getenv('GOOGLE_WORKSPACE_DOMAIN', 'not configured'),
            "service_account_path": os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'not configured'),
            "error": str(e)
        }

# DWD Sync Endpoint
class DWDSyncRequest(BaseModel):
    user_email: str

class GradeRoleSyncRequest(BaseModel):
    service: str
    email: Optional[str] = None

@router.post("/sync-dwd/{service}")
async def sync_dwd(service: str, request: DWDSyncRequest):
    """
    Sync Google Classroom/Calendar data using Domain-Wide Delegation (DWD)
    Requires: user_email in request body (email of the user to sync data for)
    """
    if service not in ["classroom", "calendar"]:
        raise HTTPException(status_code=400, detail="Service must be 'classroom' or 'calendar'")
    
    user_email = request.user_email
    if not user_email:
        raise HTTPException(status_code=400, detail="user_email is required")
    
    # Get DWD service
    dwd_service = get_dwd_service()
    if not dwd_service:
        raise HTTPException(
            status_code=500, 
            detail="DWD service not available. Check GOOGLE_APPLICATION_CREDENTIALS path and service account file."
        )
    
    # Get user profile to find user_id
    admin_service = SupabaseAdminService()
    user_profile = admin_service.get_user_profile_by_email(user_email)
    
    if not user_profile:
        raise HTTPException(status_code=404, detail=f"User profile not found for {user_email}")
    
    user_id = user_profile.get('user_id') or user_profile.get('id')
    if not user_id:
        raise HTTPException(status_code=404, detail=f"user_id not found for {user_email}")
    
    # Get Supabase client
    from supabase_config import get_supabase_client
    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not available")
    
    sync_stats = {
        "courses": {"created": 0, "updated": 0},
        "teachers": {"created": 0, "updated": 0},
        "students": {"created": 0, "updated": 0},
        "coursework": {"created": 0, "updated": 0},
        "submissions": {"created": 0, "updated": 0},
        "announcements": {"created": 0, "updated": 0},
        "calendars": {"created": 0, "updated": 0},
        "events": {"created": 0, "updated": 0}
    }
    
    def parse_google_timestamp(timestamp: str = None) -> str:
        """Parse Google timestamp to ISO format"""
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).isoformat()
        except:
            return None
    
    try:
        if service == "classroom":
            print(f"🔍 DWD: Fetching Classroom data for {user_email}...")
            
            # Fetch courses
            courses = dwd_service.fetch_user_courses(user_email)
            print(f"🔍 DWD: Found {len(courses)} courses")
            
            # Process each course
            for course in courses:
                course_id = course.get('id')
                if not course_id:
                    continue
                
                print(f"🔍 DWD: Processing course: {course.get('name', 'Unknown')} ({course_id})")
                
                # Prepare course data
                course_data = {
                    "user_id": user_id,
                    "course_id": course_id,
                    "name": course.get('name', ''),
                    "description": course.get('description'),
                    "section": course.get('section'),
                    "room": course.get('room'),
                    "owner_id": course.get('ownerId'),
                    "enrollment_code": course.get('enrollmentCode'),
                    "course_state": course.get('courseState'),
                    "alternate_link": course.get('alternateLink'),
                    "teacher_group_email": course.get('teacherGroupEmail'),
                    "course_group_email": course.get('courseGroupEmail'),
                    "guardians_enabled": course.get('guardiansEnabled', False),
                    "calendar_enabled": bool(course.get('calendarId')),
                    "max_rosters": course.get('maxRosters'),
                    "course_material_sets": course.get('courseMaterialSets'),
                    "gradebook_settings": course.get('gradebookSettings'),
                    "description_heading": course.get('descriptionHeading'),
                    "update_time": parse_google_timestamp(course.get('updateTime')),
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Upsert course - check if exists first (use limit(1) instead of single() to handle 0 rows)
                existing_course_result = supabase.table('google_classroom_courses').select('id').eq('user_id', user_id).eq('course_id', course_id).limit(1).execute()
                
                db_course_id = None
                if existing_course_result.data and len(existing_course_result.data) > 0:
                    # Course exists - update it
                    existing_course_id = existing_course_result.data[0]['id']
                    supabase.table('google_classroom_courses').update(course_data).eq('id', existing_course_id).execute()
                    db_course_id = existing_course_id
                    sync_stats["courses"]["updated"] += 1
                else:
                    # Course doesn't exist - insert it
                    result = supabase.table('google_classroom_courses').insert(course_data).execute()
                    if result.data and len(result.data) > 0:
                        db_course_id = result.data[0].get('id')
                        sync_stats["courses"]["created"] += 1
                
                if not db_course_id:
                    # Fallback: try to get ID
                    result = supabase.table('google_classroom_courses').select('id').eq('user_id', user_id).eq('course_id', course_id).limit(1).execute()
                    if result.data and len(result.data) > 0:
                        db_course_id = result.data[0]['id']
                    else:
                        print(f"⚠️ DWD: Could not get database course ID for {course_id}")
                        continue
                
                # Fetch and store teachers
                try:
                    teachers = dwd_service.fetch_course_teachers(user_email, course_id)
                    for teacher in teachers:
                        teacher_data = {
                            "course_id": db_course_id,
                            "user_id": teacher.get('userId', ''),
                            "course_user_id": f"{course_id}_{teacher.get('userId', '')}",
                            "profile": teacher.get('profile', {})
                        }
                        
                        existing = supabase.table('google_classroom_teachers').select('id').eq('course_id', db_course_id).eq('course_user_id', teacher_data['course_user_id']).limit(1).execute()
                        
                        if existing.data and len(existing.data) > 0:
                            supabase.table('google_classroom_teachers').update(teacher_data).eq('id', existing.data['id']).execute()
                            sync_stats["teachers"]["updated"] += 1
                        else:
                            supabase.table('google_classroom_teachers').insert(teacher_data).execute()
                            sync_stats["teachers"]["created"] += 1
                except Exception as e:
                    print(f"⚠️ DWD: Error fetching teachers for course {course_id}: {e}")
                
                # Fetch and store students
                try:
                    students = dwd_service.fetch_course_students(user_email, course_id)
                    for student in students:
                        student_data = {
                            "course_id": db_course_id,
                            "user_id": student.get('userId', ''),
                            "course_user_id": f"{course_id}_{student.get('userId', '')}",
                            "profile": student.get('profile', {}),
                            "student_work_folder": student.get('studentWorkFolder')
                        }
                        
                        existing = supabase.table('google_classroom_students').select('id').eq('course_id', db_course_id).eq('course_user_id', student_data['course_user_id']).limit(1).execute()
                        
                        if existing.data and len(existing.data) > 0:
                            supabase.table('google_classroom_students').update(student_data).eq('id', existing.data['id']).execute()
                            sync_stats["students"]["updated"] += 1
                        else:
                            supabase.table('google_classroom_students').insert(student_data).execute()
                            sync_stats["students"]["created"] += 1
                except Exception as e:
                    print(f"⚠️ DWD: Error fetching students for course {course_id}: {e}")
                
                # Fetch and store coursework
                try:
                    coursework_list = dwd_service.fetch_course_coursework(user_email, course_id)
                    for cw in coursework_list:
                        cw_id = cw.get('id')
                        if not cw_id:
                            continue
                        
                        due_date = None
                        if cw.get('dueDate'):
                            due_date_str = f"{cw['dueDate'].get('year', 2000)}-{cw['dueDate'].get('month', 1):02d}-{cw['dueDate'].get('day', 1):02d}"
                            due_date = parse_google_timestamp(f"{due_date_str}T00:00:00Z")
                        elif cw.get('dueTime'):
                            due_date = parse_google_timestamp(cw['dueTime'])
                        
                        coursework_data = {
                            "course_id": db_course_id,
                            "coursework_id": cw_id,
                            "title": cw.get('title', ''),
                            "description": cw.get('description'),
                            "materials": cw.get('materials'),
                            "state": cw.get('state'),
                            "alternate_link": cw.get('alternateLink'),
                            "creation_time": parse_google_timestamp(cw.get('creationTime')),
                            "update_time": parse_google_timestamp(cw.get('updateTime')),
                            "due_date": due_date,
                            "due_time": cw.get('dueTime'),
                            "max_points": float(cw['maxPoints'].get('value', 0)) if cw.get('maxPoints') else None,
                            "work_type": cw.get('workType'),
                            "associated_with_developer": cw.get('associatedWithDeveloper', False),
                            "assignee_mode": cw.get('assigneeMode'),
                            "individual_students_options": cw.get('individualStudentsOptions'),
                            "submission_modification_mode": cw.get('submissionModificationMode'),
                            "creator_user_id": cw.get('creatorUserId'),
                            "topic_id": cw.get('topicId'),
                            "grade_category": cw.get('gradeCategory'),
                            "assignment": cw.get('assignment'),
                            "multiple_choice_question": cw.get('multipleChoiceQuestion'),
                            "last_synced_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        existing = supabase.table('google_classroom_coursework').select('id').eq('course_id', db_course_id).eq('coursework_id', cw_id).limit(1).execute()
                        
                        cw_db_id = None
                        if existing.data and len(existing.data) > 0:
                            supabase.table('google_classroom_coursework').update(coursework_data).eq('id', existing.data['id']).execute()
                            cw_db_id = existing.data['id']
                            sync_stats["coursework"]["updated"] += 1
                        else:
                            result = supabase.table('google_classroom_coursework').insert(coursework_data).execute()
                            if result.data and len(result.data) > 0:
                                cw_db_id = result.data[0].get('id')
                                sync_stats["coursework"]["created"] += 1
                        
                        # Generate embedding for coursework
                        if cw_db_id:
                            try:
                                embedding_gen = get_embedding_generator()
                                embedding_gen.generate_for_coursework(cw_db_id)
                            except Exception as e:
                                print(f"⚠️ DWD: Failed to generate embedding for coursework {cw_id}: {e}")
                        
                        # Fetch and store submissions
                        if cw_db_id:
                            try:
                                submissions = dwd_service.fetch_course_submissions(user_email, course_id, cw_id)
                                for sub in submissions:
                                    submission_data = {
                                        "coursework_id": cw_db_id,
                                        "submission_id": sub.get('id', ''),
                                        "course_id": course_id,
                                        "coursework_id_google": cw_id,
                                        "user_id": sub.get('userId', ''),
                                        "state": sub.get('state'),
                                        "alternate_link": sub.get('alternateLink'),
                                        "assigned_grade": float(sub['assignedGrade']) if sub.get('assignedGrade') else None,
                                        "draft_grade": float(sub['draftGrade']) if sub.get('draftGrade') else None,
                                        "course_work_type": sub.get('courseWorkType'),
                                        "associated_with_developer": sub.get('associatedWithDeveloper', False),
                                        "submission_history": sub.get('submissionHistory'),
                                        "last_synced_at": datetime.now(timezone.utc).isoformat()
                                    }
                                    
                                    existing = supabase.table('google_classroom_submissions').select('id').eq('coursework_id', cw_db_id).eq('submission_id', submission_data['submission_id']).limit(1).execute()
                                    
                                    if existing.data and len(existing.data) > 0:
                                        supabase.table('google_classroom_submissions').update(submission_data).eq('id', existing.data['id']).execute()
                                        sync_stats["submissions"]["updated"] += 1
                                    else:
                                        supabase.table('google_classroom_submissions').insert(submission_data).execute()
                                        sync_stats["submissions"]["created"] += 1
                            except Exception as e:
                                print(f"⚠️ DWD: Error fetching submissions for coursework {cw_id}: {e}")
                except Exception as e:
                    print(f"⚠️ DWD: Error fetching coursework for course {course_id}: {e}")
                
                # Fetch and store announcements
                try:
                    announcements = dwd_service.fetch_course_announcements(user_email, course_id)
                    for ann in announcements:
                        announcement_data = {
                            "course_id": db_course_id,
                            "announcement_id": ann.get('id', ''),
                            "text": ann.get('text'),
                            "materials": ann.get('materials'),
                            "state": ann.get('state'),
                            "alternate_link": ann.get('alternateLink'),
                            "creation_time": parse_google_timestamp(ann.get('creationTime')),
                            "update_time": parse_google_timestamp(ann.get('updateTime')),
                            "scheduled_time": parse_google_timestamp(ann.get('scheduledTime')),
                            "assignee_mode": ann.get('assigneeMode'),
                            "individual_students_options": ann.get('individualStudentsOptions'),
                            "creator_user_id": ann.get('creatorUserId'),
                            "course_work_type": ann.get('courseWorkType'),
                            "last_synced_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        existing = supabase.table('google_classroom_announcements').select('id').eq('course_id', db_course_id).eq('announcement_id', announcement_data['announcement_id']).limit(1).execute()
                        
                        ann_db_id = None
                        if existing.data and len(existing.data) > 0:
                            supabase.table('google_classroom_announcements').update(announcement_data).eq('id', existing.data['id']).execute()
                            ann_db_id = existing.data['id']
                            sync_stats["announcements"]["updated"] += 1
                        else:
                            result = supabase.table('google_classroom_announcements').insert(announcement_data).execute()
                            if result.data and len(result.data) > 0:
                                ann_db_id = result.data[0].get('id')
                                sync_stats["announcements"]["created"] += 1
                        
                        # Generate embedding for announcement
                        if ann_db_id:
                            try:
                                embedding_gen = get_embedding_generator()
                                embedding_gen.generate_for_announcement(ann_db_id)
                            except Exception as e:
                                print(f"⚠️ DWD: Failed to generate embedding for announcement {ann.get('id', 'Unknown')}: {e}")
                except Exception as e:
                    print(f"⚠️ DWD: Error fetching announcements for course {course_id}: {e}")
            
            return {
                "success": True,
                "message": f"Synced Google Classroom data for {user_email}",
                "stats": sync_stats,
                "summary": {
                    "courses": sync_stats["courses"]["created"] + sync_stats["courses"]["updated"],
                    "teachers": sync_stats["teachers"]["created"] + sync_stats["teachers"]["updated"],
                    "students": sync_stats["students"]["created"] + sync_stats["students"]["updated"],
                    "announcements": sync_stats["announcements"]["created"] + sync_stats["announcements"]["updated"],
                    "coursework": sync_stats["coursework"]["created"] + sync_stats["coursework"]["updated"],
                    "submissions": sync_stats["submissions"]["created"] + sync_stats["submissions"]["updated"]
                }
            }
        
        elif service == "calendar":
            print(f"🔍 DWD: Fetching Calendar data for {user_email}...")
            
            # Fetch calendars
            calendars = dwd_service.fetch_user_calendars(user_email)
            print(f"🔍 DWD: Found {len(calendars)} calendars")
            
            for cal in calendars:
                cal_id = cal.get('id')
                if not cal_id:
                    continue
                
                calendar_data = {
                    "user_id": user_id,
                    "calendar_id": cal_id,
                    "summary": cal.get('summary'),
                    "description": cal.get('description'),
                    "location": cal.get('location'),
                    "timezone": cal.get('timeZone'),
                    "color_id": cal.get('colorId'),
                    "background_color": cal.get('backgroundColor'),
                    "foreground_color": cal.get('foregroundColor'),
                    "access_role": cal.get('accessRole'),
                    "selected": cal.get('selected', True),
                    "primary_calendar": cal_id == 'primary',
                    "deleted": cal.get('deleted', False),
                    "conference_properties": cal.get('conferenceProperties'),
                    "notification_settings": cal.get('notificationSettings'),
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Check if calendar exists - use limit(1) instead of single() to handle 0 rows
                existing_result = supabase.table('google_calendar_calendars').select('id').eq('user_id', user_id).eq('calendar_id', cal_id).limit(1).execute()
                
                if existing_result.data and len(existing_result.data) > 0:
                    # Calendar exists - update it
                    existing_id = existing_result.data[0]['id']
                    supabase.table('google_calendar_calendars').update(calendar_data).eq('id', existing_id).execute()
                    sync_stats["calendars"]["updated"] += 1
                else:
                    # Calendar doesn't exist - insert it
                    supabase.table('google_calendar_calendars').insert(calendar_data).execute()
                    sync_stats["calendars"]["created"] += 1
                
                # Fetch events for this calendar
                try:
                    events = dwd_service.fetch_calendar_events(user_email, cal_id)
                    for event in events:
                        event_id = event.get('id')
                        if not event_id:
                            continue
                        
                        # Parse start/end times
                        start_time = None
                        end_time = None
                        all_day = False
                        
                        if event.get('start'):
                            if event['start'].get('dateTime'):
                                start_time = parse_google_timestamp(event['start']['dateTime'])
                            elif event['start'].get('date'):
                                start_time = parse_google_timestamp(f"{event['start']['date']}T00:00:00Z")
                                all_day = True
                        
                        if event.get('end'):
                            if event['end'].get('dateTime'):
                                end_time = parse_google_timestamp(event['end']['dateTime'])
                            elif event['end'].get('date'):
                                end_time = parse_google_timestamp(f"{event['end']['date']}T00:00:00Z")
                        
                        event_data = {
                            "user_id": user_id,
                            "event_id": event_id,
                            "calendar_id": cal_id,
                            "summary": event.get('summary'),
                            "description": event.get('description'),
                            "location": event.get('location'),
                            "start_time": start_time,
                            "end_time": end_time,
                            "all_day": all_day,
                            "timezone": event.get('start', {}).get('timeZone') if not all_day else None,
                            "recurrence": event.get('recurrence'),
                            "attendees": event.get('attendees'),
                            "creator": event.get('creator'),
                            "organizer": event.get('organizer'),
                            "html_link": event.get('htmlLink'),
                            "hangout_link": event.get('hangoutLink'),
                            "conference_data": event.get('conferenceData'),
                            "visibility": event.get('visibility'),
                            "transparency": event.get('transparency'),
                            "status": event.get('status'),
                            "event_type": event.get('eventType'),
                            "color_id": event.get('colorId'),
                            "last_synced_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        existing = supabase.table('google_calendar_events').select('id').eq('user_id', user_id).eq('event_id', event_id).limit(1).execute()
                        
                        if existing.data and len(existing.data) > 0:
                            supabase.table('google_calendar_events').update(event_data).eq('id', existing.data['id']).execute()
                            sync_stats["events"]["updated"] += 1
                        else:
                            supabase.table('google_calendar_events').insert(event_data).execute()
                            sync_stats["events"]["created"] += 1
                except Exception as e:
                    print(f"⚠️ DWD: Error fetching events for calendar {cal_id}: {e}")
            
            return {
                "success": True,
                "message": f"Synced Google Calendar data for {user_email}",
                "stats": sync_stats,
                "summary": {
                    "calendars": sync_stats["calendars"]["created"] + sync_stats["calendars"]["updated"],
                    "events": sync_stats["events"]["created"] + sync_stats["events"]["updated"]
                }
            }
    
    except Exception as e:
        print(f"❌ DWD: Sync failed for {user_email}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Extract meaningful error message
        error_detail = str(e)
        error_type = "unknown"
        
        # Get Client ID for error messages
        client_id_for_error = "N/A"
        try:
            dwd_service = get_dwd_service()
            if dwd_service:
                client_id_for_error = dwd_service._get_client_id()
        except:
            pass
        
        # Categorize error types and provide specific guidance
        if 'invalid_scope' in error_detail.lower() and 'empty or missing scope not allowed' in error_detail.lower():
            error_type = "invalid_scope"
            error_detail = (
                f"❌ Invalid scope error: Empty or missing scope not allowed.\n\n"
                f"This means the Client ID authorization in Admin Console is incorrect or missing.\n\n"
                f"🔧 TROUBLESHOOTING STEPS:\n"
                f"1. Go to: https://admin.google.com → Security → API Controls → Domain-wide Delegation\n"
                f"2. Verify Client ID: {client_id_for_error} is authorized\n"
                f"3. Ensure EXACTLY these 5 scopes are authorized (one per line, no typos):\n"
                f"   • https://www.googleapis.com/auth/classroom.courses.readonly\n"
                f"   • https://www.googleapis.com/auth/classroom.rosters.readonly\n"
                f"   • https://www.googleapis.com/auth/classroom.announcements.readonly\n"
                f"   • https://www.googleapis.com/auth/calendar.readonly\n"
                f"   • https://www.googleapis.com/auth/calendar.events.readonly\n"
                f"4. Remove any other scopes (only these 5)\n"
                f"5. Ensure API Access Control is set to 'Unrestricted'\n"
                f"6. Wait 15-30 minutes after authorization for propagation\n\n"
                f"📄 See: backend/DWD_ADMIN_CONSOLE_SETUP.md for detailed instructions"
            )
        elif 'unauthorized_client' in error_detail.lower():
            error_type = "unauthorized_client"
            error_detail = (
                f"❌ Unauthorized client error: Client is not authorized.\n\n"
                f"🔧 TROUBLESHOOTING STEPS:\n"
                f"1. Go to: https://admin.google.com → Security → API Controls → Domain-wide Delegation\n"
                f"2. Verify Client ID: {client_id_for_error} matches exactly (no spaces, no typos)\n"
                f"3. Ensure all 5 scopes are authorized exactly as shown\n"
                f"4. Wait 15-30 minutes for propagation\n\n"
                f"📄 See: backend/DWD_ADMIN_CONSOLE_SETUP.md for detailed instructions"
            )
        elif 'access_denied' in error_detail.lower() or 'not authorized' in error_detail.lower():
            error_type = "access_denied"
            if isinstance(e, tuple) and len(e) >= 2:
                # Extract error description from tuple format
                error_info = e[1] if isinstance(e[1], dict) else {}
                error_desc = error_info.get('error_description', error_info.get('error', 'Requested client not authorized'))
                error_detail = (
                    f"❌ Access denied: {error_desc}\n\n"
                    f"🔧 TROUBLESHOOTING STEPS:\n"
                    f"1. Verify Client ID {client_id_for_error} is authorized in Google Workspace Admin Console\n"
                    f"   (Security → API Controls → Domain-wide Delegation)\n"
                    f"2. Ensure these 5 scopes are authorized (one per line, EXACT URLs):\n"
                    f"   • https://www.googleapis.com/auth/classroom.courses.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.rosters.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.announcements.readonly\n"
                    f"   • https://www.googleapis.com/auth/calendar.readonly\n"
                    f"   • https://www.googleapis.com/auth/calendar.events.readonly\n"
                    f"3. Ensure Admin SDK API is enabled in Google Cloud Console\n"
                    f"4. Wait 15-30 minutes for propagation\n"
                    f"5. Check user email domain matches workspace domain\n"
                    f"6. Verify no typos or extra spaces in scopes\n\n"
                    f"📄 See: backend/DWD_ADMIN_CONSOLE_SETUP.md for detailed instructions"
                )
            else:
                error_detail = (
                    f"❌ Access denied: Requested client not authorized.\n\n"
                    f"🔧 TROUBLESHOOTING STEPS:\n"
                    f"1. Verify Client ID {client_id_for_error} is authorized in Google Workspace Admin Console\n"
                    f"   (Security → API Controls → Domain-wide Delegation)\n"
                    f"2. Ensure these 5 scopes are authorized (one per line, EXACT URLs):\n"
                    f"   • https://www.googleapis.com/auth/classroom.courses.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.rosters.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.announcements.readonly\n"
                    f"   • https://www.googleapis.com/auth/calendar.readonly\n"
                    f"   • https://www.googleapis.com/auth/calendar.events.readonly\n"
                    f"3. Ensure Admin SDK API is enabled in Google Cloud Console\n"
                    f"4. Wait 15-30 minutes for propagation\n"
                    f"5. Check user email domain matches workspace domain\n"
                    f"6. Verify no typos or extra spaces in scopes\n\n"
                    f"📄 See: backend/DWD_ADMIN_CONSOLE_SETUP.md for detailed instructions"
                )
        elif isinstance(e, tuple):
            # Handle tuple-formatted errors
            if len(e) >= 1:
                error_detail = str(e[0]) if e[0] else str(e)
            else:
                error_detail = str(e)
        else:
            # Generic error - still provide helpful context
            error_detail = (
                f"❌ Sync error: {error_detail}\n\n"
                f"🔧 TROUBLESHOOTING:\n"
                f"1. Check if user email '{user_email}' exists in your workspace\n"
                f"2. Verify DWD is properly configured (see backend/DWD_ADMIN_CONSOLE_SETUP.md)\n"
                f"3. Check backend logs for more details\n"
                f"4. Try running: python scripts/test_dwd_fetch.py {user_email}"
            )
        
        raise HTTPException(
            status_code=500, 
            detail=f"DWD sync failed for {user_email}:\n\n{error_detail}",
            headers={"X-Error-Type": error_type}
        )

# Helper function for parsing Google timestamps
def parse_google_timestamp(timestamp: Optional[str]) -> Optional[str]:
    """Parse Google API timestamp to ISO format"""
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).isoformat()
    except:
        return None

# Individual Sync Endpoints

@router.post("/sync/classroom/{course_id}")
async def sync_individual_course(course_id: str, email: Optional[str] = None):
    """Sync a specific Google Classroom course using DWD"""
    print(f"[SyncCourse] ========== Starting sync for course_id: {course_id} ==========")
    print(f"[SyncCourse] Admin email: {email or 'not provided'}")
    try:
        admin_service = SupabaseAdminService()
        admin = None
        if email:
            admin = admin_service.get_admin(email)
        
        if not admin:
            admin = admin_service.get_first_admin()
        
        if not admin:
            raise HTTPException(status_code=404, detail="No admin profile found")
        
        # Find course owner's email from database
        print(f"[SyncCourse] Looking up course owner for course_id: {course_id}")
        user_email = None
        
        try:
            # Query for course owner - try to find any course with this course_id
            existing_course = admin_service.supabase.table('google_classroom_courses').select('user_id').eq('course_id', course_id).limit(1).execute()
            
            if existing_course.data and len(existing_course.data) > 0:
                course_owner_user_id = existing_course.data[0].get('user_id')
                print(f"[SyncCourse] Found course in database with user_id: {course_owner_user_id}")
                
                # Find the email for this user_id
                if course_owner_user_id:
                    try:
                        owner_profile = admin_service.supabase.table('user_profiles').select('email').eq('user_id', course_owner_user_id).single().execute()
                        if owner_profile.data:
                            user_email = owner_profile.data.get('email')
                            print(f"[SyncCourse] Found course owner email: {user_email}")
                    except Exception as e:
                        print(f"[SyncCourse] Warning: Error finding course owner email: {e}")
            else:
                print(f"[SyncCourse] Course {course_id} not found in database - will use admin's email")
        except Exception as e:
            print(f"[SyncCourse] Error querying database for course owner: {e}")
        
        # If course owner not found, use admin's email
        if not user_email:
            user_email = admin.get('email')
            print(f"[SyncCourse] Using admin's email for sync: {user_email}")
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Could not determine user email for sync")
        
        # Use DWD to sync this course
        from ..services.google_dwd_service import get_dwd_service
        
        dwd_service = get_dwd_service()
        if not dwd_service:
            raise HTTPException(status_code=500, detail="DWD service not available. Please configure Domain-Wide Delegation.")
        
        # Fetch the course using DWD
        try:
            classroom_service = dwd_service.get_classroom_service(user_email)
            course_response = classroom_service.courses().get(id=course_id).execute()
            course = course_response
        except Exception as e:
            print(f"[SyncCourse] Error fetching course with DWD: {e}")
            raise HTTPException(status_code=404, detail=f"Course {course_id} not found or not accessible for {user_email}")
        
        # Get user_id for database
        profile = admin_service.supabase.table('user_profiles').select('user_id').eq('email', user_email).single().execute()
        user_id = profile.data.get('user_id') if profile.data else None
        
        if not user_id:
            raise HTTPException(status_code=400, detail=f"User ID not found for {user_email}")
        
        # Update course in database
        course_data = {
            "user_id": user_id,
            "course_id": course_id,
            "name": course.get('name', ''),
            "description": course.get('description'),
            "section": course.get('section'),
            "room": course.get('room'),
            "owner_id": course.get('ownerId'),
            "enrollment_code": course.get('enrollmentCode'),
            "course_state": course.get('courseState'),
            "alternate_link": course.get('alternateLink'),
            "teacher_group_email": course.get('teacherGroupEmail'),
            "course_group_email": course.get('courseGroupEmail'),
            "guardians_enabled": course.get('guardiansEnabled', False),
            "calendar_enabled": bool(course.get('calendarId')),
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert course
        existing = admin_service.supabase.table('google_classroom_courses').select('id, user_id').eq('course_id', course_id).limit(1).execute()
        
        if existing.data and len(existing.data) > 0:
            existing_record = existing.data[0]
            if existing_record.get('user_id') != user_id:
                print(f"[SyncCourse] Warning: Course exists with different user_id. Updating to: {user_id}")
            admin_service.supabase.table('google_classroom_courses').update(course_data).eq('id', existing_record['id']).execute()
        else:
            admin_service.supabase.table('google_classroom_courses').insert(course_data).execute()
        
        # Fetch and update related data using DWD
        try:
            # Teachers
            teachers = dwd_service.fetch_course_teachers(user_email, course_id)
            for teacher in teachers:
                teacher_data = {
                    "user_id": user_id,
                    "course_id": course_id,
                    "teacher_id": teacher.get('userId'),
                    "profile_name": teacher.get('profile', {}).get('name', {}).get('fullName', ''),
                    "email": teacher.get('profile', {}).get('emailAddress', ''),
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }
                existing_teacher = admin_service.supabase.table('google_classroom_teachers').select('id').eq('user_id', user_id).eq('course_id', course_id).eq('teacher_id', teacher_data['teacher_id']).single().execute()
                if existing_teacher.data:
                    admin_service.supabase.table('google_classroom_teachers').update(teacher_data).eq('id', existing_teacher.data['id']).execute()
                else:
                    admin_service.supabase.table('google_classroom_teachers').insert(teacher_data).execute()
            
            # Students
            students = dwd_service.fetch_course_students(user_email, course_id)
            for student in students:
                student_data = {
                    "user_id": user_id,
                    "course_id": course_id,
                    "student_id": student.get('userId'),
                    "profile_name": student.get('profile', {}).get('name', {}).get('fullName', ''),
                    "email": student.get('profile', {}).get('emailAddress', ''),
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }
                existing_student = admin_service.supabase.table('google_classroom_students').select('id').eq('user_id', user_id).eq('course_id', course_id).eq('student_id', student_data['student_id']).single().execute()
                if existing_student.data:
                    admin_service.supabase.table('google_classroom_students').update(student_data).eq('id', existing_student.data['id']).execute()
                else:
                    admin_service.supabase.table('google_classroom_students').insert(student_data).execute()
            
            # Announcements
            announcements = dwd_service.fetch_course_announcements(user_email, course_id)
            for ann in announcements:
                ann_data = {
                    "user_id": user_id,
                    "course_id": course_id,
                    "announcement_id": ann.get('id'),
                    "text": ann.get('text', ''),
                    "state": ann.get('state'),
                    "alternate_link": ann.get('alternateLink'),
                    "creation_time": parse_google_timestamp(ann.get('creationTime')),
                    "update_time": parse_google_timestamp(ann.get('updateTime')),
                    "scheduled_time": parse_google_timestamp(ann.get('scheduledTime')),
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }
                existing_ann = admin_service.supabase.table('google_classroom_announcements').select('id').eq('user_id', user_id).eq('course_id', course_id).eq('announcement_id', ann_data['announcement_id']).single().execute()
                if existing_ann.data:
                    admin_service.supabase.table('google_classroom_announcements').update(ann_data).eq('id', existing_ann.data['id']).execute()
                else:
                    admin_service.supabase.table('google_classroom_announcements').insert(ann_data).execute()
        except Exception as e:
            print(f"[SyncCourse] Warning: Error syncing related data: {e}")
        
        print(f"[SyncCourse] ========== Successfully synced course: {course.get('name', course_id)} ==========")
        print(f"[SyncCourse] Course saved with user_id: {user_id}")
        
        return {
            "success": True,
            "message": f"Course '{course.get('name', course_id)}' synced successfully using DWD",
            "course": course_data,
            "synced_for": user_email
        }
        
    except HTTPException as e:
        print(f"[SyncCourse] ❌ HTTP Error: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        print(f"[SyncCourse] ❌ Unexpected error syncing individual course: {e}")
        import traceback
        traceback.print_exc()
        error_msg = f"Sync error: {str(e)}"
        if course_id:
            error_msg += f" (course_id: {course_id})"
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/sync/calendar/{calendar_id}")
async def sync_individual_calendar(calendar_id: str, email: Optional[str] = None):
    """Sync a specific Google Calendar using DWD"""
    try:
        admin_service = SupabaseAdminService()
        admin = None
        if email:
            admin = admin_service.get_admin(email)
        
        if not admin:
            admin = admin_service.get_first_admin()
        
        if not admin:
            raise HTTPException(status_code=404, detail="No admin profile found")
        
        # Find calendar owner's email from database
        user_email = None
        
        try:
            # Query for calendar owner
            existing_calendar = admin_service.supabase.table('google_calendar_calendars').select('user_id').eq('calendar_id', calendar_id).limit(1).execute()
            
            if existing_calendar.data and len(existing_calendar.data) > 0:
                calendar_owner_user_id = existing_calendar.data[0].get('user_id')
                if calendar_owner_user_id:
                    owner_profile = admin_service.supabase.table('user_profiles').select('email').eq('user_id', calendar_owner_user_id).single().execute()
                    if owner_profile.data:
                        user_email = owner_profile.data.get('email')
        except Exception as e:
            print(f"[SyncCalendar] Error querying database for calendar owner: {e}")
        
        # If calendar owner not found, use admin's email
        if not user_email:
            user_email = admin.get('email')
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Could not determine user email for sync")
        
        # Use DWD to sync this calendar
        from ..services.google_dwd_service import get_dwd_service
        
        dwd_service = get_dwd_service()
        if not dwd_service:
            raise HTTPException(status_code=500, detail="DWD service not available. Please configure Domain-Wide Delegation.")
        
        # Fetch the calendar using DWD
        try:
            calendar_service = dwd_service.get_calendar_service(user_email)
            calendar_response = calendar_service.calendars().get(calendarId=calendar_id).execute()
            calendar = calendar_response
        except Exception as e:
            print(f"[SyncCalendar] Error fetching calendar with DWD: {e}")
            raise HTTPException(status_code=404, detail=f"Calendar {calendar_id} not found or not accessible for {user_email}")
        
        # Get user_id for database
        profile = admin_service.supabase.table('user_profiles').select('user_id').eq('email', user_email).single().execute()
        user_id = profile.data.get('user_id') if profile.data else None
        
        if not user_id:
            raise HTTPException(status_code=400, detail=f"User ID not found for {user_email}")
        
        # Update calendar in database
        calendar_data = {
            "user_id": user_id,
            "calendar_id": calendar_id,
            "summary": calendar.get('summary'),
            "description": calendar.get('description'),
            "location": calendar.get('location'),
            "timezone": calendar.get('timeZone'),
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert calendar
        existing = admin_service.supabase.table('google_calendar_calendars').select('id, user_id').eq('calendar_id', calendar_id).limit(1).execute()
        
        if existing.data and len(existing.data) > 0:
            existing_record = existing.data[0]
            if existing_record.get('user_id') != user_id:
                print(f"[SyncCalendar] Warning: Calendar exists with different user_id. Updating to: {user_id}")
            admin_service.supabase.table('google_calendar_calendars').update(calendar_data).eq('id', existing_record['id']).execute()
        else:
            admin_service.supabase.table('google_calendar_calendars').insert(calendar_data).execute()
        
        # Fetch and update events using DWD
        try:
            timeMin = datetime.now(timezone.utc).isoformat()
            timeMax = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
            
            events_response = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=timeMin,
                timeMax=timeMax,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_response.get('items', [])
            
            for event in events:
                event_data = {
                    "user_id": user_id,
                    "event_id": event.get('id'),
                    "calendar_id": calendar_id,
                    "summary": event.get('summary'),
                    "description": event.get('description'),
                    "location": event.get('location'),
                    "start_time": parse_google_timestamp(event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')),
                    "end_time": parse_google_timestamp(event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')),
                    "all_day": not event.get('start', {}).get('dateTime') and bool(event.get('start', {}).get('date')),
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }
                
                existing_event = admin_service.supabase.table('google_calendar_events').select('id').eq('user_id', user_id).eq('event_id', event_data['event_id']).single().execute()
                if existing_event.data:
                    admin_service.supabase.table('google_calendar_events').update(event_data).eq('id', existing_event.data['id']).execute()
                else:
                    admin_service.supabase.table('google_calendar_events').insert(event_data).execute()
        except Exception as e:
            print(f"[SyncCalendar] Warning: Error syncing events: {e}")
        
        return {
            "success": True,
            "message": f"Calendar '{calendar.get('summary', calendar_id)}' synced successfully using DWD",
            "calendar": calendar_data,
            "synced_for": user_email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error syncing individual calendar: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

@router.post("/sync/event/{event_id}")
async def sync_individual_event(event_id: str, email: Optional[str] = None, calendar_id: Optional[str] = None):
    """Sync a specific Google Calendar event using DWD"""
    try:
        admin_service = SupabaseAdminService()
        admin = None
        if email:
            admin = admin_service.get_admin(email)
        
        if not admin:
            admin = admin_service.get_first_admin()
        
        if not admin:
            raise HTTPException(status_code=404, detail="No admin profile found")
        
        # Find event owner's email from database
        user_email = None
        
        try:
            # Query for event owner
            existing_event = admin_service.supabase.table('google_calendar_events').select('user_id').eq('event_id', event_id).limit(1).execute()
            
            if existing_event.data and len(existing_event.data) > 0:
                event_owner_user_id = existing_event.data[0].get('user_id')
                if event_owner_user_id:
                    owner_profile = admin_service.supabase.table('user_profiles').select('email').eq('user_id', event_owner_user_id).single().execute()
                    if owner_profile.data:
                        user_email = owner_profile.data.get('email')
        except Exception as e:
            print(f"[SyncEvent] Error querying database for event owner: {e}")
        
        # If event owner not found, use admin's email
        if not user_email:
            user_email = admin.get('email')
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Could not determine user email for sync")
        
        # Use DWD to sync this event
        from ..services.google_dwd_service import get_dwd_service
        
        dwd_service = get_dwd_service()
        if not dwd_service:
            raise HTTPException(status_code=500, detail="DWD service not available. Please configure Domain-Wide Delegation.")
        
        # Get calendar_id if not provided
        if not calendar_id:
            try:
                existing_event = admin_service.supabase.table('google_calendar_events').select('calendar_id').eq('user_id', admin_service.supabase.table('user_profiles').select('user_id').eq('email', user_email).single().execute().data.get('user_id')).eq('event_id', event_id).limit(1).execute()
                if existing_event.data and existing_event.data[0].get('calendar_id'):
                    calendar_id = existing_event.data[0]['calendar_id']
                else:
                    calendar_id = 'primary'
            except:
                calendar_id = 'primary'
        
        # Fetch the event using DWD
        try:
            calendar_service = dwd_service.get_calendar_service(user_email)
            event_response = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            event = event_response
        except Exception as e:
            print(f"[SyncEvent] Error fetching event with DWD: {e}")
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found or not accessible for {user_email}")
        
        # Get user_id for database
        profile = admin_service.supabase.table('user_profiles').select('user_id').eq('email', user_email).single().execute()
        user_id = profile.data.get('user_id') if profile.data else None
        
        if not user_id:
            raise HTTPException(status_code=400, detail=f"User ID not found for {user_email}")
        
        # Update event in database
        start_time = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
        end_time = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
        
        event_data = {
            "user_id": user_id,
            "calendar_id": calendar_id,
            "event_id": event_id,
            "summary": event.get('summary', ''),
            "description": event.get('description'),
            "location": event.get('location'),
            "start_time": parse_google_timestamp(start_time) if start_time else None,
            "end_time": parse_google_timestamp(end_time) if end_time else None,
            "status": event.get('status'),
            "html_link": event.get('htmlLink'),
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }
        
        existing = admin_service.supabase.table('google_calendar_events').select('id').eq('user_id', user_id).eq('calendar_id', calendar_id).eq('event_id', event_id).single().execute()
        
        if existing.data:
            admin_service.supabase.table('google_calendar_events').update(event_data).eq('id', existing.data['id']).execute()
        else:
            admin_service.supabase.table('google_calendar_events').insert(event_data).execute()
        
        return {
            "success": True,
            "message": f"Event '{event.get('summary', event_id)}' synced successfully using DWD",
            "event": event_data,
            "synced_for": user_email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error syncing individual event: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

@router.post("/sync/website/{url:path}")
async def sync_individual_website(url: str, email: Optional[str] = None):
    """Sync a specific website page"""
    try:
        from urllib.parse import unquote
        from app.agents.web_crawler_agent import WebCrawlerAgent
        from supabase_config import get_supabase_client
        
        # Decode URL
        url = unquote(url)
        
        print(f"[Admin] Individual website sync requested for: {url}")
        
        supabase = get_supabase_client()
        if not supabase:
            raise HTTPException(status_code=500, detail="Supabase not available")
        
        # Get content type from config
        from app.config.essential_pages import PAGE_CONTENT_TYPES
        content_type = PAGE_CONTENT_TYPES.get(url, 'general')
        
        # Crawl the specific URL
        crawler = WebCrawlerAgent()
        content = crawler.extract_content_from_url(url, query="", skip_link_following=True)
        
        if 'error' in content:
            raise HTTPException(status_code=400, detail=f"Error crawling URL: {content['error']}")
        
        # Extract keywords
        keywords = []
        if content.get('title'):
            keywords.extend(content['title'].lower().split()[:5])
        if content.get('description'):
            keywords.extend(content['description'].lower().split()[:5])
        
        # Prepare data
        cache_data = {
            'url': url,
            'title': content.get('title', ''),
            'description': content.get('description', ''),
            'main_content': content.get('main_content', '')[:50000],
            'headings': content.get('headings', []),
            'links': content.get('links', [])[:50],
            'content_type': content_type,
            'query_keywords': list(set(keywords))[:10],
            'relevance_score': len(keywords),
            'is_active': True,
            'crawled_at': datetime.utcnow().isoformat()
        }
        
        # Update or insert
        existing = supabase.table('web_crawler_data').select('id').eq('url', url).eq('is_active', True).order('crawled_at', desc=True).limit(1).execute()
        
        if existing.data and len(existing.data) > 0:
            record_id = existing.data[0]['id']
            update_data = {
                'title': cache_data['title'],
                'description': cache_data['description'],
                'main_content': cache_data['main_content'],
                'headings': cache_data['headings'],
                'links': cache_data['links'],
                'content_type': cache_data['content_type'],
                'query_keywords': cache_data['query_keywords'],
                'relevance_score': cache_data['relevance_score'],
                'crawled_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            supabase.table('web_crawler_data').update(update_data).eq('id', record_id).execute()
        else:
            result = supabase.table('web_crawler_data').insert(cache_data).select('id').execute()
            record_id = result.data[0].get('id') if result.data else None
        
        # Generate embedding
        if record_id:
            try:
                embedding_gen = get_embedding_generator()
                embedding_gen.generate_for_web_crawler(record_id)
            except Exception as e:
                print(f"Warning: Failed to generate embedding: {e}")
        
        return {
            "success": True,
            "message": f"Page '{content.get('title', url)}' synced successfully",
            "page": {
                "url": url,
                "title": content.get('title', ''),
                "content_type": content_type,
                "crawled_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error syncing individual website page: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

@router.post("/sync-all")
async def sync_all_users(background_tasks: BackgroundTasks, email: Optional[str] = None):
    """
    Trigger bulk sync for all users with active Google integrations.
    Runs asynchronously in background.
    """
    # Verify admin privileges
    admin_service = SupabaseAdminService()
    if email:
        profile = admin_service.get_user_profile_by_email(email)
        if not profile or not profile.get('admin_privileges'):
            raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Check if sync is already running
    if _sync_status["is_running"]:
        raise HTTPException(
            status_code=409, 
            detail="Bulk sync is already running. Please wait for it to complete."
        )
    
    # Reset status
    _sync_status.update({
        "is_running": True,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "total_users": 0,
        "users_synced": 0,
        "users_failed": 0,
        "error": None
    })
    
    # Get scheduler and trigger sync in background
    scheduler = get_auto_sync_scheduler()
    
    async def run_sync_with_tracking():
        try:
            # Get count of users to sync
            supabase = admin_service.supabase
            integrations_result = supabase.table('google_integrations').select('admin_id').eq('is_active', True).execute()
            
            if integrations_result.data:
                admin_ids = set(i.get('admin_id') for i in integrations_result.data)
                _sync_status["total_users"] = len(admin_ids)
            
            # Run the sync
            await scheduler.sync_all_connected_services()
            
            # Update status on completion
            _sync_status.update({
                "is_running": False,
                "completed_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            _sync_status.update({
                "is_running": False,
                "completed_at": datetime.utcnow().isoformat(),
                "error": str(e)
            })
            print(f"[BulkSync] Error: {e}")
    
    background_tasks.add_task(run_sync_with_tracking)
    
    return {
        "success": True,
        "message": "Bulk sync started in background",
        "status": {
            "is_running": True,
            "started_at": _sync_status["started_at"]
        }
    }

@router.get("/sync-all/status")
async def get_sync_status():
    """Get current status of bulk sync operation"""
    return {
        "status": _sync_status
    }

@router.get("/users/by-grade-role")
async def get_users_by_grade_role(email: Optional[str] = None):
    """Get all users organized by grade and role"""
    try:
        admin_service = SupabaseAdminService()
        
        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Get all active users with grade and role
        result = admin_service.supabase.table('user_profiles').select(
            'id, email, first_name, last_name, role, grade, user_id'
        ).eq('is_active', True).execute()
        
        # Get last sync times from google tables for each user
        user_sync_times = {}
        for user in result.data:
            user_id = user.get('user_id') or user.get('id')
            if not user_id:
                continue
            
            # Check for last sync in classroom courses
            try:
                classroom_sync = admin_service.supabase.table('google_classroom_courses').select(
                    'last_synced_at'
                ).eq('user_id', user_id).order('last_synced_at', desc=True).limit(1).execute()
                
                if classroom_sync.data and len(classroom_sync.data) > 0:
                    sync_time = classroom_sync.data[0].get('last_synced_at')
                    if sync_time:
                        if user_id not in user_sync_times or sync_time > user_sync_times[user_id]:
                            user_sync_times[user_id] = sync_time
            except:
                pass
            
            # Check for last sync in calendar calendars
            try:
                calendar_sync = admin_service.supabase.table('google_calendar_calendars').select(
                    'last_synced_at'
                ).eq('user_id', user_id).order('last_synced_at', desc=True).limit(1).execute()
                
                if calendar_sync.data and len(calendar_sync.data) > 0:
                    sync_time = calendar_sync.data[0].get('last_synced_at')
                    if sync_time:
                        if user_id not in user_sync_times or sync_time > user_sync_times[user_id]:
                            user_sync_times[user_id] = sync_time
            except:
                pass
        
        # Organize by grade and role
        organized = {}
        for user in result.data:
            grade = user.get('grade') or 'Ungraded'
            role = user.get('role') or 'student'
            user_id = user.get('user_id') or user.get('id')
            
            if grade not in organized:
                organized[grade] = {
                    'student': [],
                    'teacher': [],
                    'parent': []
                }
            
            # Determine last sync status
            last_sync = user_sync_times.get(user_id) if user_id else None
            status = 'pending'
            if last_sync:
                try:
                    sync_date = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                    hours_ago = (datetime.now(timezone.utc) - sync_date).total_seconds() / 3600
                    if hours_ago < 24:
                        status = 'synced'
                    else:
                        status = 'pending'
                except:
                    status = 'pending'
            
            user_data = {
                'email': user.get('email'),
                'name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get('email'),
                'lastSync': last_sync,
                'status': status
            }
            
            organized[grade][role].append(user_data)
        
        return organized
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting users by grade/role: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@router.post("/sync/grade/{grade}")
async def sync_grade(grade: str, request: GradeRoleSyncRequest):
    """Sync all users in a specific grade"""
    service = request.service
    email = request.email
    
    if service not in ["classroom", "calendar"]:
        raise HTTPException(status_code=400, detail="Service must be 'classroom' or 'calendar'")
    
    try:
        admin_service = SupabaseAdminService()
        
        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Get all users in this grade
        result = admin_service.supabase.table('user_profiles').select(
            'email, role'
        ).eq('is_active', True).eq('grade', grade).execute()
        
        if not result.data:
            return {
                "success": True,
                "message": f"No users found in {grade}",
                "synced": 0,
                "failed": 0
            }
        
        # Sync each user using DWD
        synced = 0
        failed = 0
        
        for user in result.data:
            user_email = user.get('email')
            if not user_email:
                continue
            
            try:
                # Call the DWD sync endpoint logic directly
                sync_request = DWDSyncRequest(user_email=user_email)
                sync_response = await sync_dwd(service, sync_request)
                if sync_response and sync_response.get('success', False):
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error syncing {user_email}: {e}")
                failed += 1
        
        return {
            "success": True,
            "message": f"Synced {service} for {grade}",
            "synced": synced,
            "failed": failed,
            "total": len(result.data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error syncing grade {grade}: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing grade: {str(e)}")

@router.post("/sync/grade/{grade}/role/{role}")
async def sync_grade_role(grade: str, role: str, request: GradeRoleSyncRequest):
    """Sync all users of a specific role in a specific grade"""
    service = request.service
    email = request.email
    
    if service not in ["classroom", "calendar"]:
        raise HTTPException(status_code=400, detail="Service must be 'classroom' or 'calendar'")
    
    if role not in ["student", "teacher", "parent"]:
        raise HTTPException(status_code=400, detail="Role must be 'student', 'teacher', or 'parent'")
    
    try:
        admin_service = SupabaseAdminService()
        
        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Get all users with this grade and role
        result = admin_service.supabase.table('user_profiles').select('email').eq(
            'is_active', True
        ).eq('grade', grade).eq('role', role).execute()
        
        if not result.data:
            return {
                "success": True,
                "message": f"No {role}s found in {grade}",
                "synced": 0,
                "failed": 0
            }
        
        # Sync each user using DWD
        synced = 0
        failed = 0
        
        for user in result.data:
            user_email = user.get('email')
            if not user_email:
                continue
            
            try:
                # Call the DWD sync endpoint logic directly
                sync_request = DWDSyncRequest(user_email=user_email)
                sync_response = await sync_dwd(service, sync_request)
                if sync_response and sync_response.get('success', False):
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error syncing {user_email}: {e}")
                failed += 1
        
        return {
            "success": True,
            "message": f"Synced {service} for {role}s in {grade}",
            "synced": synced,
            "failed": failed,
            "total": len(result.data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error syncing {role}s in {grade}: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing users: {str(e)}")

