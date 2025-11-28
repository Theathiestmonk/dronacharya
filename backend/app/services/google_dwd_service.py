"""
Google Domain-Wide Delegation (DWD) Service
Allows service account to impersonate users and access their Google Classroom/Calendar data
"""
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Dict, List, Optional
from datetime import datetime, timezone

class GoogleDWDService:
    """Service for Google Domain-Wide Delegation (DWD) authentication"""
    
    def __init__(self):
        # Get service account path from env var or use default
        self.service_account_path = os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS',
            os.path.join(os.path.dirname(__file__), '../../service-account-key.json')
        )
        self.workspace_domain = os.getenv('GOOGLE_WORKSPACE_DOMAIN', 'atsnai.com')
        
        # Note: For Domain-Wide Delegation, scopes are configured in Google Workspace Admin Console
        # Do NOT pass scopes when creating credentials - they are enforced by Admin Console authorization
        self._base_credentials = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load service account credentials for Domain-Wide Delegation"""
        try:
            # Resolve relative path
            if not os.path.isabs(self.service_account_path):
                # Make path relative to project root
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                self.service_account_path = os.path.join(base_dir, self.service_account_path.replace('backend/', ''))
            
            if os.path.exists(self.service_account_path):
                # For DWD, create credentials WITHOUT scopes
                # Scopes are authorized in Google Workspace Admin Console, not in code
                self._base_credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path
                )
                print(f"✅ DWD: Service account credentials loaded from {self.service_account_path}")
            else:
                print(f"⚠️ DWD: Service account file not found at {self.service_account_path}")
        except Exception as e:
            print(f"❌ DWD: Failed to load credentials: {str(e)}")
            self._base_credentials = None
    
    def _get_delegated_credentials(self, user_email: str):
        """Get delegated credentials for a specific user"""
        if not self._base_credentials:
            raise Exception("Service account credentials not loaded. Check GOOGLE_APPLICATION_CREDENTIALS path.")
        
        # Verify email is in workspace domain
        if not user_email.endswith(f"@{self.workspace_domain}"):
            raise Exception(f"User email {user_email} is not in workspace domain {self.workspace_domain}")
        
        # Create delegated credentials (impersonate user)
        delegated_credentials = self._base_credentials.with_subject(user_email)
        return delegated_credentials
    
    def get_classroom_service(self, user_email: str):
        """Get Google Classroom service for a specific user"""
        credentials = self._get_delegated_credentials(user_email)
        return build('classroom', 'v1', credentials=credentials)
    
    def get_calendar_service(self, user_email: str):
        """Get Google Calendar service for a specific user"""
        credentials = self._get_delegated_credentials(user_email)
        return build('calendar', 'v3', credentials=credentials)
    
    def fetch_user_courses(self, user_email: str) -> List[Dict]:
        """Fetch all courses for a user"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().list().execute()
            courses = results.get('courses', [])
            print(f"✅ DWD: Fetched {len(courses)} courses for {user_email}")
            return courses
        except Exception as e:
            print(f"❌ DWD: Failed to fetch courses for {user_email}: {str(e)}")
            raise
    
    def fetch_course_teachers(self, user_email: str, course_id: str) -> List[Dict]:
        """Fetch teachers for a specific course"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().teachers().list(courseId=course_id).execute()
            teachers = results.get('teachers', [])
            return teachers
        except Exception as e:
            print(f"❌ DWD: Failed to fetch teachers for course {course_id}: {str(e)}")
            return []
    
    def fetch_course_students(self, user_email: str, course_id: str) -> List[Dict]:
        """Fetch students for a specific course"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().students().list(courseId=course_id).execute()
            students = results.get('students', [])
            return students
        except Exception as e:
            print(f"❌ DWD: Failed to fetch students for course {course_id}: {str(e)}")
            return []
    
    def fetch_course_coursework(self, user_email: str, course_id: str) -> List[Dict]:
        """Fetch coursework for a specific course"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().courseWork().list(courseId=course_id).execute()
            coursework = results.get('courseWork', [])
            return coursework
        except Exception as e:
            print(f"❌ DWD: Failed to fetch coursework for course {course_id}: {str(e)}")
            return []
    
    def fetch_course_submissions(self, user_email: str, course_id: str, coursework_id: str) -> List[Dict]:
        """Fetch student submissions for a specific coursework"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().courseWork().studentSubmissions().list(
                courseId=course_id,
                courseWorkId=coursework_id
            ).execute()
            submissions = results.get('studentSubmissions', [])
            return submissions
        except Exception as e:
            print(f"❌ DWD: Failed to fetch submissions for coursework {coursework_id}: {str(e)}")
            return []
    
    def fetch_course_announcements(self, user_email: str, course_id: str) -> List[Dict]:
        """Fetch announcements for a specific course"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().announcements().list(courseId=course_id).execute()
            announcements = results.get('announcements', [])
            return announcements
        except Exception as e:
            print(f"❌ DWD: Failed to fetch announcements for course {course_id}: {str(e)}")
            return []
    
    def fetch_user_calendars(self, user_email: str) -> List[Dict]:
        """Fetch all calendars for a user"""
        try:
            calendar_service = self.get_calendar_service(user_email)
            results = calendar_service.calendarList().list().execute()
            calendars = results.get('items', [])
            return calendars
        except Exception as e:
            print(f"❌ DWD: Failed to fetch calendars for {user_email}: {str(e)}")
            return []
    
    def fetch_calendar_events(self, user_email: str, calendar_id: str = 'primary', 
                             time_min: Optional[str] = None) -> List[Dict]:
        """Fetch events from a calendar"""
        try:
            calendar_service = self.get_calendar_service(user_email)
            
            params = {
                'calendarId': calendar_id,
                'maxResults': 2500,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if time_min:
                params['timeMin'] = time_min
            else:
                # Default to current time
                params['timeMin'] = datetime.now(timezone.utc).isoformat()
            
            results = calendar_service.events().list(**params).execute()
            events = results.get('items', [])
            return events
        except Exception as e:
            print(f"❌ DWD: Failed to fetch events for calendar {calendar_id}: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """Check if DWD service is available (credentials loaded)"""
        return self._base_credentials is not None

# Global instance
_dwd_service = None

def get_dwd_service() -> Optional[GoogleDWDService]:
    """Get global DWD service instance"""
    global _dwd_service
    if _dwd_service is None:
        _dwd_service = GoogleDWDService()
    return _dwd_service if _dwd_service.is_available() else None



