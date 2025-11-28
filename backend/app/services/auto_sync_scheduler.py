"""
Automatic sync scheduler for Google Classroom and Calendar
Runs every 12 hours to sync all connected services
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import os

from supabase_config import get_supabase_client
from ..services.supabase_admin import SupabaseAdminService

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

class AutoSyncScheduler:
    """Scheduler for automatic syncing of Google services"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.supabase = get_supabase_client()
        self.admin_service = SupabaseAdminService()
        self.is_running = False
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            print("[AutoSync] Scheduler already running")
            return
        
        # Verify Supabase connection before starting
        if not self.supabase:
            print("[AutoSync] ⚠️ Warning: Supabase client not available. Scheduler will start but syncs may fail.")
        else:
            # Test connection
            try:
                # Simple query to test connectivity
                self.supabase.table('user_profiles').select('id').limit(1).execute()
                print("[AutoSync] ✅ Supabase connection verified")
            except Exception as e:
                print(f"[AutoSync] ⚠️ Warning: Could not verify Supabase connection: {type(e).__name__}")
                print("[AutoSync] Scheduler will start but syncs may fail until connection is restored.")
        
        # Schedule sync job to run every 12 hours
        # Delay first sync to 30 seconds to allow app to fully start
        self.scheduler.add_job(
            self.sync_all_connected_services,
            trigger=IntervalTrigger(hours=12),
            id='auto_sync_job',
            name='Auto Sync Google Services',
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(seconds=30)  # Run first sync 30 seconds after startup
        )
        
        self.scheduler.start()
        self.is_running = True
        print("[AutoSync] Scheduler started - will run every 12 hours")
        print(f"[AutoSync] Next sync scheduled for: {self.scheduler.get_job('auto_sync_job').next_run_time}")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            print("[AutoSync] Scheduler stopped")
    
    async def sync_all_connected_services(self):
        """Sync all connected Google services for all admins"""
        print(f"[AutoSync] Starting automatic sync at {datetime.now().isoformat()}")
        
        try:
            # Get all active admins with Google integrations
            if not self.supabase:
                print("[AutoSync] ⚠️ Supabase client not available - skipping sync")
                return
            
            # Get all active integrations with network error handling
            try:
                integrations_result = self.supabase.table('google_integrations').select('*').eq('is_active', True).execute()
            except (httpx.ConnectError, httpx.ConnectTimeout, Exception) as e:
                error_type = type(e).__name__
                if 'getaddrinfo' in str(e) or 'ConnectError' in error_type:
                    print(f"[AutoSync] ⚠️ Network error connecting to Supabase: {error_type}")
                    print("[AutoSync] This is normal if there's no internet connection. Will retry on next scheduled run.")
                else:
                    print(f"[AutoSync] ⚠️ Error querying Supabase: {error_type}")
                return
            
            if not integrations_result.data:
                print("[AutoSync] No active integrations found")
                return
            
            # Group integrations by admin_id
            admin_integrations: Dict[str, List[Dict[str, Any]]] = {}
            for integration in integrations_result.data:
                admin_id = integration.get('admin_id')
                if admin_id not in admin_integrations:
                    admin_integrations[admin_id] = []
                admin_integrations[admin_id].append(integration)
            
            print(f"[AutoSync] Found {len(admin_integrations)} admins with active integrations")
            
            # Sync for each admin
            for admin_id, integrations in admin_integrations.items():
                try:
                    # Get admin profile with error handling
                    try:
                        admin_result = self.supabase.table('user_profiles').select('*').eq('id', admin_id).single().execute()
                    except (httpx.ConnectError, httpx.ConnectTimeout, Exception) as e:
                        print(f"[AutoSync] ⚠️ Network error fetching admin profile for {admin_id}: {type(e).__name__}")
                        continue
                    if not admin_result.data:
                        print(f"[AutoSync] Admin {admin_id} not found, skipping")
                        continue
                    
                    admin = admin_result.data
                    admin_email = admin.get('email')
                    
                    print(f"[AutoSync] Syncing services for admin: {admin_email}")
                    
                    # Check which services are connected
                    has_classroom = any(i['service_type'] == 'classroom' for i in integrations)
                    has_calendar = any(i['service_type'] == 'calendar' for i in integrations)
                    
                    # Sync Classroom if connected
                    if has_classroom:
                        try:
                            await self.sync_classroom_for_admin(admin_id, admin_email, integrations)
                            print(f"[AutoSync] ✅ Classroom sync completed for {admin_email}")
                        except Exception as e:
                            print(f"[AutoSync] ❌ Classroom sync failed for {admin_email}: {e}")
                    
                    # Sync Calendar if connected
                    if has_calendar:
                        try:
                            await self.sync_calendar_for_admin(admin_id, admin_email, integrations)
                            print(f"[AutoSync] ✅ Calendar sync completed for {admin_email}")
                        except Exception as e:
                            print(f"[AutoSync] ❌ Calendar sync failed for {admin_email}: {e}")
                    
                except Exception as e:
                    print(f"[AutoSync] Error syncing for admin {admin_id}: {e}")
                    continue
            
            print(f"[AutoSync] Automatic sync completed at {datetime.now().isoformat()}")
            
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            error_type = type(e).__name__
            print(f"[AutoSync] ⚠️ Network connectivity error: {error_type}")
            print("[AutoSync] This is normal if there's no internet connection. Will retry on next scheduled run.")
        except Exception as e:
            error_type = type(e).__name__
            print(f"[AutoSync] ⚠️ Unexpected error in sync_all_connected_services: {error_type}: {e}")
            # Only print full traceback for unexpected errors (not network errors)
            if 'getaddrinfo' not in str(e) and 'ConnectError' not in error_type:
                import traceback
                traceback.print_exc()
    
    async def sync_classroom_for_admin(self, admin_id: str, admin_email: str, integrations: List[Dict[str, Any]]):
        """Sync Google Classroom for a specific admin"""
        classroom_integration = next((i for i in integrations if i['service_type'] == 'classroom'), None)
        if not classroom_integration:
            return
        
        # Get access token (refresh if needed)
        access_token = classroom_integration['access_token']
        expires_at = classroom_integration.get('token_expires_at')
        
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expires_dt < datetime.utcnow():
                # Token expired, refresh it
                if not classroom_integration.get('refresh_token'):
                    print(f"[AutoSync] Token expired and no refresh token for {admin_email}")
                    return
                
                async with httpx.AsyncClient() as client:
                    refresh_response = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": GOOGLE_CLIENT_ID,
                            "client_secret": GOOGLE_CLIENT_SECRET,
                            "refresh_token": classroom_integration['refresh_token'],
                            "grant_type": "refresh_token"
                        }
                    )
                    if refresh_response.status_code != 200:
                        print(f"[AutoSync] Failed to refresh token for {admin_email}")
                        return
                    refresh_data = refresh_response.json()
                    access_token = refresh_data['access_token']
                    
                    # Update token in database
                    new_expires_at = datetime.utcnow() + timedelta(seconds=refresh_data.get('expires_in', 3600))
                    self.supabase.table('google_integrations').update({
                        'access_token': access_token,
                        'token_expires_at': new_expires_at.isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('id', classroom_integration['id']).execute()
        
        # Get user_id with error handling
        try:
            profile = self.supabase.table('user_profiles').select('user_id').eq('id', admin_id).single().execute()
            user_id = profile.data.get('user_id') if profile.data else None
            if not user_id:
                print(f"[AutoSync] User ID not found for admin {admin_email}")
                return
        except (httpx.ConnectError, httpx.ConnectTimeout, Exception) as e:
            print(f"[AutoSync] ⚠️ Network error fetching user_id for {admin_email}: {type(e).__name__}")
            return
        
        # Fetch all courses
        async with httpx.AsyncClient() as client:
            courses_response = await client.get(
                "https://classroom.googleapis.com/v1/courses",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if courses_response.status_code != 200:
                print(f"[AutoSync] Failed to fetch courses: {courses_response.status_code}")
                return
            
            courses = courses_response.json().get('courses', [])
            print(f"[AutoSync] Found {len(courses)} courses for {admin_email}")
            
            # Sync each course (simplified - just update course data)
            for course in courses:
                course_id = course.get('id')
                if not course_id:
                    continue
                
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
                    "last_synced_at": datetime.utcnow().isoformat()
                }
                
                # Upsert course with error handling
                try:
                    existing = self.supabase.table('google_classroom_courses').select('id').eq('user_id', user_id).eq('course_id', course_id).single().execute()
                    if existing.data:
                        self.supabase.table('google_classroom_courses').update(course_data).eq('id', existing.data['id']).execute()
                    else:
                        self.supabase.table('google_classroom_courses').insert(course_data).execute()
                except (httpx.ConnectError, httpx.ConnectTimeout, Exception) as e:
                    print(f"[AutoSync] ⚠️ Network error saving course {course_id}: {type(e).__name__}")
                    continue
    
    async def sync_calendar_for_admin(self, admin_id: str, admin_email: str, integrations: List[Dict[str, Any]]):
        """Sync Google Calendar for a specific admin"""
        calendar_integration = next((i for i in integrations if i['service_type'] == 'calendar'), None)
        if not calendar_integration:
            return
        
        # Get access token (refresh if needed)
        access_token = calendar_integration['access_token']
        expires_at = calendar_integration.get('token_expires_at')
        
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expires_dt < datetime.utcnow():
                if not calendar_integration.get('refresh_token'):
                    print(f"[AutoSync] Token expired and no refresh token for {admin_email}")
                    return
                
                async with httpx.AsyncClient() as client:
                    refresh_response = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": GOOGLE_CLIENT_ID,
                            "client_secret": GOOGLE_CLIENT_SECRET,
                            "refresh_token": calendar_integration['refresh_token'],
                            "grant_type": "refresh_token"
                        }
                    )
                    if refresh_response.status_code != 200:
                        print(f"[AutoSync] Failed to refresh token for {admin_email}")
                        return
                    refresh_data = refresh_response.json()
                    access_token = refresh_data['access_token']
                    
                    # Update token in database
                    new_expires_at = datetime.utcnow() + timedelta(seconds=refresh_data.get('expires_in', 3600))
                    self.supabase.table('google_integrations').update({
                        'access_token': access_token,
                        'token_expires_at': new_expires_at.isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('id', calendar_integration['id']).execute()
        
        # Get user_id with error handling
        try:
            profile = self.supabase.table('user_profiles').select('user_id').eq('id', admin_id).single().execute()
            user_id = profile.data.get('user_id') if profile.data else None
            if not user_id:
                print(f"[AutoSync] User ID not found for admin {admin_email}")
                return
        except (httpx.ConnectError, httpx.ConnectTimeout, Exception) as e:
            print(f"[AutoSync] ⚠️ Network error fetching user_id for {admin_email}: {type(e).__name__}")
            return
        
        # Fetch calendars
        async with httpx.AsyncClient() as client:
            calendars_response = await client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if calendars_response.status_code != 200:
                print(f"[AutoSync] Failed to fetch calendars: {calendars_response.status_code}")
                return
            
            calendars = calendars_response.json().get('items', [])
            print(f"[AutoSync] Found {len(calendars)} calendars for {admin_email}")
            
            # Sync each calendar
            time_min = datetime.utcnow().isoformat() + 'Z'
            time_max = (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z'
            
            for calendar in calendars:
                calendar_id = calendar.get('id')
                if not calendar_id:
                    continue
                
                # Update calendar metadata
                calendar_data = {
                    "user_id": user_id,
                    "calendar_id": calendar_id,
                    "summary": calendar.get('summary', ''),
                    "description": calendar.get('description'),
                    "time_zone": calendar.get('timeZone'),
                    "location": calendar.get('location'),
                    "last_synced_at": datetime.utcnow().isoformat()
                }
                
                try:
                    existing = self.supabase.table('google_calendar_calendars').select('id').eq('user_id', user_id).eq('calendar_id', calendar_id).single().execute()
                    if existing.data:
                        self.supabase.table('google_calendar_calendars').update(calendar_data).eq('id', existing.data['id']).execute()
                    else:
                        self.supabase.table('google_calendar_calendars').insert(calendar_data).execute()
                except (httpx.ConnectError, httpx.ConnectTimeout, Exception) as e:
                    print(f"[AutoSync] ⚠️ Network error saving calendar {calendar_id}: {type(e).__name__}")
                    continue
                
                # Fetch events for this calendar
                try:
                    events_response = await client.get(
                        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                        headers={"Authorization": f"Bearer {access_token}"},
                        params={
                            "timeMin": time_min,
                            "timeMax": time_max,
                            "singleEvents": True,
                            "orderBy": "startTime"
                        }
                    )
                    
                    if events_response.status_code == 200:
                        events = events_response.json().get('items', [])
                        for event in events:
                            event_id = event.get('id')
                            if not event_id:
                                continue
                            
                            start_time = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
                            end_time = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
                            
                            def parse_timestamp(ts):
                                if not ts:
                                    return None
                                try:
                                    return datetime.fromisoformat(ts.replace('Z', '+00:00')).isoformat()
                                except:
                                    return None
                            
                            event_data = {
                                "user_id": user_id,
                                "calendar_id": calendar_id,
                                "event_id": event_id,
                                "summary": event.get('summary', ''),
                                "description": event.get('description'),
                                "location": event.get('location'),
                                "start_time": parse_timestamp(start_time),
                                "end_time": parse_timestamp(end_time),
                                "status": event.get('status'),
                                "html_link": event.get('htmlLink'),
                                "last_synced_at": datetime.utcnow().isoformat()
                            }
                            
                            try:
                                existing_event = self.supabase.table('google_calendar_events').select('id').eq('user_id', user_id).eq('calendar_id', calendar_id).eq('event_id', event_id).single().execute()
                                if existing_event.data:
                                    self.supabase.table('google_calendar_events').update(event_data).eq('id', existing_event.data['id']).execute()
                                else:
                                    self.supabase.table('google_calendar_events').insert(event_data).execute()
                            except (httpx.ConnectError, httpx.ConnectTimeout, Exception) as e:
                                print(f"[AutoSync] ⚠️ Network error saving event {event_id}: {type(e).__name__}")
                                continue
                except Exception as e:
                    print(f"[AutoSync] Error fetching events for calendar {calendar_id}: {e}")

# Global scheduler instance
_scheduler_instance: AutoSyncScheduler = None

def get_auto_sync_scheduler() -> AutoSyncScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AutoSyncScheduler()
    return _scheduler_instance


