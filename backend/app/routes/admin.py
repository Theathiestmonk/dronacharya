from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import json
from datetime import datetime, timedelta
import os

from ..core.database import get_db
from ..models.admin import Admin, GoogleIntegration, ClassroomData, CalendarData
# Auth functions removed - using Supabase authentication in frontend
from ..services.supabase_admin import SupabaseAdminService
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["admin"])

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

@router.get("/auth-url")
async def get_google_auth_url(service: str):
    """Generate Google OAuth URL for admin integration"""
    print(f"🔍 Auth URL request for service: {service}")
    print(f"🔍 GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
    print(f"🔍 GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")
    
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID not configured")
    
    if service not in ["classroom", "calendar", "both"]:
        raise HTTPException(status_code=400, detail="Service must be 'classroom', 'calendar', or 'both'")
    
    if service == "both":
        scopes = GOOGLE_CLASSROOM_SCOPES + GOOGLE_CALENDAR_SCOPES
    elif service == "classroom":
        scopes = GOOGLE_CLASSROOM_SCOPES
    else:
        scopes = GOOGLE_CALENDAR_SCOPES
    scope_string = " ".join(scopes)
    
    # CRITICAL: Ensure redirect_uri points to FRONTEND, not backend
    redirect_uri = GOOGLE_REDIRECT_URI
    if "localhost:8000" in redirect_uri or "/api/" in redirect_uri:
        print(f"⚠️ ERROR: redirect_uri points to backend: {redirect_uri}")
        print(f"⚠️ FORCING redirect_uri to frontend: http://localhost:3000/admin/callback")
        redirect_uri = "http://localhost:3000/admin/callback"
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope_string}&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={service}"
    )
    
    print(f"🔍 Generated auth URL with redirect_uri: {redirect_uri}")
    print(f"🔍 Full auth URL: {auth_url}")
    return {"auth_url": auth_url, "service": service}

@router.get("/callback")
async def handle_google_callback(
    code: str,
    state: str,
    email: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    DEPRECATED: This route should NOT be used.
    OAuth callbacks should go through Next.js frontend at /admin/callback which calls /api/admin/callback.
    This route is kept for backward compatibility but will reject requests that don't have email.
    """
    print(f"⚠️ [BACKEND CALLBACK] DEPRECATED ROUTE CALLED - This should use Next.js API route instead")
    print(f"⚠️ [BACKEND CALLBACK] Code: {code[:20]}..., State: {state}, Email: {email}")
    
    # REJECT requests without email - force using Next.js callback API
    if not email:
        print(f"❌ [BACKEND CALLBACK] Rejecting callback without email - must use Next.js callback route")
        raise HTTPException(
            status_code=400, 
            detail="This route requires email parameter. Please use the frontend callback at /admin/callback which will call the Next.js API route."
        )
    
    if state not in ["classroom", "calendar", "both"]:
        raise HTTPException(status_code=400, detail="Invalid service type")
    
    try:
        # Use Supabase service
        admin_service = SupabaseAdminService()
        
        # Get CURRENT USER by email - NO FALLBACK
        print(f"🔍 [BACKEND CALLBACK] Looking for admin with email: {email}")
        admin = admin_service.get_admin(email)
        
        if not admin:
            print(f"❌ [BACKEND CALLBACK] Admin not found for email: {email}")
            raise HTTPException(
                status_code=404, 
                detail=f"Admin profile not found for {email}. Please ensure this user has admin_privileges=true."
            )
        
        print(f"✅ [BACKEND CALLBACK] Found admin: {admin['email']} (ID: {admin['id']})")
        
        # Exchange code for tokens
        token_data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data
            )
            response.raise_for_status()
            tokens = response.json()
        
        print(f"🔍 [BACKEND CALLBACK] Tokens received, storing under admin_id: {admin['id']}")
        
        # Store tokens for each service - using current user's ID
        if state == "both":
            # Create integration for classroom
            admin_service.create_google_integration(
                admin_id=admin['id'],  # Current user's ID
                service_type="classroom",
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_expires_at=datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
                scope=" ".join(GOOGLE_CLASSROOM_SCOPES)
            )
            
            # Create integration for calendar
            admin_service.create_google_integration(
                admin_id=admin['id'],  # Current user's ID
                service_type="calendar",
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_expires_at=datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
                scope=" ".join(GOOGLE_CALENDAR_SCOPES)
            )
            
            # Enable both services
            admin_service.update_admin_integrations(admin['id'], classroom_enabled=True, calendar_enabled=True)
        
        else:
            # Single service integration
            admin_service.create_google_integration(
                admin_id=admin['id'],  # Current user's ID
                service_type=state,
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_expires_at=datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
                scope=" ".join(GOOGLE_CLASSROOM_SCOPES if state == "classroom" else GOOGLE_CALENDAR_SCOPES)
            )
            
            if state == "classroom":
                admin_service.update_admin_integrations(admin['id'], classroom_enabled=True)
            else:
                admin_service.update_admin_integrations(admin['id'], calendar_enabled=True)
        
        print(f"✅ [BACKEND CALLBACK] Successfully stored integrations for {admin['email']} (ID: {admin['id']})")
        
        # Redirect back to admin dashboard
        return RedirectResponse(url="http://localhost:3000/admin?connected=true", status_code=302)
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Integration error: {str(e)}")

@router.get("/integrations")
async def get_admin_integrations(email: Optional[str] = None):
    """Get admin's Google integrations status"""
    
    try:
        admin_service = SupabaseAdminService()
        admin = None
        if email:
            admin = admin_service.get_admin(email)
        
        if not admin:
            admin = admin_service.get_first_admin()
        
        if not admin:
            print("No admin profile found in user_profiles")
            return {
                "classroom_enabled": False,
                "calendar_enabled": False,
                "integrations": []
            }
        
        return admin_service.get_integration_status(admin['id'])
        
    except Exception as e:
        print(f"Error getting integrations: {e}")
        return {
            "classroom_enabled": False,
            "calendar_enabled": False,
            "integrations": []
        }

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
