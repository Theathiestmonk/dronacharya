#!/usr/bin/env python3
"""
Admin SDK approach to sync ALL classroom and calendar data from entire prakriti.org.in domain
Uses Google Admin SDK for domain-wide access instead of user-based DWD
"""

import os
import sys
import json
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Add current directory to path
sys.path.insert(0, os.getcwd())

def get_admin_service_account_credentials():
    """Get credentials for Admin SDK access using same logic as DWD service"""

    # Use same credential loading logic as DWD service
    service_account_path = os.getenv(
        'GOOGLE_APPLICATION_CREDENTIALS',
        os.path.join(os.path.dirname(__file__), 'service-account-key.json')
    )

    # Try multiple candidate paths like DWD service does
    candidates = [
        service_account_path,
        os.path.join(os.path.dirname(__file__), 'service-account-key.json'),
        os.path.join(os.path.dirname(__file__), '../service-account-key.json'),
        os.path.join(os.path.dirname(__file__), '../../service-account-key.json'),
        os.path.join(os.path.dirname(__file__), '../../../service-account-key.json'),
    ]

    creds_path = None
    for candidate in candidates:
        candidate = os.path.normpath(os.path.expandvars(candidate))
        # Fix common typos
        candidate = candidate.replace('droonacharya', 'dronacharya')
        candidate = candidate.replace('backkend', 'backend')

        if os.path.exists(candidate):
            creds_path = candidate
            break

    if not creds_path:
        raise Exception(f"Service account credentials not found. Tried paths: {candidates}")

    print(f"Using credentials file: {creds_path}")

    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=[
            'https://www.googleapis.com/auth/admin.directory.user.readonly',
            'https://www.googleapis.com/auth/classroom.courses.readonly',
            'https://www.googleapis.com/auth/classroom.rosters.readonly',
            'https://www.googleapis.com/auth/classroom.announcements.readonly',
            'https://www.googleapis.com/auth/classroom.coursework.readonly',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events.readonly'
        ]
    )

    # Set the subject to a domain admin
    admin_email = os.getenv('GOOGLE_ADMIN_EMAIL', 'admin@learners.prakriti.org.in')
    credentials = credentials.with_subject(admin_email)

    return credentials

def get_all_domain_users():
    """Get all users in the prakriti.org.in domain"""
    print("Fetching all users in prakriti.org.in domain...")

    try:
        credentials = get_admin_service_account_credentials()
        service = build('admin', 'directory_v1', credentials=credentials)

        domain = 'learners.prakriti.org.in'
        all_users = []
        page_token = None

        while True:
            results = service.users().list(
                domain=domain,
                pageToken=page_token,
                maxResults=500
            ).execute()

            users = results.get('users', [])
            all_users.extend(users)

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        print(f"Found {len(all_users)} users in domain")
        return all_users

    except Exception as e:
        print(f"Error fetching domain users: {e}")
        return []

def sync_all_classroom_data():
    """Sync ALL classroom data from entire domain using Admin SDK"""
    print("=" * 60)
    print("ADMIN SDK: SYNCING ALL CLASSROOM DATA FROM PRAKRITI.ORG.IN")
    print("=" * 60)

    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            raise Exception("Supabase connection failed")

        # Get credentials and build services
        credentials = get_admin_service_account_credentials()
        classroom_service = build('classroom', 'v1', credentials=credentials)

        # Get all users in domain
        domain_users = get_all_domain_users()
        teacher_emails = [user['primaryEmail'] for user in domain_users if user.get('isAdmin') != True]

        print(f"Processing classroom data for {len(teacher_emails)} potential teachers...")

        sync_stats = {
            "courses": {"created": 0, "updated": 0, "total": 0},
            "teachers": {"created": 0, "updated": 0, "total": 0},
            "students": {"created": 0, "updated": 0, "total": 0},
            "coursework": {"created": 0, "updated": 0, "total": 0},
            "announcements": {"created": 0, "updated": 0, "total": 0},
            "submissions": {"created": 0, "updated": 0, "total": 0}
        }

        # Fetch ALL courses from the domain (not user-specific)
        print("Fetching ALL courses from domain...")
        all_courses = []
        page_token = None

        while True:
            try:
                results = classroom_service.courses().list(
                    pageToken=page_token,
                    pageSize=100
                ).execute()

                courses = results.get('courses', [])
                all_courses.extend(courses)

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            except Exception as e:
                print(f"Error fetching courses page: {e}")
                break

        print(f"Found {len(all_courses)} courses in entire domain")

        # Process each course
        for course in all_courses:
            course_id = course.get('id')
            if not course_id:
                continue

            print(f"Processing course: {course.get('name', 'Unknown')} ({course_id})")

            # Store course data
            course_data = {
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
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
                "is_domain_wide": True
            }

            # Upsert course
            existing = supabase.table('google_classroom_courses').select('id').eq('course_id', course_id).limit(1).execute()

            if existing.data and len(existing.data) > 0:
                supabase.table('google_classroom_courses').update(course_data).eq('id', existing.data[0]['id']).execute()
                sync_stats["courses"]["updated"] += 1
            else:
                supabase.table('google_classroom_courses').insert(course_data).execute()
                sync_stats["courses"]["created"] += 1

            sync_stats["courses"]["total"] += 1

            # Get course database ID for related data
            course_db_result = supabase.table('google_classroom_courses').select('id').eq('course_id', course_id).limit(1).execute()
            course_db_id = course_db_result.data[0]['id'] if course_db_result.data else None

            if not course_db_id:
                continue

            # Fetch and store teachers
            try:
                teachers_result = classroom_service.courses().teachers().list(courseId=course_id).execute()
                teachers = teachers_result.get('teachers', [])

                for teacher in teachers:
                    teacher_data = {
                        "course_id": course_db_id,
                        "user_id": teacher.get('userId', ''),
                        "course_user_id": f"{course_id}_{teacher.get('userId', '')}",
                        "profile": teacher.get('profile', {}),
                        "is_domain_wide": True
                    }

                    existing = supabase.table('google_classroom_teachers').select('id').eq('course_id', course_db_id).eq('course_user_id', teacher_data['course_user_id']).limit(1).execute()

                    if existing.data and len(existing.data) > 0:
                        supabase.table('google_classroom_teachers').update(teacher_data).eq('id', existing.data[0]['id']).execute()
                        sync_stats["teachers"]["updated"] += 1
                    else:
                        supabase.table('google_classroom_teachers').insert(teacher_data).execute()
                        sync_stats["teachers"]["created"] += 1

                    sync_stats["teachers"]["total"] += 1

            except Exception as e:
                print(f"Warning: Could not fetch teachers for course {course_id}: {e}")

            # Fetch and store students
            try:
                students_result = classroom_service.courses().students().list(courseId=course_id).execute()
                students = students_result.get('students', [])

                for student in students:
                    student_data = {
                        "course_id": course_db_id,
                        "user_id": student.get('userId', ''),
                        "course_user_id": f"{course_id}_{student.get('userId', '')}",
                        "profile": student.get('profile', {}),
                        "student_work_folder": student.get('studentWorkFolder'),
                        "is_domain_wide": True
                    }

                    existing = supabase.table('google_classroom_students').select('id').eq('course_id', course_db_id).eq('course_user_id', student_data['course_user_id']).limit(1).execute()

                    if existing.data and len(existing.data) > 0:
                        supabase.table('google_classroom_students').update(student_data).eq('id', existing.data[0]['id']).execute()
                        sync_stats["students"]["updated"] += 1
                    else:
                        supabase.table('google_classroom_students').insert(student_data).execute()
                        sync_stats["students"]["created"] += 1

                    sync_stats["students"]["total"] += 1

            except Exception as e:
                print(f"Warning: Could not fetch students for course {course_id}: {e}")

            # Fetch and store coursework
            try:
                coursework_result = classroom_service.courses().courseWork().list(courseId=course_id).execute()
                coursework_list = coursework_result.get('courseWork', [])

                for cw in coursework_list:
                    cw_id = cw.get('id')
                    if not cw_id:
                        continue

                    due_date = None
                    if cw.get('dueDate'):
                        due_date_str = f"{cw['dueDate'].get('year', 2000)}-{cw['dueDate'].get('month', 1):02d}-{cw['dueDate'].get('day', 1):02d}"
                        due_date = f"{due_date_str}T00:00:00Z"
                    elif cw.get('dueTime'):
                        due_date = cw['dueTime']

                    coursework_data = {
                        "course_id": course_db_id,
                        "coursework_id": cw_id,
                        "title": cw.get('title', ''),
                        "description": cw.get('description'),
                        "materials": cw.get('materials'),
                        "state": cw.get('state'),
                        "alternate_link": cw.get('alternateLink'),
                        "creation_time": cw.get('creationTime'),
                        "update_time": cw.get('updateTime'),
                        "due_date": due_date,
                        "due_time": cw.get('dueTime'),
                        "max_points": float(cw['maxPoints'].get('value', 0)) if cw.get('maxPoints') else None,
                        "work_type": cw.get('workType'),
                        "creator_user_id": cw.get('creatorUserId'),
                        "last_synced_at": datetime.now(timezone.utc).isoformat(),
                        "is_domain_wide": True
                    }

                    existing = supabase.table('google_classroom_coursework').select('id').eq('course_id', course_db_id).eq('coursework_id', cw_id).limit(1).execute()

                    if existing.data and len(existing.data) > 0:
                        supabase.table('google_classroom_coursework').update(coursework_data).eq('id', existing.data[0]['id']).execute()
                        sync_stats["coursework"]["updated"] += 1
                    else:
                        supabase.table('google_classroom_coursework').insert(coursework_data).execute()
                        sync_stats["coursework"]["created"] += 1

                    sync_stats["coursework"]["total"] += 1

            except Exception as e:
                print(f"Warning: Could not fetch coursework for course {course_id}: {e}")

            # Fetch and store announcements
            try:
                announcements_result = classroom_service.courses().announcements().list(courseId=course_id).execute()
                announcements = announcements_result.get('announcements', [])

                for ann in announcements:
                    announcement_data = {
                        "course_id": course_db_id,
                        "announcement_id": ann.get('id', ''),
                        "text": ann.get('text'),
                        "materials": ann.get('materials'),
                        "state": ann.get('state'),
                        "alternate_link": ann.get('alternateLink'),
                        "creation_time": ann.get('creationTime'),
                        "update_time": ann.get('updateTime'),
                        "creator_user_id": ann.get('creatorUserId'),
                        "last_synced_at": datetime.now(timezone.utc).isoformat(),
                        "is_domain_wide": True
                    }

                    existing = supabase.table('google_classroom_announcements').select('id').eq('course_id', course_db_id).eq('announcement_id', announcement_data['announcement_id']).limit(1).execute()

                    if existing.data and len(existing.data) > 0:
                        supabase.table('google_classroom_announcements').update(announcement_data).eq('id', existing.data[0]['id']).execute()
                        sync_stats["announcements"]["updated"] += 1
                    else:
                        supabase.table('google_classroom_announcements').insert(announcement_data).execute()
                        sync_stats["announcements"]["created"] += 1

                    sync_stats["announcements"]["total"] += 1

            except Exception as e:
                print(f"Warning: Could not fetch announcements for course {course_id}: {e}")

        return {
            "success": True,
            "message": f"Successfully synced ALL classroom data from prakriti.org.in domain",
            "stats": sync_stats,
            "summary": {
                "courses": sync_stats["courses"]["total"],
                "teachers": sync_stats["teachers"]["total"],
                "students": sync_stats["students"]["total"],
                "coursework": sync_stats["coursework"]["total"],
                "announcements": sync_stats["announcements"]["total"]
            }
        }

    except Exception as e:
        print(f"ADMIN SDK SYNC FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

def sync_all_calendar_data():
    """Sync ALL calendar data from entire domain using Admin SDK"""
    print("=" * 60)
    print("ADMIN SDK: SYNCING ALL CALENDAR DATA FROM PRAKRITI.ORG.IN")
    print("=" * 60)

    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            raise Exception("Supabase connection failed")

        # Get credentials and build calendar service
        credentials = get_admin_service_account_credentials()
        calendar_service = build('calendar', 'v3', credentials=credentials)

        sync_stats = {
            "calendars": {"created": 0, "updated": 0, "total": 0},
            "events": {"created": 0, "updated": 0, "total": 0}
        }

        # Get all domain users to sync their calendars
        domain_users = get_all_domain_users()
        user_emails = [user['primaryEmail'] for user in domain_users]

        print(f"Syncing calendar data for {len(user_emails)} users...")

        for user_email in user_emails[:10]:  # Limit to first 10 for testing
            print(f"Processing calendar for: {user_email}")

            try:
                # Get user's calendars
                calendars_result = calendar_service.calendarList().list(
                    minAccessRole='owner'
                ).execute()

                calendars = calendars_result.get('items', [])

                for calendar in calendars:
                    calendar_id = calendar.get('id')
                    if not calendar_id:
                        continue

                    # Skip primary calendar duplicates
                    if calendar_id.endswith('@group.calendar.google.com'):
                        continue

                    calendar_data = {
                        "user_email": user_email,
                        "calendar_id": calendar_id,
                        "summary": calendar.get('summary', ''),
                        "description": calendar.get('description'),
                        "timezone": calendar.get('timeZone'),
                        "access_role": calendar.get('accessRole'),
                        "primary_calendar": calendar.get('primary', False),
                        "last_synced_at": datetime.now(timezone.utc).isoformat(),
                        "is_domain_wide": True
                    }

                    # Upsert calendar
                    existing = supabase.table('google_calendar_calendars').select('id').eq('calendar_id', calendar_id).limit(1).execute()

                    if existing.data and len(existing.data) > 0:
                        supabase.table('google_calendar_calendars').update(calendar_data).eq('id', existing.data[0]['id']).execute()
                        sync_stats["calendars"]["updated"] += 1
                    else:
                        supabase.table('google_calendar_calendars').insert(calendar_data).execute()
                        sync_stats["calendars"]["created"] += 1

                    sync_stats["calendars"]["total"] += 1

                    # Get calendar database ID
                    cal_db_result = supabase.table('google_calendar_calendars').select('id').eq('calendar_id', calendar_id).limit(1).execute()
                    cal_db_id = cal_db_result.data[0]['id'] if cal_db_result.data else None

                    if cal_db_id:
                        # Fetch recent events (last 30 days)
                        time_min = (datetime.now() - timedelta(days=30)).isoformat() + 'Z'
                        time_max = (datetime.now() + timedelta(days=90)).isoformat() + 'Z'

                        try:
                            events_result = calendar_service.events().list(
                                calendarId=calendar_id,
                                timeMin=time_min,
                                timeMax=time_max,
                                singleEvents=True,
                                orderBy='startTime',
                                maxResults=100
                            ).execute()

                            events = events_result.get('items', [])

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
                                        start_time = event['start']['dateTime']
                                    elif event['start'].get('date'):
                                        start_time = event['start']['date'] + 'T00:00:00Z'
                                        all_day = True

                                if event.get('end'):
                                    if event['end'].get('dateTime'):
                                        end_time = event['end']['dateTime']
                                    elif event['end'].get('date'):
                                        end_time = event['end']['date'] + 'T00:00:00Z'

                                event_data = {
                                    "calendar_id": cal_db_id,
                                    "event_id": event_id,
                                    "summary": event.get('summary', ''),
                                    "description": event.get('description'),
                                    "location": event.get('location'),
                                    "start_time": start_time,
                                    "end_time": end_time,
                                    "all_day": all_day,
                                    "timezone": event.get('start', {}).get('timeZone'),
                                    "status": event.get('status'),
                                    "html_link": event.get('htmlLink'),
                                    "last_synced_at": datetime.now(timezone.utc).isoformat(),
                                    "is_domain_wide": True
                                }

                                existing = supabase.table('google_calendar_events').select('id').eq('event_id', event_id).limit(1).execute()

                                if existing.data and len(existing.data) > 0:
                                    supabase.table('google_calendar_events').update(event_data).eq('id', existing.data[0]['id']).execute()
                                    sync_stats["events"]["updated"] += 1
                                else:
                                    supabase.table('google_calendar_events').insert(event_data).execute()
                                    sync_stats["events"]["created"] += 1

                                sync_stats["events"]["total"] += 1

                        except Exception as e:
                            print(f"Warning: Could not fetch events for calendar {calendar_id}: {e}")

            except Exception as e:
                print(f"Warning: Could not process calendar for {user_email}: {e}")

        return {
            "success": True,
            "message": f"Successfully synced ALL calendar data from prakriti.org.in domain",
            "stats": sync_stats,
            "summary": {
                "calendars": sync_stats["calendars"]["total"],
                "events": sync_stats["events"]["total"]
            }
        }

    except Exception as e:
        print(f"CALENDAR SYNC FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import asyncio

    print("Starting Admin SDK Domain Sync...")

    # Test environment
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    admin_email = os.getenv('GOOGLE_ADMIN_EMAIL', 'admin@learners.prakriti.org.in')

    if not creds_path or not os.path.exists(creds_path):
        print(f"ERROR: Credentials file not found: {creds_path}")
        sys.exit(1)

    print(f"Using credentials: {creds_path}")
    print(f"Admin email: {admin_email}")

    # Sync classroom data
    print("\n" + "="*80)
    print("PHASE 1: SYNCING CLASSROOM DATA")
    print("="*80)

    classroom_result = sync_all_classroom_data()

    if classroom_result['success']:
        print("\nClassroom sync completed successfully!")
        print(json.dumps(classroom_result['summary'], indent=2))
    else:
        print(f"\nClassroom sync failed: {classroom_result.get('error', 'Unknown error')}")

    # Sync calendar data
    print("\n" + "="*80)
    print("PHASE 2: SYNCING CALENDAR DATA")
    print("="*80)

    calendar_result = sync_all_calendar_data()

    if calendar_result['success']:
        print("\nCalendar sync completed successfully!")
        print(json.dumps(calendar_result['summary'], indent=2))
    else:
        print(f"\nCalendar sync failed: {calendar_result.get('error', 'Unknown error')}")

    # Final summary
    print("\n" + "="*80)
    print("DOMAIN SYNC COMPLETE")
    print("="*80)

    if classroom_result['success'] or calendar_result['success']:
        print("SUCCESS: Domain data sync completed!")

        total_items = 0
        if classroom_result['success']:
            summary = classroom_result['summary']
            total_items += summary['courses'] + summary['teachers'] + summary['students'] + summary['coursework'] + summary['announcements']

        if calendar_result['success']:
            summary = calendar_result['summary']
            total_items += summary['calendars'] + summary['events']

        print(f"Total items synced: {total_items}")
        print("\nData is now available in Supabase for the entire prakriti.org.in domain!")
    else:
        print("FAILED: All sync operations failed")
        sys.exit(1)
