from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import json
import asyncio
from datetime import datetime, timedelta, timezone
import os

from ..core.database import get_db
from ..models.admin import Admin, GoogleIntegration, ClassroomData, CalendarData, GoogleCloudDriveRead
# Auth functions removed - using Supabase authentication in frontend
from ..services.supabase_admin import SupabaseAdminService
from ..services.google_dwd_service import get_dwd_service
from ..services.embedding_generator import get_embedding_generator
from ..services.auto_sync_scheduler import get_auto_sync_scheduler
# Ensure backend root is in sys.path
import sys
import os
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from token_refresh_service import refresh_expired_tokens
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

# Sensitive Data Credentials (for Drive/Classroom)
GOOGLE_SENSITIVE_CLIENT_ID = os.getenv("GOOGLE_SENSITIVE_CLIENT_ID")
GOOGLE_SENSITIVE_CLIENT_SECRET = os.getenv("GOOGLE_SENSITIVE_CLIENT_SECRET")

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

GOOGLE_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",  # Access exam files shared with admin account
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
        # Determine which credentials to use
        is_sensitive = integration.service_type in ["classroom", "drive"]
        client_id = GOOGLE_SENSITIVE_CLIENT_ID if is_sensitive and GOOGLE_SENSITIVE_CLIENT_ID else GOOGLE_CLIENT_ID
        client_secret = GOOGLE_SENSITIVE_CLIENT_SECRET if is_sensitive and GOOGLE_SENSITIVE_CLIENT_SECRET else GOOGLE_CLIENT_SECRET

        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
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

# DWD Client ID Helper Endpoint
@router.get("/dwd/client-id")
async def get_dwd_client_id():
    """Get the Client ID that needs to be authorized in Google Workspace Admin Console"""
    try:
        dwd_service = get_dwd_service()
        if not dwd_service:
            return {
                "error": "DWD service not available",
                "instructions": "Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_JSON environment variable"
            }
        
        client_id = dwd_service._get_client_id()
        service_account_email = None
        project_id = None
        
        # Try to get service account email and project ID
        try:
            import json
            service_account_path = dwd_service.service_account_path
            if os.path.exists(service_account_path):
                with open(service_account_path, 'r') as f:
                    service_account_info = json.load(f)
                    service_account_email = service_account_info.get('client_email')
                    project_id = service_account_info.get('project_id')
            elif os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'):
                service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
                service_account_email = service_account_info.get('client_email')
                project_id = service_account_info.get('project_id')
        except Exception as e:
            print(f"Warning: Could not read service account info: {e}")
        
        return {
            "client_id": client_id,
            "service_account_email": service_account_email,
            "project_id": project_id,
            "workspace_domain": dwd_service.workspace_domain,
            "instructions": {
                "step_1": "Go to https://admin.google.com",
                "step_2": "Navigate to: Security → API Controls → Domain-wide Delegation",
                "step_3": f"Click 'Add new' and enter Client ID: {client_id}",
                "step_4": "Add these OAuth scopes (one per line, EXACT URLs):",
                "scopes": [
                    "https://www.googleapis.com/auth/classroom.courses.readonly",
                    "https://www.googleapis.com/auth/classroom.rosters.readonly",
                    "https://www.googleapis.com/auth/classroom.coursework.readonly",
                    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
                    "https://www.googleapis.com/auth/classroom.announcements.readonly",
                    "https://www.googleapis.com/auth/admin.directory.user.readonly",
                    "https://www.googleapis.com/auth/calendar.readonly",
                    "https://www.googleapis.com/auth/calendar.events.readonly"
                ],
                "step_5": "Click 'Authorize'",
                "step_6": "Wait 15-30 minutes for changes to propagate",
                "note": "The Client ID must match EXACTLY (no spaces, no typos)"
            }
        }
    except Exception as e:
        return {
            "error": str(e),
            "instructions": "Check that GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_JSON is set correctly"
        }

# DWD Diagnostic Endpoint
@router.get("/dwd/diagnose")
async def diagnose_dwd():
    """Comprehensive DWD diagnostic information"""
    import json
    from datetime import datetime

    # Get Client ID for display
    client_id = None
    try:
        dwd_service = get_dwd_service()
        if dwd_service:
            client_id = dwd_service._get_client_id()
    except:
        pass

    result = {
        "timestamp": datetime.now().isoformat(),
        "environment": "production" if os.getenv("RENDER") else "localhost",
        "client_id": client_id,
        "client_id_authorization_url": "https://admin.google.com/ac/owl/domainwidedelegation?hl=en" if client_id else None,
        "checks": {}
    }

    # Environment variables check
    env_vars = [
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GOOGLE_WORKSPACE_DOMAIN',
        'GOOGLE_SERVICE_ACCOUNT_JSON',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY'
    ]

    result["checks"]["environment_variables"] = {}
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if any(sensitive in var.upper() for sensitive in ['KEY', 'SECRET', 'JSON']):
                result["checks"]["environment_variables"][var] = f"SET (length: {len(value)})"
            else:
                result["checks"]["environment_variables"][var] = value
        else:
            result["checks"]["environment_variables"][var] = "NOT SET"

    # Service account file check
    result["checks"]["service_account_file"] = {}
    file_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-key.json')
    result["checks"]["service_account_file"]["path"] = file_path
    result["checks"]["service_account_file"]["exists"] = os.path.exists(file_path)

    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            result["checks"]["service_account_file"]["valid_json"] = True
            result["checks"]["service_account_file"]["project_id"] = data.get('project_id')
            result["checks"]["service_account_file"]["client_email"] = data.get('client_email')
            result["checks"]["service_account_file"]["client_id"] = data.get('client_id')
        except Exception as e:
            result["checks"]["service_account_file"]["valid_json"] = False
            result["checks"]["service_account_file"]["error"] = str(e)

    # Domain configuration check
    configured_domain = os.getenv('GOOGLE_WORKSPACE_DOMAIN', 'NOT SET')
    result["checks"]["domain_config"] = {
        "configured_domain": configured_domain,
        "expected_domain": "learners.prakriti.org.in",
        "matches": configured_domain == "learners.prakriti.org.in"
    }

    # DWD service initialization
    result["checks"]["dwd_service"] = {}
    try:
        dwd_service = get_dwd_service()
        result["checks"]["dwd_service"]["initialized"] = dwd_service is not None

        if dwd_service:
            result["checks"]["dwd_service"]["available"] = dwd_service.is_available()
            result["checks"]["dwd_service"]["workspace_domain"] = dwd_service.workspace_domain
            result["checks"]["dwd_service"]["service_account_path"] = dwd_service.service_account_path

            # Test basic credentials
            if hasattr(dwd_service, '_base_credentials'):
                result["checks"]["dwd_service"]["base_credentials_loaded"] = dwd_service._base_credentials is not None
            else:
                result["checks"]["dwd_service"]["base_credentials_loaded"] = False
        else:
            result["checks"]["dwd_service"]["error"] = "DWD service initialization failed"
    except Exception as e:
        result["checks"]["dwd_service"]["error"] = str(e)

    # Supabase connection
    result["checks"]["supabase"] = {}
    try:
        supabase = get_supabase_client()
        result["checks"]["supabase"]["client_created"] = supabase is not None

        if supabase:
            # Test simple query
            try:
                test_result = supabase.table('user_profiles').select('count').limit(1).execute()
                result["checks"]["supabase"]["connection_successful"] = True
            except Exception as e:
                result["checks"]["supabase"]["connection_successful"] = False
                result["checks"]["supabase"]["query_error"] = str(e)
    except Exception as e:
        result["checks"]["supabase"]["error"] = str(e)

    return result

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
                    # Generate embedding for updated course
                    try:
                        embedding_gen = get_embedding_generator()
                        embedding_gen.generate_for_course(existing_course_id)
                    except Exception as e:
                        print(f"⚠️ DWD: Failed to generate embedding for course {existing_course_id}: {e}")
                else:
                    # Course doesn't exist - insert it
                    result = supabase.table('google_classroom_courses').insert(course_data).execute()
                    if result.data and len(result.data) > 0:
                        db_course_id = result.data[0].get('id')
                        sync_stats["courses"]["created"] += 1
                        # Generate embedding for new course
                        try:
                            embedding_gen = get_embedding_generator()
                            embedding_gen.generate_for_course(db_course_id)
                        except Exception as e:
                            print(f"⚠️ DWD: Failed to generate embedding for course {db_course_id}: {e}")
                
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
                            teacher_db_id = existing.data[0]['id']
                            supabase.table('google_classroom_teachers').update(teacher_data).eq('id', teacher_db_id).execute()
                            sync_stats["teachers"]["updated"] += 1
                            # Generate embedding for updated teacher
                            try:
                                embedding_gen = get_embedding_generator()
                                embedding_gen.generate_for_teacher(teacher_db_id)
                            except Exception as e:
                                print(f"⚠️ DWD: Failed to generate embedding for teacher {teacher_db_id}: {e}")
                        else:
                            result = supabase.table('google_classroom_teachers').insert(teacher_data).execute()
                            if result.data and len(result.data) > 0:
                                teacher_db_id = result.data[0].get('id')
                                sync_stats["teachers"]["created"] += 1
                                # Generate embedding for new teacher
                                try:
                                    embedding_gen = get_embedding_generator()
                                    embedding_gen.generate_for_teacher(teacher_db_id)
                                except Exception as e:
                                    print(f"⚠️ DWD: Failed to generate embedding for teacher {teacher_db_id}: {e}")
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
                            student_db_id = existing.data[0]['id']
                            supabase.table('google_classroom_students').update(student_data).eq('id', student_db_id).execute()
                            sync_stats["students"]["updated"] += 1
                            # Generate embedding for updated student
                            try:
                                embedding_gen = get_embedding_generator()
                                embedding_gen.generate_for_student(student_db_id)
                            except Exception as e:
                                print(f"⚠️ DWD: Failed to generate embedding for student {student_db_id}: {e}")
                        else:
                            result = supabase.table('google_classroom_students').insert(student_data).execute()
                            if result.data and len(result.data) > 0:
                                student_db_id = result.data[0].get('id')
                                sync_stats["students"]["created"] += 1
                                # Generate embedding for new student
                                try:
                                    embedding_gen = get_embedding_generator()
                                    embedding_gen.generate_for_student(student_db_id)
                                except Exception as e:
                                    print(f"⚠️ DWD: Failed to generate embedding for student {student_db_id}: {e}")
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
                            supabase.table('google_classroom_coursework').update(coursework_data).eq('id', existing.data[0]['id']).execute()
                            cw_db_id = existing.data[0]['id']
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
                                        submission_db_id = existing.data[0]['id']
                                        supabase.table('google_classroom_submissions').update(submission_data).eq('id', submission_db_id).execute()
                                        sync_stats["submissions"]["updated"] += 1
                                        # Generate embedding for updated submission
                                        try:
                                            embedding_gen = get_embedding_generator()
                                            embedding_gen.generate_for_submission(submission_db_id)
                                        except Exception as e:
                                            print(f"⚠️ DWD: Failed to generate embedding for submission {submission_db_id}: {e}")
                                    else:
                                        result = supabase.table('google_classroom_submissions').insert(submission_data).execute()
                                        if result.data and len(result.data) > 0:
                                            submission_db_id = result.data[0].get('id')
                                            sync_stats["submissions"]["created"] += 1
                                            # Generate embedding for new submission
                                            try:
                                                embedding_gen = get_embedding_generator()
                                                embedding_gen.generate_for_submission(submission_db_id)
                                            except Exception as e:
                                                print(f"⚠️ DWD: Failed to generate embedding for submission {submission_db_id}: {e}")
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
                            supabase.table('google_classroom_announcements').update(announcement_data).eq('id', existing.data[0]['id']).execute()
                            ann_db_id = existing.data[0]['id']
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
                    # Generate embedding for updated calendar
                    try:
                        embedding_gen = get_embedding_generator()
                        embedding_gen.generate_for_calendar(existing_id)
                    except Exception as e:
                        print(f"⚠️ DWD: Failed to generate embedding for calendar {existing_id}: {e}")
                else:
                    # Calendar doesn't exist - insert it
                    result = supabase.table('google_calendar_calendars').insert(calendar_data).execute()
                    if result.data and len(result.data) > 0:
                        calendar_db_id = result.data[0].get('id')
                        sync_stats["calendars"]["created"] += 1
                        # Generate embedding for new calendar
                        try:
                            embedding_gen = get_embedding_generator()
                            embedding_gen.generate_for_calendar(calendar_db_id)
                        except Exception as e:
                            print(f"⚠️ DWD: Failed to generate embedding for calendar {calendar_db_id}: {e}")
                
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
                            event_db_id = existing.data[0]['id']
                            supabase.table('google_calendar_events').update(event_data).eq('id', event_db_id).execute()
                            sync_stats["events"]["updated"] += 1
                            # Generate embedding for updated event
                            try:
                                embedding_gen = get_embedding_generator()
                                embedding_gen.generate_for_calendar_event(event_db_id)
                            except Exception as e:
                                print(f"⚠️ DWD: Failed to generate embedding for calendar event {event_db_id}: {e}")
                        else:
                            result = supabase.table('google_calendar_events').insert(event_data).execute()
                            if result.data and len(result.data) > 0:
                                event_db_id = result.data[0].get('id')
                                sync_stats["events"]["created"] += 1
                                # Generate embedding for new event
                                try:
                                    embedding_gen = get_embedding_generator()
                                    embedding_gen.generate_for_calendar_event(event_db_id)
                                except Exception as e:
                                    print(f"⚠️ DWD: Failed to generate embedding for calendar event {event_db_id}: {e}")
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
                f"3. Ensure EXACTLY these 8 scopes are authorized (one per line, no typos):\n"
                f"   • https://www.googleapis.com/auth/classroom.courses.readonly\n"
                f"   • https://www.googleapis.com/auth/classroom.rosters.readonly\n"
                f"   • https://www.googleapis.com/auth/classroom.coursework.readonly\n"
                f"   • https://www.googleapis.com/auth/classroom.student-submissions.students.readonly\n"
                f"   • https://www.googleapis.com/auth/classroom.announcements.readonly\n"
                f"   • https://www.googleapis.com/auth/admin.directory.user.readonly\n"
                f"   • https://www.googleapis.com/auth/calendar.readonly\n"
                f"   • https://www.googleapis.com/auth/calendar.events.readonly\n"
                f"4. Remove any other scopes (only these 8)\n"
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
                f"3. Ensure all 8 scopes are authorized exactly as shown (see list below)\n"
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
                    f"2. Ensure these 8 scopes are authorized (one per line, EXACT URLs):\n"
                    f"   • https://www.googleapis.com/auth/classroom.courses.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.rosters.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.coursework.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.student-submissions.students.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.announcements.readonly\n"
                    f"   • https://www.googleapis.com/auth/admin.directory.user.readonly\n"
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
                    f"2. Ensure these 8 scopes are authorized (one per line, EXACT URLs):\n"
                    f"   • https://www.googleapis.com/auth/classroom.courses.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.rosters.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.coursework.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.student-submissions.students.readonly\n"
                    f"   • https://www.googleapis.com/auth/classroom.announcements.readonly\n"
                    f"   • https://www.googleapis.com/auth/admin.directory.user.readonly\n"
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
            admin_service.supabase.table('google_calendar_events').update(event_data).eq('id', existing.data[0]['id']).execute()
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
        
        # For calendar pages, always extract and store calendar events (even if page content is cached)
        if 'calendar' in url.lower():
            print(f"[Admin] Calendar page detected, extracting calendar events...")
            try:
                calendar_info = crawler.extract_calendar_events_with_selenium(url, query="")
                if calendar_info:
                    print(f"[Admin] ✅ Calendar events extracted and stored")
                    content['main_content'] += "\n\n" + calendar_info
            except Exception as e:
                print(f"[Admin] ⚠️ Warning: Failed to extract calendar events: {e}")
                # Don't fail the sync if calendar extraction fails, just log it
        
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


# GCDR (Google Cloud Drive Read) Token Management Routes
@router.get("/gcdr/tokens")
async def get_gcdr_tokens(email: Optional[str] = None):
    """Get all GCDR tokens for admin dashboard"""
    try:
        admin_service = SupabaseAdminService()

        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")

        # Get admin ID
        admin_profile = admin_service.get_user_profile_by_email(email)
        if not admin_profile:
            raise HTTPException(status_code=404, detail="Admin profile not found")

        admin_id = admin_profile.get('user_id')

        # Query GCDR tokens from Supabase
        try:
            from supabase_config import get_supabase_client
            supabase = get_supabase_client()
            try:
                result = supabase.table('gcdr').select('*').eq('admin_id', admin_id).order('created_at', desc=True).execute()
            except Exception as query_error:
                print(f"[GCDR] Supabase query error: {query_error}")
                # Try a simple query to check if table exists
                try:
                    test_result = supabase.table('gcdr').select('count').limit(1).execute()
                    print(f"[GCDR] Table exists, but query failed: {query_error}")
                except Exception as table_error:
                    print(f"[GCDR] Table doesn't exist or connection issue: {table_error}")
                raise query_error

            tokens = result.data or []

            return {
                "success": True,
                "tokens": tokens,
                "total": len(tokens)
            }

        except Exception as e:
            print(f"[GCDR] Error fetching tokens: {e}")
            raise HTTPException(status_code=500, detail=f"Error fetching tokens: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching GCDR tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching tokens: {str(e)}")

@router.post("/gcdr/tokens")
async def create_gcdr_token(request: dict, email: Optional[str] = None):
    """Create/store a new GCDR token"""
    try:
        admin_service = SupabaseAdminService()

        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")

        # Get admin ID
        admin_profile = admin_service.get_user_profile_by_email(email)
        if not admin_profile:
            raise HTTPException(status_code=404, detail="Admin profile not found")

        admin_id = admin_profile.get('user_id')

        # Validate required fields
        required_fields = ['user_email', 'access_token', 'token_expires_at', 'scope']
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

            # Check if token already exists for this user in Supabase
        try:
            from supabase_config import get_supabase_client
            supabase = get_supabase_client()
            existing_result = supabase.table('gcdr').select('id').eq('admin_id', admin_id).eq('user_email', request['user_email']).execute()

            if existing_result.data and len(existing_result.data) > 0:
                # Update existing token
                update_data = {
                    'access_token': request['access_token'],
                    'refresh_token': request.get('refresh_token'),
                    'token_expires_at': request['token_expires_at'],
                    'scope': request['scope'],
                    'token_type': request.get('token_type', 'Bearer'),
                    'client_id': request.get('client_id'),
                    'project_name': request.get('project_name', 'Prakriti Drive Test'),
                    'notes': request.get('notes'),
                    'updated_at': 'now()'
                }

                result = supabase.table('gcdr').update(update_data).eq('id', existing_result.data[0]['id']).execute()
                token_id = existing_result.data[0]['id']
                action = "updated"

            else:
                # Create new token
                insert_data = {
                    'admin_id': admin_id,
                    'user_email': request['user_email'],
                    'access_token': request['access_token'],
                    'refresh_token': request.get('refresh_token'),
                    'token_expires_at': request['token_expires_at'],
                    'scope': request['scope'],
                    'token_type': request.get('token_type', 'Bearer'),
                    'is_active': True,
                    'client_id': request.get('client_id'),
                    'project_name': request.get('project_name', 'Prakriti Drive Test'),
                    'notes': request.get('notes')
                }

                result = supabase.table('gcdr').insert(insert_data).execute()
                token_id = result.data[0]['id'] if result.data else None
                action = "created"

            return {
                "success": True,
                "message": f"GCDR token {action} successfully",
                "token_id": token_id
            }

        finally:
            pass  # No session to close when using Supabase

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating GCDR token: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating token: {str(e)}")

@router.put("/gcdr/tokens/{token_id}")
async def update_gcdr_token(token_id: int, request: dict, email: Optional[str] = None):
    """Update an existing GCDR token"""
    try:
        admin_service = SupabaseAdminService()

        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")

        # Get admin ID
        admin_profile = admin_service.get_user_profile_by_email(email)
        if not admin_profile:
            raise HTTPException(status_code=404, detail="Admin profile not found")

        admin_id = admin_profile.get('user_id')

        from ..core.database import get_db_session
        from datetime import datetime
        session = next(get_db_session())

        try:
            # Find the token
            token = session.query(GoogleCloudDriveRead).filter(
                GoogleCloudDriveRead.id == token_id,
                GoogleCloudDriveRead.admin_id == admin_id
            ).first()

            if not token:
                raise HTTPException(status_code=404, detail="Token not found")

            # Update fields
            if 'access_token' in request:
                token.access_token = request['access_token']
            if 'refresh_token' in request:
                token.refresh_token = request['refresh_token']
            if 'token_expires_at' in request:
                token.token_expires_at = datetime.fromisoformat(request['token_expires_at'])
            if 'scope' in request:
                token.scope = request['scope']
            if 'token_type' in request:
                token.token_type = request['token_type']
            if 'is_active' in request:
                token.is_active = request['is_active']
            if 'client_id' in request:
                token.client_id = request['client_id']
            if 'project_name' in request:
                token.project_name = request['project_name']
            if 'notes' in request:
                token.notes = request['notes']

            token.updated_at = datetime.utcnow()
            session.commit()

            return {
                "success": True,
                "message": "GCDR token updated successfully"
            }

        finally:
            pass  # No session to close when using Supabase

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating GCDR token: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating token: {str(e)}")

@router.delete("/gcdr/tokens/{token_id}")
async def delete_gcdr_token(token_id: int, email: Optional[str] = None):
    """Delete a GCDR token"""
    try:
        admin_service = SupabaseAdminService()

        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")

        # Get admin ID
        admin_profile = admin_service.get_user_profile_by_email(email)
        if not admin_profile:
            raise HTTPException(status_code=404, detail="Admin profile not found")

        admin_id = admin_profile.get('user_id')

        # Delete token from Supabase
        try:
            from supabase_config import get_supabase_client
            supabase = get_supabase_client()

            # First check if token exists and belongs to admin
            token_result = supabase.table('gcdr').select('id').eq('id', token_id).eq('admin_id', admin_id).execute()

            if not token_result.data or len(token_result.data) == 0:
                raise HTTPException(status_code=404, detail="Token not found")

            # Delete the token
            delete_result = supabase.table('gcdr').delete().eq('id', token_id).eq('admin_id', admin_id).execute()

            return {
                "success": True,
                "message": "GCDR token deleted successfully"
            }

        finally:
            pass  # No session to close when using Supabase

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting GCDR token: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting token: {str(e)}")

@router.post("/gcdr/tokens/{token_id}/test")
async def test_gcdr_token(token_id: int, request: Request):
    """Test if a GCDR token is working by making a Drive API call"""
    try:
        # Parse request body
        body = await request.json()
        email = body.get('email')

        admin_service = SupabaseAdminService()

        # Debug logging
        print(f"[GCDR Test] Testing token {token_id} for email: {email}")

        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            print(f"[GCDR Test] Profile lookup result: {profile}")
            if not profile:
                raise HTTPException(status_code=404, detail=f"User profile not found for email: {email}")
            if not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")

        # Get admin ID
        admin_profile = admin_service.get_user_profile_by_email(email)
        if not admin_profile:
            raise HTTPException(status_code=404, detail=f"Admin profile not found for email: {email}")

        print(f"[GCDR Test] Admin profile found: {admin_profile.get('id')}")

        admin_id = admin_profile.get('user_id')

        # Get the token from Supabase
        try:
            from supabase_config import get_supabase_client
            supabase = get_supabase_client()
            token_result = supabase.table('gcdr').select('*').eq('id', token_id).eq('admin_id', admin_id).execute()

            if not token_result.data or len(token_result.data) == 0:
                raise HTTPException(status_code=404, detail="Token not found")

            token = token_result.data[0]

            # Check if token is expired
            from datetime import datetime, timezone
            token_expires_at = token.get('token_expires_at')
            if token_expires_at:
                # Parse the datetime string and make it offset-aware
                if isinstance(token_expires_at, str):
                    expires_dt = datetime.fromisoformat(token_expires_at.replace('Z', '+00:00'))
                    if expires_dt.tzinfo is None:
                        expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                else:
                    expires_dt = token_expires_at

                # Compare with offset-aware current time
                now = datetime.now(timezone.utc)
                if expires_dt < now:
                    return {
                        "success": False,
                        "message": "Token is expired",
                        "expired": True
                    }

            # Test the token by making a simple Drive API call
            import requests

            headers = {
                'Authorization': f'{token.get("token_type", "Bearer")} {token["access_token"]}',
                'Accept': 'application/json'
            }

            # Test by listing files (limited to 10 to get more info)
            url = 'https://www.googleapis.com/drive/v3/files?pageSize=10&fields=files(id,name,mimeType,modifiedTime)&orderBy=modifiedTime desc'

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                all_files = data.get('files', [])
                files_count = len(all_files)

                # Count exam-related files using the same keywords as search_exam_files
                exam_keywords = [
                    'exam', 'examination', 'test', 'assessment', 'schedule', 'timetable',
                    'results', 'marks', 'grades', 'score', 'paper', 'question paper',
                    'final', 'midterm', 'quiz', 'evaluation', 'report card', 'infosheet',
                    'info sheet', 'info', 'sheet', 'timetable', 'time table', 'date sheet',
                    'syllabus', 'sa1', 'sa2', 'fa1', 'fa2', 'fa3', 'fa4',
                    'g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9', 'g10', 'g11', 'g12',
                    'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'grade11', 'grade12'
                ]

                exam_files = []
                for file in all_files:
                    file_name_lower = file.get('name', '').lower()
                    if any(keyword.lower() in file_name_lower for keyword in exam_keywords):
                        exam_files.append(file)

                # Update last_used_at in Supabase
                update_result = supabase.table('gcdr').update({
                    'last_used_at': 'now()'
                }).eq('id', token_id).execute()

                return {
                    "success": True,
                    "message": f"Token is working correctly. Found {files_count} total files, {len(exam_files)} exam-related files.",
                    "files_count": files_count,
                    "exam_files_count": len(exam_files),
                    "can_access_drive": True,
                    "sample_files": [f.get('name', 'Unknown') for f in all_files[:3]],  # Show first 3 file names
                    "exam_files": [f.get('name', 'Unknown') for f in exam_files[:3]]  # Show first 3 exam files
                }
            else:
                error_data = response.json()
                return {
                    "success": False,
                    "message": f"Token test failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                    "status_code": response.status_code,
                    "can_access_drive": False
                }

        finally:
            pass  # No session to close when using Supabase

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error testing GCDR token: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing token: {str(e)}")

@router.post("/regenerate-embeddings")
async def regenerate_all_embeddings(email: Optional[str] = None):
    """
    Regenerate embeddings for all records across all tables
    Requires admin privileges
    """
    try:
        admin_service = SupabaseAdminService()

        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")

        print(f"[Admin] 🔄 Starting embedding regeneration for all records...")

        # Get embedding generator and regenerate all embeddings
        embedding_gen = get_embedding_generator()
        results = embedding_gen.regenerate_all_embeddings()

        return {
            "success": True,
            "message": f"Embedding regeneration completed. Generated {sum(results.values()) - results['errors']} embeddings across {len(results) - 1} tables",
            "results": results,
            "summary": {
                "total_embeddings": sum(results.values()) - results['errors'],
                "total_errors": results['errors'],
                "tables_processed": len(results) - 1
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Admin] ❌ Error during embedding regeneration: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Embedding regeneration failed: {str(e)}")

@router.get("/gcdr/connect")
async def connect_google_drive(request: Request, email: str = Query(..., description="Admin email")):
    """Redirect to Google OAuth for Drive access"""

    # Get admin profile
    admin_service = SupabaseAdminService()
    admin_profile = admin_service.get_user_profile_by_email(email)

    if not admin_profile:
        raise HTTPException(status_code=404, detail="Admin profile not found")

    # Google OAuth configuration
    # Use Sensitive Client ID for Drive access
    client_id = GOOGLE_SENSITIVE_CLIENT_ID or GOOGLE_CLIENT_ID
    print(f"[DEBUG] GCDR Connect - Using Client ID: {client_id}")
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", f"{request.base_url}api/admin/gcdr/callback")

    if not client_id:
        raise HTTPException(status_code=500, detail="Google OAuth client ID not configured")

    # OAuth scopes for Drive read access + user info
    scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]

    # Build authorization URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={' '.join(scopes)}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={email}"  # Pass email as state for callback
    )

    return RedirectResponse(url=auth_url)

@router.get("/gcdr/callback")
async def google_drive_oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter (admin email)"),
    error: Optional[str] = Query(None, description="Error if OAuth failed")
):
    """Handle Google OAuth callback for Drive access"""

    if error:
        return RedirectResponse(url=f"/admin?error=oauth_error&message={error}")

    try:
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        # Use Sensitive Credentials for Drive access
        client_id = GOOGLE_SENSITIVE_CLIENT_ID or GOOGLE_CLIENT_ID
        client_secret = GOOGLE_SENSITIVE_CLIENT_SECRET or GOOGLE_CLIENT_SECRET
        redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")

        print(f"[GCDR OAuth] Client ID: {client_id[:20]}...")
        print(f"[GCDR OAuth] Redirect URI: {redirect_uri}")
        print(f"[GCDR OAuth] Code received: {code[:20]}...")

        if not all([client_id, client_secret, redirect_uri]):
            print(f"[GCDR OAuth] Missing config: client_id={bool(client_id)}, client_secret={bool(client_secret)}, redirect_uri={bool(redirect_uri)}")
            raise HTTPException(status_code=500, detail="Google OAuth credentials not configured")

        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }

        import requests
        print(f"[GCDR OAuth] Exchanging code for tokens...")
        token_response = requests.post(token_url, data=token_data)

        if token_response.status_code != 200:
            print(f"[GCDR OAuth] Token exchange failed: {token_response.status_code} - {token_response.text}")
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_response.text}")

        token_info = token_response.json()
        print(f"[GCDR OAuth] Token exchange successful, got access_token: {bool(token_info.get('access_token'))}")

        access_token = token_info.get("access_token")
        refresh_token = token_info.get("refresh_token")
        expires_in = token_info.get("expires_in", 3600)

        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")

        # First, validate the token using tokeninfo endpoint
        tokeninfo_url = f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
        print(f"[GCDR OAuth] Validating token...")
        tokeninfo_response = requests.get(tokeninfo_url)

        if tokeninfo_response.status_code != 200:
            print(f"[GCDR OAuth] Token validation failed: {tokeninfo_response.status_code} - {tokeninfo_response.text}")
            raise HTTPException(status_code=400, detail=f"Token validation failed: {tokeninfo_response.text}")

        token_info = tokeninfo_response.json()
        user_email = token_info.get('email')

        if not user_email:
            print(f"[GCDR OAuth] No email in token info: {token_info}")
            raise HTTPException(status_code=400, detail="Failed to get user email from token")

        print(f"[GCDR OAuth] Token validated for user: {user_email}")
        user_info = {"email": user_email}  # Minimal user info

        user_email = user_info.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="Failed to get user email from token")

        # Get admin profile
        admin_service = SupabaseAdminService()
        admin_profile = admin_service.get_user_profile_by_email(state)  # state contains admin email

        if not admin_profile:
            raise HTTPException(status_code=404, detail="Admin profile not found")

        # Use 'id' from user_profiles (not 'user_id' which is auth.users.id)
        # google_integrations.admin_id references user_profiles.id
        admin_id = admin_profile.get('user_id')
        
        if not admin_id:
            raise HTTPException(status_code=400, detail="User profile ID not found")
        
        # Calculate token expiry
        from datetime import datetime, timedelta
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Store token in Supabase
        try:
            from supabase_config import get_supabase_client
            supabase = get_supabase_client()

            # Check if token already exists for this admin and email
            existing_result = supabase.table('gcdr').select('id').eq('admin_id', admin_id).eq('user_email', user_email).execute()

            if existing_result.data and len(existing_result.data) > 0:
                # Update existing token
                update_data = {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': token_expires_at.isoformat(),
                    'is_active': True,
                    'updated_at': 'now()'
                }
                supabase.table('gcdr').update(update_data).eq('id', existing_result.data[0]['id']).execute()
            else:
                # Create new token
                insert_data = {
                    'admin_id': admin_id,
                    'user_email': user_email,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': token_expires_at.isoformat(),
                    'scope': "https://www.googleapis.com/auth/drive.readonly",
                    'token_type': "Bearer",
                    'is_active': True,
                    'project_name': "Prakriti Drive Access"
                }
                supabase.table('gcdr').insert(insert_data).execute()

            # Redirect back to admin dashboard with success
            return RedirectResponse(url=f"/admin?tab=drive&success=connected&email={user_email}")

        except Exception as e:
            print(f"[GCDR OAuth] Database error: {e}")
            return RedirectResponse(url=f"/admin?tab=drive&error=database_error&message={str(e)}")

    except Exception as e:
        print(f"[GCDR OAuth] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"/admin?tab=drive&error=unexpected_error&message={str(e)}")

@router.post("/gcdr/refresh-tokens")
async def refresh_all_gcdr_tokens(email: Optional[str] = None):
    """Refresh all expired GCDR tokens"""
    try:
        admin_service = SupabaseAdminService()

        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")

        # Import from root (already in sys.path from top-level)
        from token_refresh_service import refresh_expired_tokens
        refresh_expired_tokens()
    except Exception as e:
        print(f"[Admin] Error refreshing tokens (import error?): {e}")
        # Log the full traceback for debugging
        import traceback
        traceback.print_exc()
        raise e

        return {
            "success": True,
            "message": "Token refresh process completed. Check logs for details."
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Admin] Error refreshing tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")

    except Exception as e:
        print(f"[GCDR OAuth] Error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"/admin?tab=drive&error=connection_failed&message={str(e)}")

# =============================================
# GOOGLE CLASSROOM OAUTH ENDPOINTS (FOR ASSIGNMENTS)
# =============================================

@router.get("/classroom/connect")
async def connect_google_classroom(request: Request, email: str = Query(..., description="Teacher email")):
    """Redirect to Google OAuth for Classroom assignment access"""
    
    # Get admin/teacher profile
    admin_service = SupabaseAdminService()
    admin_profile = admin_service.get_user_profile_by_email(email)
    
    if not admin_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Google OAuth configuration
    # Use Sensitive Client ID for Classroom access
    client_id = GOOGLE_SENSITIVE_CLIENT_ID or GOOGLE_CLIENT_ID
    
    # Use separate redirect URI for Classroom (since GOOGLE_OAUTH_REDIRECT_URI is for Drive)
    # Construct from request or use environment variable
    redirect_uri = os.getenv("GOOGLE_CLASSROOM_OAUTH_REDIRECT_URI")
    if not redirect_uri:
        # Construct from request base URL
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/admin/classroom/callback"
    
    if not client_id:
        raise HTTPException(status_code=500, detail="Google OAuth client ID not configured")
    
    # OAuth scopes for Classroom - ONLY for assignments (courses, rosters, announcements handled by DWD)
    scopes = [
        "https://www.googleapis.com/auth/classroom.courses.readonly",  # Needed to list courses
        "https://www.googleapis.com/auth/classroom.coursework.me.readonly",  # For own assignments
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    
    # Build authorization URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={' '.join(scopes)}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={email}"  # Pass email as state for callback
    )
    
    return RedirectResponse(url=auth_url)

@router.get("/classroom/callback")
async def google_classroom_oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter (teacher email)"),
    error: Optional[str] = Query(None, description="Error if OAuth failed")
):
    """Handle Google OAuth callback for Classroom assignment access"""
    
    if error:
        return RedirectResponse(url=f"/admin?tab=classroom&error=oauth_error&message={error}")
    
    try:
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        
        # Use Sensitive Credentials for Classroom access
        client_id = GOOGLE_SENSITIVE_CLIENT_ID or GOOGLE_CLIENT_ID
        client_secret = GOOGLE_SENSITIVE_CLIENT_SECRET or GOOGLE_CLIENT_SECRET
        
        # Use separate redirect URI for Classroom, or fallback to constructing from request
        # Since GOOGLE_OAUTH_REDIRECT_URI is for Drive, we need a separate one for Classroom
        redirect_uri = os.getenv("GOOGLE_CLASSROOM_OAUTH_REDIRECT_URI")
        if not redirect_uri:
            # Construct from request if not set
            from fastapi import Request as FastAPIRequest
            # Note: In callback, we need to reconstruct the redirect URI that was used in /connect
            # Default to localhost:8000 for development, or use the same pattern as Drive
            base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
            redirect_uri = f"{base_url}/api/admin/classroom/callback"
        
        if not all([client_id, client_secret]):
            raise HTTPException(status_code=500, detail="Google OAuth credentials not configured")
        
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        import requests
        print(f"[Classroom OAuth] Exchanging code for tokens...")
        token_response = requests.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            print(f"[Classroom OAuth] Token exchange failed: {token_response.status_code} - {token_response.text}")
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_response.text}")
        
        token_info = token_response.json()
        access_token = token_info.get("access_token")
        refresh_token = token_info.get("refresh_token")
        expires_in = token_info.get("expires_in", 3600)
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Validate token and get user email
        tokeninfo_url = f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
        tokeninfo_response = requests.get(tokeninfo_url)
        
        if tokeninfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Token validation failed")
        
        token_info_data = tokeninfo_response.json()
        user_email = token_info_data.get('email')
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Failed to get user email from token")
        
        print(f"[Classroom OAuth] Token validated for user: {user_email}")
        
        # Get admin/teacher profile
        admin_service = SupabaseAdminService()
        admin_profile = admin_service.get_user_profile_by_email(state)
        
        if not admin_profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Use 'id' from user_profiles (not 'user_id' which is auth.users.id)
        # google_integrations.admin_id references user_profiles.id
        admin_id = admin_profile.get('id')
        
        if not admin_id:
            raise HTTPException(status_code=400, detail="User profile ID not found")
        
        # Calculate token expiry
        from datetime import datetime, timedelta
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Store token in Supabase (using google_integrations table)
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        
        scope_string = " ".join([
            "https://www.googleapis.com/auth/classroom.courses.readonly",
            "https://www.googleapis.com/auth/classroom.coursework.me.readonly"
        ])
        
        # Check if token already exists
        existing_result = supabase.table('google_integrations').select('id').eq('admin_id', admin_id).eq('service_type', 'classroom').execute()
        
        if existing_result.data and len(existing_result.data) > 0:
            # Update existing token
            update_data = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_expires_at': token_expires_at.isoformat(),
                'scope': scope_string,
                'is_active': True,
                'updated_at': datetime.utcnow().isoformat()
            }
            supabase.table('google_integrations').update(update_data).eq('id', existing_result.data[0]['id']).execute()
        else:
            # Create new token
            insert_data = {
                'admin_id': admin_id,
                'service_type': 'classroom',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_expires_at': token_expires_at.isoformat(),
                'scope': scope_string,
                'is_active': True
            }
            supabase.table('google_integrations').insert(insert_data).execute()
        
        # Redirect back to admin dashboard
        return RedirectResponse(url=f"/admin?tab=classroom&success=connected&email={user_email}")
        
    except Exception as e:
        print(f"[Classroom OAuth] Error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"/admin?tab=classroom&error=oauth_error&message={str(e)}")

@router.get("/classroom/oauth-token")
async def get_classroom_oauth_token(email: Optional[str] = None):
    """Get Classroom OAuth token for the admin"""
    try:
        admin_service = SupabaseAdminService()
        
        # Verify admin privileges
        if email:
            profile = admin_service.get_user_profile_by_email(email)
            if not profile or not profile.get('admin_privileges'):
                raise HTTPException(status_code=403, detail="Admin privileges required")
            # Use 'id' from user_profiles (not 'user_id' which is auth.users.id)
            admin_id = profile.get('id')
        else:
            raise HTTPException(status_code=400, detail="Email is required")
        
        if not admin_id:
            raise HTTPException(status_code=400, detail="User profile ID not found")
        
        # Get token from database
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        
        token_result = supabase.table('google_integrations').select(
            'id, admin_id, service_type, access_token, refresh_token, token_expires_at, scope, is_active, created_at, updated_at'
        ).eq('admin_id', admin_id).eq('service_type', 'classroom').eq('is_active', True).maybe_single().execute()
        
        if token_result.data:
            return {
                "success": True,
                "token": token_result.data
            }
        else:
            return {
                "success": True,
                "token": None
            }
    except Exception as e:
        print(f"[Classroom OAuth] Error fetching token: {e}")
        return {
            "success": False,
            "token": None,
            "error": str(e)
        }

@router.post("/classroom/sync-assignments")
async def sync_assignments_oauth(email: str = Query(..., description="Teacher email")):
    """Sync assignments using OAuth token and store in google_classroom_coursework table"""
    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        
        # Get teacher profile
        admin_service = SupabaseAdminService()
        admin_profile = admin_service.get_user_profile_by_email(email)
        
        if not admin_profile:
            raise HTTPException(status_code=404, detail="Teacher profile not found")
        
        # Use 'id' from user_profiles for admin_id (references user_profiles.id)
        admin_id = admin_profile.get('id')
        # Use 'user_id' for user_id (references auth.users.id) - needed for google_classroom_courses
        user_id = admin_profile.get('user_id')
        
        if not admin_id:
            raise HTTPException(status_code=400, detail="User profile ID not found")
        
        # Get OAuth token from database
        token_result = supabase.table('google_integrations').select(
            'access_token, refresh_token, token_expires_at'
        ).eq('admin_id', admin_id).eq('service_type', 'classroom').eq('is_active', True).single().execute()
        
        if not token_result.data:
            raise HTTPException(status_code=404, detail="No active Classroom OAuth token found. Please connect Google Classroom first.")
        
        access_token = token_result.data['access_token']
        token_expires_at = token_result.data.get('token_expires_at')
        
        # Check if token is expired and refresh if needed
        import requests
        if token_expires_at:
            expires_dt = datetime.fromisoformat(token_expires_at.replace('Z', '+00:00'))
            # Use timezone-aware datetime for comparison
            if expires_dt < datetime.now(timezone.utc):
                # Refresh token
                refresh_token = token_result.data.get('refresh_token')
                if refresh_token:
                    refresh_response = requests.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": GOOGLE_SENSITIVE_CLIENT_ID or GOOGLE_CLIENT_ID,
                            "client_secret": GOOGLE_SENSITIVE_CLIENT_SECRET or GOOGLE_CLIENT_SECRET,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token"
                        }
                    )
                    if refresh_response.status_code == 200:
                        refresh_data = refresh_response.json()
                        access_token = refresh_data['access_token']
                        new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=refresh_data.get('expires_in', 3600))
                        # Update token in database
                        supabase.table('google_integrations').update({
                            'access_token': access_token,
                            'token_expires_at': new_expires_at.isoformat()
                        }).eq('admin_id', admin_id).eq('service_type', 'classroom').execute()
        
        # Fetch all courses using OAuth token
        headers = {"Authorization": f"Bearer {access_token}"}
        courses_response = requests.get(
            "https://classroom.googleapis.com/v1/courses",
            headers=headers
        )
        
        if courses_response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch courses: {courses_response.text}")
        
        courses = courses_response.json().get('courses', [])
        print(f"[Classroom OAuth Sync] Found {len(courses)} courses")
        
        # Sync stats
        assignments_synced = 0
        assignments_updated = 0
        assignments_created = 0
        
        def parse_google_timestamp(timestamp: str = None) -> str:
            """Parse Google timestamp to ISO format"""
            if not timestamp:
                return None
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).isoformat()
            except:
                return None
        
        def parse_max_points(max_points_value):
            """Parse maxPoints - can be int, float, or dict with 'value' key"""
            if not max_points_value:
                return None
            try:
                if isinstance(max_points_value, (int, float)):
                    return float(max_points_value)
                elif isinstance(max_points_value, dict):
                    value = max_points_value.get('value')
                    if value is not None:
                        return float(value)
                return None
            except (ValueError, TypeError):
                return None
        
        # Fetch assignments for each course
        for course in courses:
            course_id = course.get('id')
            course_name = course.get('name', 'Unknown')
            
            if not course_id:
                continue
            
            print(f"[Classroom OAuth Sync] Processing course: {course_name} ({course_id})")
            
            # Get or create course in database
            existing_course = supabase.table('google_classroom_courses').select('id').eq('course_id', course_id).limit(1).execute()
            
            db_course_id = None
            if existing_course.data and len(existing_course.data) > 0:
                db_course_id = existing_course.data[0]['id']
            else:
                # Create course entry if it doesn't exist
                course_data = {
                    "user_id": user_id,
                    "course_id": course_id,
                    "name": course.get('name', ''),
                    "description": course.get('description'),
                    "section": course.get('section'),
                    "room": course.get('room'),
                    "alternate_link": course.get('alternateLink'),
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }
                result = supabase.table('google_classroom_courses').insert(course_data).execute()
                if result.data and len(result.data) > 0:
                    db_course_id = result.data[0].get('id')
            
            if not db_course_id:
                print(f"⚠️ [Classroom OAuth Sync] Could not get database course ID for {course_id}")
                continue
            
            # Fetch coursework (assignments) for this course
            coursework_response = requests.get(
                f"https://classroom.googleapis.com/v1/courses/{course_id}/courseWork",
                headers=headers
            )
            
            if coursework_response.status_code == 200:
                coursework_list = coursework_response.json().get('courseWork', [])
                print(f"[Classroom OAuth Sync] Found {len(coursework_list)} assignments in {course_name}")
                
                for assignment in coursework_list:
                    cw_id = assignment.get('id')
                    if not cw_id:
                        continue
                    
                    # Parse due date
                    due_date = None
                    due_time = None
                    if assignment.get('dueDate'):
                        due_date_str = f"{assignment['dueDate'].get('year', 2000)}-{assignment['dueDate'].get('month', 1):02d}-{assignment['dueDate'].get('day', 1):02d}"
                        due_date = parse_google_timestamp(f"{due_date_str}T00:00:00Z")
                    elif assignment.get('dueTime'):
                        due_date = parse_google_timestamp(assignment['dueTime'])
                    
                    # Extract time portion from dueTime if it exists (max 20 chars for VARCHAR(20))
                    if assignment.get('dueTime'):
                        due_time_raw = assignment.get('dueTime')
                        if isinstance(due_time_raw, str):
                            # If it's a timestamp string, extract time portion (HH:MM:SS)
                            try:
                                if 'T' in due_time_raw:
                                    # ISO format: "2024-01-15T14:30:00Z" -> "14:30:00"
                                    time_part = due_time_raw.split('T')[1].split('Z')[0].split('+')[0]
                                    due_time = time_part[:20]  # Ensure max 20 chars
                                elif ':' in due_time_raw:
                                    # Already a time string, truncate to 20 chars
                                    due_time = due_time_raw[:20]
                                else:
                                    due_time = None
                            except:
                                due_time = None
                        elif isinstance(due_time_raw, dict):
                            # If it's a TimeOfDay object: {"hours": 14, "minutes": 30}
                            hours = due_time_raw.get('hours', 0)
                            minutes = due_time_raw.get('minutes', 0)
                            seconds = due_time_raw.get('seconds', 0)
                            due_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    # Prepare assignment data
                    assignment_data = {
                        "course_id": db_course_id,
                        "coursework_id": cw_id,
                        "title": assignment.get('title', ''),
                        "description": assignment.get('description'),
                        "materials": assignment.get('materials'),
                        "state": assignment.get('state'),
                        "alternate_link": assignment.get('alternateLink'),
                        "creation_time": parse_google_timestamp(assignment.get('creationTime')),
                        "update_time": parse_google_timestamp(assignment.get('updateTime')),
                        "due_date": due_date,
                        "due_time": due_time,
                        "max_points": parse_max_points(assignment.get('maxPoints')),
                        "work_type": assignment.get('workType'),
                        "associated_with_developer": assignment.get('associatedWithDeveloper', False),
                        "assignee_mode": assignment.get('assigneeMode'),
                        "individual_students_options": assignment.get('individualStudentsOptions'),
                        "submission_modification_mode": assignment.get('submissionModificationMode'),
                        "creator_user_id": assignment.get('creatorUserId'),
                        "topic_id": assignment.get('topicId'),
                        "grade_category": assignment.get('gradeCategory'),
                        "assignment": assignment.get('assignment'),
                        "multiple_choice_question": assignment.get('multipleChoiceQuestion'),
                        "last_synced_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Upsert assignment
                    existing = supabase.table('google_classroom_coursework').select('id').eq('course_id', db_course_id).eq('coursework_id', cw_id).limit(1).execute()
                    
                    if existing.data and len(existing.data) > 0:
                        supabase.table('google_classroom_coursework').update(assignment_data).eq('id', existing.data[0]['id']).execute()
                        assignments_updated += 1
                    else:
                        supabase.table('google_classroom_coursework').insert(assignment_data).execute()
                        assignments_created += 1
                    
                    assignments_synced += 1
            else:
                print(f"⚠️ [Classroom OAuth Sync] Failed to fetch assignments for course {course_name}: {coursework_response.text}")
        
        return {
            "success": True,
            "message": f"Synced {assignments_synced} assignments",
            "assignments_synced": assignments_synced,
            "assignments_created": assignments_created,
            "assignments_updated": assignments_updated,
            "courses_processed": len(courses)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Classroom OAuth Sync] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to sync assignments: {str(e)}")

