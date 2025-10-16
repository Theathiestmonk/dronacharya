from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import json
from datetime import datetime, timedelta
import os

from ..core.database import get_db
from ..models.admin import Admin, GoogleIntegration, ClassroomData, CalendarData
from ..core.auth import get_current_user, authenticate_admin, create_access_token
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

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(login_data: AdminLogin, db: Session = Depends(get_db)):
    """Login endpoint for admin users."""
    admin = authenticate_admin(login_data.email, login_data.password, db)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    access_token = create_access_token(data={"sub": admin.email})
    
    return AdminLoginResponse(
        access_token=access_token,
        token_type="bearer",
        admin={
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "role": admin.role,
            "is_active": admin.is_active
        }
    )

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/api/admin/callback")

# Google API scopes
GOOGLE_CLASSROOM_SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly"
]

GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly"
]

@router.get("/auth-url")
async def get_google_auth_url(service: str, current_user: Admin = Depends(get_current_user)):
    """Generate Google OAuth URL for admin integration"""
    if service not in ["classroom", "calendar"]:
        raise HTTPException(status_code=400, detail="Service must be 'classroom' or 'calendar'")
    
    # Check if user is admin
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    scopes = GOOGLE_CLASSROOM_SCOPES if service == "classroom" else GOOGLE_CALENDAR_SCOPES
    scope_string = " ".join(scopes)
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scope_string}&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={service}"
    )
    
    return {"auth_url": auth_url, "service": service}

@router.post("/callback")
async def handle_google_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """Handle Google OAuth callback and store tokens"""
    if state not in ["classroom", "calendar"]:
        raise HTTPException(status_code=400, detail="Invalid service type")
    
    # Check if user is admin
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
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
        
        # Store tokens in database
        integration = GoogleIntegration(
            admin_id=current_user.id,
            service_type=state,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_expires_at=datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
            scope=" ".join(GOOGLE_CLASSROOM_SCOPES if state == "classroom" else GOOGLE_CALENDAR_SCOPES)
        )
        
        db.add(integration)
        
        # Update admin record
        admin = db.query(Admin).filter(Admin.email == current_user.email).first()
        if not admin:
            admin = Admin(
                email=current_user.email,
                name=current_user.name,
                role="admin"
            )
            db.add(admin)
        
        if state == "classroom":
            admin.google_classroom_enabled = True
        else:
            admin.google_calendar_enabled = True
            
        db.commit()
        
        return {
            "success": True,
            "message": f"Google {state} integration successful",
            "service": state
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Integration error: {str(e)}")

@router.get("/integrations")
async def get_admin_integrations(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """Get admin's Google integrations status"""
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    admin = db.query(Admin).filter(Admin.email == current_user.email).first()
    if not admin:
        return {
            "classroom_enabled": False,
            "calendar_enabled": False,
            "integrations": []
        }
    
    integrations = db.query(GoogleIntegration).filter(
        GoogleIntegration.admin_id == admin.id,
        GoogleIntegration.is_active == True
    ).all()
    
    return {
        "classroom_enabled": admin.google_classroom_enabled,
        "calendar_enabled": admin.google_calendar_enabled,
        "integrations": [
            {
                "service_type": integration.service_type,
                "created_at": integration.created_at,
                "expires_at": integration.token_expires_at
            }
            for integration in integrations
        ]
    }

@router.post("/sync/classroom")
async def sync_classroom_data(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """Sync Google Classroom data"""
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    admin = db.query(Admin).filter(Admin.email == current_user.email).first()
    if not admin or not admin.google_classroom_enabled:
        raise HTTPException(status_code=400, detail="Google Classroom not integrated")
    
    integration = db.query(GoogleIntegration).filter(
        GoogleIntegration.admin_id == admin.id,
        GoogleIntegration.service_type == "classroom",
        GoogleIntegration.is_active == True
    ).first()
    
    if not integration:
        raise HTTPException(status_code=400, detail="No active Classroom integration found")
    
    try:
        # Refresh token if needed
        if integration.token_expires_at <= datetime.utcnow():
            await refresh_google_token(integration, db)
        
        # Fetch courses from Google Classroom API
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {integration.access_token}"}
            response = await client.get(
                "https://classroom.googleapis.com/v1/courses",
                headers=headers
            )
            response.raise_for_status()
            courses_data = response.json()
        
        # Store/update courses in database
        courses_synced = 0
        for course in courses_data.get("courses", []):
            existing_course = db.query(ClassroomData).filter(
                ClassroomData.admin_id == admin.id,
                ClassroomData.course_id == course["id"]
            ).first()
            
            if existing_course:
                # Update existing course
                existing_course.course_name = course.get("name", "")
                existing_course.course_description = course.get("description", "")
                existing_course.course_room = course.get("room", "")
                existing_course.course_section = course.get("section", "")
                existing_course.course_state = course.get("courseState", "")
                existing_course.teacher_email = course.get("teacherEmail", "")
                existing_course.raw_data = course
                existing_course.last_synced = datetime.utcnow()
            else:
                # Create new course
                new_course = ClassroomData(
                    admin_id=admin.id,
                    course_id=course["id"],
                    course_name=course.get("name", ""),
                    course_description=course.get("description", ""),
                    course_room=course.get("room", ""),
                    course_section=course.get("section", ""),
                    course_state=course.get("courseState", ""),
                    teacher_email=course.get("teacherEmail", ""),
                    raw_data=course
                )
                db.add(new_course)
            
            courses_synced += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Synced {courses_synced} courses from Google Classroom",
            "courses_synced": courses_synced
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Google Classroom API error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

@router.post("/sync/calendar")
async def sync_calendar_data(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """Sync Google Calendar data"""
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    admin = db.query(Admin).filter(Admin.email == current_user.email).first()
    if not admin or not admin.google_calendar_enabled:
        raise HTTPException(status_code=400, detail="Google Calendar not integrated")
    
    integration = db.query(GoogleIntegration).filter(
        GoogleIntegration.admin_id == admin.id,
        GoogleIntegration.service_type == "calendar",
        GoogleIntegration.is_active == True
    ).first()
    
    if not integration:
        raise HTTPException(status_code=400, detail="No active Calendar integration found")
    
    try:
        # Refresh token if needed
        if integration.token_expires_at <= datetime.utcnow():
            await refresh_google_token(integration, db)
        
        # Fetch events from Google Calendar API
        time_min = datetime.utcnow().isoformat() + "Z"
        time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {integration.access_token}"}
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers=headers,
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": True,
                    "orderBy": "startTime"
                }
            )
            response.raise_for_status()
            events_data = response.json()
        
        # Store/update events in database
        events_synced = 0
        for event in events_data.get("items", []):
            existing_event = db.query(CalendarData).filter(
                CalendarData.admin_id == admin.id,
                CalendarData.event_id == event["id"]
            ).first()
            
            start_time = datetime.fromisoformat(
                event["start"].get("dateTime", event["start"].get("date", "")).replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(
                event["end"].get("dateTime", event["end"].get("date", "")).replace("Z", "+00:00")
            )
            
            if existing_event:
                # Update existing event
                existing_event.event_title = event.get("summary", "")
                existing_event.event_description = event.get("description", "")
                existing_event.event_start = start_time
                existing_event.event_end = end_time
                existing_event.event_location = event.get("location", "")
                existing_event.event_status = event.get("status", "")
                existing_event.raw_data = event
                existing_event.last_synced = datetime.utcnow()
            else:
                # Create new event
                new_event = CalendarData(
                    admin_id=admin.id,
                    event_id=event["id"],
                    event_title=event.get("summary", ""),
                    event_description=event.get("description", ""),
                    event_start=start_time,
                    event_end=end_time,
                    event_location=event.get("location", ""),
                    event_status=event.get("status", ""),
                    calendar_id="primary",
                    raw_data=event
                )
                db.add(new_event)
            
            events_synced += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Synced {events_synced} events from Google Calendar",
            "events_synced": events_synced
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Google Calendar API error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

@router.get("/data/classroom")
async def get_classroom_data(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """Get synced classroom data for chatbot"""
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    admin = db.query(Admin).filter(Admin.email == current_user.email).first()
    if not admin:
        return {"courses": []}
    
    courses = db.query(ClassroomData).filter(
        ClassroomData.admin_id == admin.id
    ).all()
    
    return {
        "courses": [
            {
                "id": course.course_id,
                "name": course.course_name,
                "description": course.course_description,
                "room": course.course_room,
                "section": course.course_section,
                "state": course.course_state,
                "teacher_email": course.teacher_email,
                "last_synced": course.last_synced
            }
            for course in courses
        ]
    }

@router.get("/data/calendar")
async def get_calendar_data(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """Get synced calendar data for chatbot"""
    if not current_user.role or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    admin = db.query(Admin).filter(Admin.email == current_user.email).first()
    if not admin:
        return {"events": []}
    
    events = db.query(CalendarData).filter(
        CalendarData.admin_id == admin.id,
        CalendarData.event_start >= datetime.utcnow()
    ).order_by(CalendarData.event_start).all()
    
    return {
        "events": [
            {
                "id": event.event_id,
                "title": event.event_title,
                "description": event.event_description,
                "start": event.event_start.isoformat(),
                "end": event.event_end.isoformat(),
                "location": event.event_location,
                "status": event.event_status,
                "last_synced": event.last_synced
            }
            for event in events
        ]
    }

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
