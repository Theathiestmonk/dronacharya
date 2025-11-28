"""
Supabase-based admin service for Google integrations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
from supabase_config import get_supabase_client

class SupabaseAdminService:
    """Service for managing admin data in Supabase"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def get_admin(self, email: str) -> Optional[Dict[str, Any]]:
        """Get admin by email from user_profiles"""
        try:
            # Check for admin by email with admin_privileges=true
            result = self.supabase.table('user_profiles').select('*').eq('email', email).eq('admin_privileges', True).eq('is_active', True).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting admin: {e}")
            return None
    
    def get_user_profile_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user profile by email (any user, not just admin)"""
        try:
            result = self.supabase.table('user_profiles').select('*').eq('email', email).eq('is_active', True).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return None
    
    def get_first_admin(self) -> Optional[Dict[str, Any]]:
        """Get first available admin from user_profiles"""
        try:
            result = self.supabase.table('user_profiles').select('*').eq('admin_privileges', True).eq('is_active', True).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting first admin: {e}")
            return None
    
    def create_admin(self, email: str, name: str, role: str = 'admin') -> Optional[Dict[str, Any]]:
        """Create new admin profile"""
        try:
            # For user_profiles, we need to first ensure user exists in auth.users
            # Or skip this and let the user create their profile through normal flow
            print(f"Cannot create admin profile without user_id. Please create through user registration or update existing profile.")
            return None
        except Exception as e:
            print(f"Error creating admin: {e}")
            return None
    
    def update_admin_integrations(self, admin_id: int, classroom_enabled: bool = None, calendar_enabled: bool = None) -> bool:
        """Update admin integration flags - Not needed with google_integrations table"""
        try:
            # Integration status is now determined by google_integrations table
            # No need to update flags in user_profiles
            return True
        except Exception as e:
            print(f"Error updating admin integrations: {e}")
            return False
    
    def create_google_integration(self, admin_id: int, service_type: str, access_token: str, 
                                refresh_token: str, token_expires_at: datetime, scope: str) -> Optional[Dict[str, Any]]:
        """Create Google integration record"""
        try:
            integration_data = {
                'admin_id': admin_id,
                'service_type': service_type,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_expires_at': token_expires_at.isoformat(),
                'scope': scope,
                'is_active': True
            }
            result = self.supabase.table('google_integrations').insert(integration_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating Google integration: {e}")
            return None
    
    def get_google_integrations(self, admin_id: int) -> List[Dict[str, Any]]:
        """Get all Google integrations for admin"""
        try:
            result = self.supabase.table('google_integrations').select('*').eq('admin_id', admin_id).eq('is_active', True).execute()
            return result.data
        except Exception as e:
            print(f"Error getting Google integrations: {e}")
            return []
    
    def get_integration_status(self, admin_id: int) -> Dict[str, Any]:
        """Get integration status for admin from google_integrations table"""
        try:
            integrations = self.get_google_integrations(admin_id)
            
            # Check which services are enabled based on active integrations
            classroom_enabled = any(i['service_type'] == 'classroom' for i in integrations)
            calendar_enabled = any(i['service_type'] == 'calendar' for i in integrations)
            
            return {
                'classroom_enabled': classroom_enabled,
                'calendar_enabled': calendar_enabled,
                'integrations': [
                    {
                        'id': integration['id'],
                        'service_type': integration['service_type'],
                        'is_active': integration['is_active'],
                        'created_at': integration['created_at'],
                        'token_expires_at': integration['token_expires_at']
                    }
                    for integration in integrations
                ]
            }
        except Exception as e:
            print(f"Error getting integration status: {e}")
            return {'classroom_enabled': False, 'calendar_enabled': False, 'integrations': []}
    
    def sync_classroom_data(self, admin_id: Any, classroom_data: List[Dict[str, Any]]) -> bool:
        """Sync classroom data to Supabase"""
        try:
            # Clear existing data - handle both UUID and integer admin_id
            self.supabase.table('classroom_data').delete().eq('admin_id', admin_id).execute()
            
            # Insert new data
            if classroom_data:
                self.supabase.table('classroom_data').insert(classroom_data).execute()
            return True
        except Exception as e:
            print(f"Error syncing classroom data: {e}")
            return False
    
    def sync_calendar_data(self, admin_id: Any, calendar_data: List[Dict[str, Any]]) -> bool:
        """Sync calendar data to Supabase"""
        try:
            # Clear existing data - handle both UUID and integer admin_id
            self.supabase.table('calendar_data').delete().eq('admin_id', admin_id).execute()
            
            # Insert new data
            if calendar_data:
                self.supabase.table('calendar_data').insert(calendar_data).execute()
            return True
        except Exception as e:
            print(f"Error syncing calendar data: {e}")
            return False
    
    def get_classroom_data(self, admin_id: Any, show_all_users: bool = True) -> List[Dict[str, Any]]:
        """Get classroom data for admin from normalized tables
        
        Args:
            admin_id: The admin's user_profiles.id
            show_all_users: If True (default), show courses from all users. If False, show only admin's courses.
        """
        try:
            # Get user_id from user_profiles (admin_id is user_profiles.id, we need auth.users.id)
            profile = self.supabase.table('user_profiles').select('user_id, admin_privileges').eq('id', admin_id).single().execute()
            user_id = profile.data.get('user_id') if profile.data else None
            is_admin = profile.data.get('admin_privileges', False) if profile.data else False
            
            if not user_id:
                print(f"No user_id found for admin_id {admin_id}")
                return []
            
            # For admins, show all courses from all users (if show_all_users is True)
            # Otherwise, show only courses for this specific user
            if is_admin and show_all_users:
                # Get all courses from all users (admin view)
                # Get MAX last_synced_at across all courses
                max_sync_result = self.supabase.table('google_classroom_courses').select('last_synced_at').order('last_synced_at', desc=True).limit(1).execute()
                most_recent_sync = max_sync_result.data[0].get('last_synced_at') if max_sync_result.data and len(max_sync_result.data) > 0 else None
                
                # Get all courses (limit to 500 for performance)
                result = self.supabase.table('google_classroom_courses').select('*').order('last_synced_at', desc=True).limit(500).execute()
            else:
                # Get only courses for this specific user
                max_sync_result = self.supabase.table('google_classroom_courses').select('last_synced_at').eq('user_id', user_id).order('last_synced_at', desc=True).limit(1).execute()
                most_recent_sync = max_sync_result.data[0].get('last_synced_at') if max_sync_result.data and len(max_sync_result.data) > 0 else None
                result = self.supabase.table('google_classroom_courses').select('*').eq('user_id', user_id).limit(100).execute()
            
            # Transform to match expected format
            courses = []
            for course in result.data:
                courses.append({
                    'course_id': course.get('course_id', ''),
                    'course_name': course.get('name', ''),
                    'course_description': course.get('description', ''),
                    'course_room': course.get('room', ''),
                    'course_section': course.get('section', ''),
                    'course_state': course.get('course_state', ''),
                    'teacher_email': None,  # Will need to fetch from teachers table if needed
                    'student_count': 0,  # Will need to count from students table if needed
                    'last_synced': course.get('last_synced_at', '') or most_recent_sync or ''
                })
            
            print(f"🔍 [get_classroom_data] Found {len(courses)} courses (show_all_users={show_all_users}, is_admin={is_admin})")
            return courses
        except Exception as e:
            print(f"Error getting classroom data: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_calendar_data(self, admin_id: Any) -> List[Dict[str, Any]]:
        """Get calendar data for admin from normalized tables"""
        try:
            # Get user_id from user_profiles (admin_id is user_profiles.id, we need auth.users.id)
            profile = self.supabase.table('user_profiles').select('user_id').eq('id', admin_id).single().execute()
            user_id = profile.data.get('user_id') if profile.data else None
            
            if not user_id:
                print(f"No user_id found for admin_id {admin_id}")
                return []
            
            # Query from normalized google_calendar_events table
            # First, get the MAX last_synced_at for calendar sync timestamp from ALL events (not just future)
            # This ensures we show the sync status even if there are no upcoming events
            max_sync_result = self.supabase.table('google_calendar_events').select('last_synced_at').eq('user_id', user_id).order('last_synced_at', desc=True).limit(1).execute()
            
            most_recent_sync = None
            if max_sync_result.data and len(max_sync_result.data) > 0:
                most_recent_sync = max_sync_result.data[0].get('last_synced_at')
            
            # Also check google_calendar_calendars table for sync timestamp as fallback
            if not most_recent_sync:
                cal_sync_result = self.supabase.table('google_calendar_calendars').select('last_synced_at').eq('user_id', user_id).order('last_synced_at', desc=True).limit(1).execute()
                if cal_sync_result.data and len(cal_sync_result.data) > 0:
                    most_recent_sync = cal_sync_result.data[0].get('last_synced_at')
            
            # Get events from the next 90 days, ordered by start_time
            from datetime import datetime, timedelta
            time_min = datetime.utcnow().isoformat()
            time_max = (datetime.utcnow() + timedelta(days=90)).isoformat()
            
            result = self.supabase.table('google_calendar_events').select('*').eq('user_id', user_id).gte('start_time', time_min).lte('start_time', time_max).order('start_time', desc=False).limit(100).execute()
            
            # Transform to match expected format
            events = []
            for event in result.data:
                events.append({
                    'event_id': event.get('event_id', ''),
                    'event_title': event.get('summary', ''),
                    'event_description': event.get('description', ''),
                    'event_start': event.get('start_time', ''),
                    'event_end': event.get('end_time', ''),
                    'event_location': event.get('location', ''),
                    'event_status': event.get('status', ''),
                    'last_synced': most_recent_sync or event.get('last_synced_at', '')
                })
            
            # If no events but we have a sync timestamp, add a dummy entry to show sync status
            if len(events) == 0 and most_recent_sync:
                events.append({
                    'event_id': 'sync_status',
                    'event_title': 'Calendar Sync Status',
                    'event_description': '',
                    'event_start': '',
                    'event_end': '',
                    'event_location': '',
                    'event_status': '',
                    'last_synced': most_recent_sync
                })
            
            print(f"🔍 [get_calendar_data] Found {len(events)} events, most recent sync: {most_recent_sync}")
            return events
        except Exception as e:
            print(f"Error getting calendar data: {e}")
            return []






