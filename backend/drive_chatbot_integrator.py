#!/usr/bin/env python3

import sys
import os
import requests
import json
from typing import Optional, Dict, Any, List

# Add backend to path for imports
sys.path.append(os.path.dirname(__file__))

from grade_exam_detector import GradeExamDetector
from supabase_config import get_supabase_client
from token_refresh_service import TokenRefreshService

class DriveChatbotIntegrator:
    """Integrates Google Drive data with chatbot responses"""

    def __init__(self):
        self.detector = GradeExamDetector()
        self.supabase = get_supabase_client()

    def get_active_drive_token(self) -> Optional[Dict[str, Any]]:
        """Get the active Google Drive token, refreshing if necessary"""
        try:
            print("[DriveChatbot] Retrieving active token from database...")
            result = self.supabase.table('gcdr').select('*').eq('is_active', True).order('created_at', desc=True).limit(1).execute()

            if result.data:
                token = result.data[0]
                print(f"[DriveChatbot] Found token for user: {token['user_email']}")
                print(f"[DriveChatbot] Token expires: {token.get('token_expires_at', 'Unknown')}")

                # Check if token needs refresh
                refresh_service = TokenRefreshService()
                valid_token = refresh_service.ensure_valid_token(token)

                if valid_token:
                    print("[DriveChatbot] Token is valid (refreshed if needed)")
                    return valid_token
                else:
                    print("[DriveChatbot] Token refresh failed")
                    return None
            else:
                print("[DriveChatbot] No active tokens found")
                return None
        except Exception as e:
            print(f"[DriveChatbot] Error getting token: {e}")
            return None

    def find_grade_sheet(self, grade: str, token: Dict[str, Any]) -> Optional[str]:
        """Find the Google Sheet file ID for a specific grade"""
        try:
            access_token = token['access_token']
            headers = {'Authorization': f'Bearer {access_token}'}

            # First, let's see what files are accessible
            print(f"[DriveChatbot] Checking accessible files for grade {grade}...")
            print(f"[DriveChatbot] Using token: {access_token[:20]}...")

            # Search for all Google Sheets first
            search_url = "https://www.googleapis.com/drive/v3/files"
            search_params = {
                'q': "mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
                'fields': 'files(id,name)',
                'pageSize': 20
            }

            print(f"[DriveChatbot] Making request to: {search_url}")
            response = requests.get(search_url, headers=headers, params=search_params)
            print(f"[DriveChatbot] Response status: {response.status_code}")

            if response.status_code == 200:
                all_sheets = response.json().get('files', [])
                print(f"[DriveChatbot] Found {len(all_sheets)} total Google Sheets:")
                for sheet in all_sheets:
                    print(f"  - {sheet['name']} (ID: {sheet['id']})")

                # Now search for grade-specific sheet
                grade_sheets = [s for s in all_sheets if f'G{grade}- InfoSheet' in s['name']]
                if grade_sheets:
                    print(f"[DriveChatbot] Found matching sheet: {grade_sheets[0]['name']}")
                    return grade_sheets[0]['id']

                print(f"[DriveChatbot] No sheet found for grade {grade}")
                return None
            else:
                print(f"[DriveChatbot] Error listing files: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"[DriveChatbot] Error finding grade sheet: {e}")
            return None

    def extract_sheet_data(self, file_id: str, sheet_name: str, token: Dict[str, Any]) -> Optional[List[List[str]]]:
        """Extract data from a specific sheet tab"""
        try:
            access_token = token['access_token']
            headers = {'Authorization': f'Bearer {access_token}'}

            # Get data from specific sheet - URL encode the sheet name
            import urllib.parse
            if sheet_name:
                encoded_sheet_name = urllib.parse.quote(sheet_name, safe='')
                range_url = f"https://sheets.googleapis.com/v4/spreadsheets/{file_id}/values/{encoded_sheet_name}"
            else:
                # Get the first sheet (default) - try different approaches
                range_url = f"https://sheets.googleapis.com/v4/spreadsheets/{file_id}/values/Sheet1"

            print(f"[DriveChatbot] Requesting data from: {range_url}")
            response = requests.get(range_url, headers=headers)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        values = data.get('values', [])
                        if not values:
                            print(f"[DriveChatbot] No data found in sheet '{sheet_name}' - empty values array")
                        return values
                    else:
                        print(f"[DriveChatbot] Unexpected response format: {type(data)}")
                        print(f"[DriveChatbot] Response content: {data}")
                        return None
                except ValueError as e:
                    print(f"[DriveChatbot] Failed to parse JSON response: {e}")
                    print(f"[DriveChatbot] Response status: {response.status_code}")
                    print(f"[DriveChatbot] Content-Type: {response.headers.get('content-type', 'unknown')}")
                    print(f"[DriveChatbot] Raw response (first 1000 chars): {response.text[:1000]}")
                    # If it's not JSON, it might be an error message
                    if 'error' in response.text.lower():
                        print(f"[DriveChatbot] API returned error message: {response.text}")
                    return None

            print(f"[DriveChatbot] HTTP {response.status_code} error for sheet '{sheet_name}'")
            print(f"[DriveChatbot] Error response: {response.text}")
            print(f"[DriveChatbot] Requested URL: {range_url}")
            return None

        except Exception as e:
            print(f"[DriveChatbot] Error extracting sheet data: {e}")
            return None

    def format_exam_schedule(self, data: List[List[str]], exam_type: str, subject_filter: str = None) -> str:
        """Format exam schedule data into readable text with tabular format and future dates only"""
        if not data or len(data) < 2:
            return f"No {exam_type.upper()} schedule data found."

        from datetime import datetime, timezone
        import re

        # Get current date for filtering
        current_date = datetime.now(timezone.utc)
        current_year = current_date.year

        # For academic year sheets (like "2025-26"), assume September dates are from previous year
        # If current month is January-June, and we see September-December dates, they might be from previous year
        current_month = current_date.month

        # Collect upcoming exams
        upcoming_exams = []

        # Skip header rows and process data
        for row in data[3:]:  # Skip empty row, title row, grade row
            if row and len(row) >= 4:
                day = row[1].strip() if len(row) > 1 else ""
                date_str = row[2].strip() if len(row) > 2 else ""
                subject = row[3].strip() if len(row) > 3 else ""

                if date_str and subject and subject.lower() not in ['regular school', 'prep break']:
                    # Filter by subject if specified
                    if subject_filter:
                        # Normalize subject names for matching
                        subject_normalized = subject.lower().strip()
                        filter_normalized = subject_filter.lower().strip()

                        # Handle common variations
                        subject_mapping = {
                            'math': ['math', 'mathematics', 'maths'],
                            'english': ['english'],
                            'science': ['science'],
                            'hindi': ['hindi'],
                            'french': ['french'],
                            'igs': ['igs', 'integrated general studies'],
                            'social science': ['social science', 'sst', 'social studies']
                        }

                        # Check if the subject matches the filter
                        matches_filter = False
                        for key, variations in subject_mapping.items():
                            if filter_normalized in variations and subject_normalized in variations:
                                matches_filter = True
                                break

                        # Also check direct match
                        if subject_normalized == filter_normalized:
                            matches_filter = True

                        if not matches_filter:
                            continue
                    # Parse date (format: "19-Sep" or similar)
                    try:
                        # Handle various date formats like "19-Sep", "19 September", etc.
                        date_str_clean = date_str.replace('-', ' ').replace('/', ' ')

                        # Try to parse the date
                        if '-' in date_str:
                            # Format like "19-Sep"
                            day_part, month_part = date_str.split('-', 1)
                            try:
                                day_num = int(day_part.strip())
                                month_name = month_part.strip()

                                # Convert month name to number
                                month_names = {
                                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                                    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                                    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
                                }

                                month_num = month_names.get(month_name.lower())
                                if month_num:
                                    # Determine the correct year for the exam date
                                    exam_year = current_year

                                    # If we're in early year (Jan-Jun) and the exam month is late year (Sep-Dec),
                                    # the exam might be from the previous year (academic year logic)
                                    if current_month <= 6 and month_num >= 9:
                                        exam_year = current_year - 1
                                    # If we're in late year (Jul-Dec) and the exam month is early year (Jan-Jun),
                                    # the exam might be from the next year
                                    elif current_month >= 7 and month_num <= 6:
                                        exam_year = current_year + 1

                                    try:
                                        # Create date object
                                        exam_date = datetime(exam_year, month_num, day_num, tzinfo=timezone.utc)

                                        # Only include future dates
                                        if exam_date >= current_date:
                                            upcoming_exams.append({
                                                'date': exam_date,
                                                'day': day,
                                                'date_display': date_str,
                                                'subject': subject
                                            })
                                    except ValueError:
                                        # Invalid date (e.g., Feb 30th), skip
                                        continue
                            except (ValueError, KeyError):
                                # Skip invalid date formats
                                continue
                        else:
                            # Skip if date format is not recognized
                            continue

                    except Exception:
                        # Skip rows with unparseable dates
                        continue

        if not upcoming_exams:
            return f"No upcoming {exam_type.upper()} exams found. All scheduled exams may have passed."

        # Sort by date
        upcoming_exams.sort(key=lambda x: x['date'])

        # Format as table
        response = f"**📅 UPCOMING {exam_type.upper()} Examination Schedule"
        if subject_filter:
            response += f" - {subject_filter.title()}"
        response += ":**\n\n"
        response += "| Date | Day | Subject |\n"
        response += "|------|-----|---------|\n"

        for exam in upcoming_exams:
            response += f"| {exam['date_display']} | {exam['day']} | {exam['subject']} |\n"

        response += f"\n*Showing {len(upcoming_exams)} upcoming exam(s)*"

        return response

    def format_syllabus(self, data: List[List[str]], exam_type: str) -> str:
        """Format syllabus data into readable text"""
        if not data or len(data) < 2:
            return f"No {exam_type.upper()} syllabus data found."

        response = f"**{exam_type.upper()} Syllabus:**\n\n"

        # Process syllabus data (usually in the first few rows)
        for row in data[1:3]:  # Usually syllabus is in first 2-3 rows
            if row and len(row) > 1:
                subject = row[0].strip() if len(row) > 0 else ""
                content = row[1].strip() if len(row) > 1 else ""

                if subject and content:
                    # Truncate long content for chat response
                    if len(content) > 200:
                        content = content[:200] + "..."
                    response += f"**{subject}:**\n{content}\n\n"

        return response

    def format_timetable(self, data: List[List[str]], filter_day: str = None, filter_days: list[str] = None) -> str:
        """Format timetable data into readable table with proper null handling"""
        if not data or len(data) < 3:
            return "No timetable data found."

        # If filtering by day(s), determine which days to show
        target_days = []
        if filter_days and len(filter_days) > 0:
            # Multiple days requested
            print(f"[DriveChatbot] Filtering timetable for multiple days: {filter_days}")
            for day in filter_days:
                if day.lower() in ['today', 'todays', "today's"]:
                    # Get current day
                    from datetime import datetime
                    current_day = datetime.now().strftime('%A').upper()
                    target_days.append(current_day)
                else:
                    # Try to match the day to a valid day name
                    day_upper = day.upper()
                    valid_days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
                    if day_upper in valid_days:
                        target_days.append(day_upper)
            # Remove duplicates
            target_days = list(set(target_days))
        elif filter_day:
            # Single day requested (backward compatibility)
            if filter_day.lower() in ['today', 'todays', "today's"]:
                # Get current day
                from datetime import datetime
                current_day = datetime.now().strftime('%A').upper()
                target_days = [current_day]
                print(f"[DriveChatbot] Filtering timetable for today: {current_day}")
            else:
                # Try to match the filter_day to a valid day name
                filter_day_upper = filter_day.upper()
                valid_days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
                if filter_day_upper in valid_days:
                    target_days = [filter_day_upper]
                    print(f"[DriveChatbot] Filtering timetable for day: {filter_day_upper}")

        # If no valid days found, show all days
        if not target_days:
            target_days = None

        response = f"🕐 **Daily Timetable"
        if target_days and len(target_days) == 1:
            response += f" - {target_days[0].title()}**"
        elif target_days and len(target_days) > 1:
            day_names = [day.title() for day in target_days]
            response += f" - {', '.join(day_names)}**"
        else:
            response += "**"
        response += "\n\n"

        # Extract time slots from first row (skip first empty cell)
        time_slots = []
        if len(data) > 0 and data[0]:
            time_slots = [cell.strip() if cell else "" for cell in data[0][1:]]

        # Create table header
        response += "| Day | Time Slot | Subject | Teacher |\n"
        response += "|-----|-----------|---------|---------|\n"

        # Process each day row by row
        i = 1  # Start from row 1 (after time slots)
        found_matching_day = False

        while i < len(data):
            row = data[i]
            if not row or len(row) == 0:
                i += 1
                continue

            day_name = row[0].strip() if len(row) > 0 and row[0] else ""

            # Check if this is a day row (has day name in first column)
            if day_name and day_name.upper() in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
                current_day = day_name.upper()

                # Skip this day if we're filtering and it doesn't match any of the target days
                if target_days and current_day not in target_days:
                    i += 1
                    continue

                found_matching_day = True

                # Get subjects for this day (from column 1 onwards, preserve nulls)
                subjects = []
                for cell in row[1:]:
                    subjects.append(cell.strip() if cell else "")

                # Check if next row has teachers (first cell should be empty/blank)
                teachers = []
                next_row = data[i + 1] if i + 1 < len(data) else None

                if (next_row and len(next_row) > 0 and
                    (not next_row[0] or not next_row[0].strip()) and  # First cell is blank
                    (len(next_row) <= 1 or not next_row[1] or not next_row[1].strip() or next_row[1].strip().upper() not in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"])):

                    # This is a teacher row - extract teacher data from column 1 onwards to match subjects
                    for cell in next_row[1:]:
                        teachers.append(cell.strip() if cell else "")
                    i += 1  # Skip the teacher row we just processed
                else:
                    # No teacher row found, use empty teachers
                    teachers = [""] * len(subjects)

                # Now create table rows for this day, ensuring all columns align
                max_slots = max(len(time_slots), len(subjects), len(teachers))

                for slot_idx in range(max_slots):
                    time_slot = time_slots[slot_idx] if slot_idx < len(time_slots) else ""
                    subject = subjects[slot_idx] if slot_idx < len(subjects) else ""
                    teacher = teachers[slot_idx] if slot_idx < len(teachers) else ""

                    # First row shows the day name, subsequent rows are blank in day column
                    day_display = f"**{current_day}**" if slot_idx == 0 else ""

                    response += f"| {day_display} | {time_slot} | {subject} | {teacher} |\n"

                # Add separator row between days (but not at the end)
                if target_days and len(target_days) > 1:  # Only add separator if showing multiple days
                    response += "|  |  |  |  |\n"

            i += 1

        if target_days and not found_matching_day:
            if len(target_days) == 1:
                return f"No timetable data found for {target_days[0].title()}."
            else:
                day_names = [day.title() for day in target_days]
                return f"No timetable data found for {', '.join(day_names)}."

        return response

    def get_exam_info(self, user_query: str, user_profile: dict = None) -> str:
        """Main function to get exam information for chatbot"""

        # Step 1: Analyze the query
        analysis = self.detector.analyze_query(user_query)
        grade = analysis['grade']
        exam_type = analysis['exam_type']
        query_type = analysis['query_type']
        subject_filter = analysis['subject']  # Single subject for backward compatibility
        subjects_filter = analysis['subjects']  # List of all subjects
        day_filter = analysis['day']  # Single day for backward compatibility
        days_filter = analysis['days']  # List of all days

        # Step 1.5: If no grade in query, try to get from user profile
        print(f"[DriveChatbot] 🔍 Checking user profile for grade: user_profile={user_profile}")
        if not grade and user_profile:
            profile_grade = user_profile.get('grade')
            print(f"[DriveChatbot] 🔍 Profile grade field: {profile_grade}")
            if profile_grade:
                # Extract grade number from profile (e.g., "Grade 7" -> "7")
                import re
                grade_match = re.search(r'(\d+)', str(profile_grade))
                if grade_match:
                    grade = grade_match.group(1)
                    print(f"[DriveChatbot] Using grade {grade} from user profile")
                else:
                    print(f"[DriveChatbot] Could not extract grade number from: {profile_grade}")
            else:
                print(f"[DriveChatbot] No grade field in user profile")

        print(f"[DriveChatbot] Query Analysis: Grade={grade}, Exam={exam_type}, Type={query_type}, Subject={subject_filter}, Subjects={subjects_filter}, Day={day_filter}, Days={days_filter}")

        # Step 2: Validate we have required info
        if not grade:
            return "I couldn't determine which grade you're asking about. Please specify your grade (e.g., 'grade 7', 'G8', 'class 9')."

        # Step 3: Get active Drive token
        token = self.get_active_drive_token()
        if not token:
            return "Sorry, the Google Drive connection is not available right now. Please contact your administrator."

        # Step 4: Find the grade-specific sheet
        file_id = self.find_grade_sheet(grade, token)
        if not file_id:
            return f"Sorry, I couldn't find the Grade {grade} information sheet. Please contact your administrator."

        print(f"[DriveChatbot] Found sheet for Grade {grade}: {file_id}")

        # Step 5: Determine which tab to read
        target_sheet = None

        if query_type == 'teacher':
            # For teacher queries, we need timetable data
            target_sheet = "TT"  # Regular Time Table
        elif query_type == 'teacher_subject':
            # For teacher subject queries (reverse lookup), we need timetable data
            target_sheet = "TT"  # Regular Time Table
        elif exam_type and query_type == 'schedule':
            if exam_type.upper() == 'SA1':
                target_sheet = "SA1 Date sheet and Syllabus"
            elif exam_type.upper() == 'SA2':
                target_sheet = "SA 2 Date Sheet"
            else:
                target_sheet = "Examination Schedule"
        elif exam_type and query_type == 'syllabus':
            if exam_type.upper() == 'SA1':
                target_sheet = "SA 1 Syllabus"
            elif exam_type.upper() == 'SA2':
                target_sheet = "SA 2 Syllabus"
            else:
                target_sheet = "Examination Schedule"
        elif query_type == 'timetable':
            target_sheet = "TT"  # Regular Time Table
        else:
            # Fallback to general exam schedule
            target_sheet = "Examination Schedule"

        # Step 6: Extract data from the target sheet
        sheet_data = self.extract_sheet_data(file_id, target_sheet, token)

        if not sheet_data:
            return f"Sorry, I couldn't find the '{target_sheet}' information for Grade {grade}."

        # Step 7: Format the response based on query type
        if query_type == 'teacher':
            # Handle teacher queries - find teacher for specific subject
            if subject_filter:
                # Use simple lookup instead of API call
                return self.get_subject_teacher_simple(subject_filter)
            else:
                return "Please specify which subject teacher you're looking for (e.g., 'who is the maths teacher')."
        elif query_type == 'teacher_subject':
            # Handle teacher subject queries - find subjects taught by teacher
            teacher_name = analysis.get('teacher_name')
            if teacher_name:
                return self.get_teacher_subjects_simple(teacher_name)
            else:
                return "Please specify which teacher you're asking about (e.g., 'what subject does Mrs. Sumayya teach')."
        elif query_type == 'schedule':
            # Special handling for general "upcoming exam" queries (no specific exam type)
            if exam_type is None:
                # Check if multiple subjects were requested
                if len(subjects_filter) > 1:
                    return self.get_multi_subject_exam_schedule(file_id, token, grade, subjects_filter)
                else:
                    return self.get_all_upcoming_exams(file_id, token, grade, subject_filter)
            else:
                return self.format_exam_schedule(sheet_data, exam_type or "exam", subject_filter)
        elif query_type == 'syllabus':
            return self.format_syllabus(sheet_data, exam_type or "exam")
        elif query_type == 'timetable':
            # Check if multiple days were requested
            if days_filter and len(days_filter) > 1:
                return self.format_timetable(sheet_data, None, days_filter)
            else:
                return self.format_timetable(sheet_data, day_filter, days_filter)
        else:
            # General exam info - show a summary of upcoming exams
            # Check if multiple subjects were requested
            if len(subjects_filter) > 1:
                return self.get_multi_subject_exam_schedule(file_id, token, grade, subjects_filter)
            else:
                return self.get_all_upcoming_exams(file_id, token, grade, subject_filter)

    def get_all_upcoming_exams(self, file_id: str, token: Dict[str, Any], grade: str, subject_filter: str = None) -> str:
        """Get upcoming exams from all relevant exam tabs and combine them"""
        from datetime import datetime, timezone
        import re

        # Get current date for filtering
        current_date = datetime.now(timezone.utc)
        current_year = current_date.year
        current_month = current_date.month

        # Define exam tabs to check for upcoming exams
        exam_tabs = [
            ("SA 2 Date Sheet", "SA2"),
            ("Examination Schedule", "General"),
            ("SA1 Date sheet and Syllabus", "SA1")  # Check SA1 too in case of future dates
        ]

        all_upcoming_exams = []

        for tab_name, exam_label in exam_tabs:
            try:
                sheet_data = self.extract_sheet_data(file_id, tab_name, token)
                if sheet_data:
                    # Parse dates from this tab
                    for row in sheet_data[3:]:  # Skip header rows
                        if row and len(row) >= 4:
                            day = row[1].strip() if len(row) > 1 else ""
                            date_str = row[2].strip() if len(row) > 2 else ""
                            subject = row[3].strip() if len(row) > 3 else ""

                            if date_str and subject and subject.lower() not in ['regular school', 'prep break']:
                                # Filter by subject if specified
                                if subject_filter:
                                    # Normalize subject names for matching
                                    subject_normalized = subject.lower().strip()
                                    filter_normalized = subject_filter.lower().strip()

                                    # Handle common variations
                                    subject_mapping = {
                                        'math': ['math', 'mathematics', 'maths'],
                                        'english': ['english'],
                                        'science': ['science'],
                                        'hindi': ['hindi'],
                                        'french': ['french'],
                                        'igs': ['igs', 'integrated general studies'],
                                        'social science': ['social science', 'sst', 'social studies']
                                    }

                                    # Check if the subject matches the filter
                                    matches_filter = False
                                    for key, variations in subject_mapping.items():
                                        if filter_normalized in variations and subject_normalized in variations:
                                            matches_filter = True
                                            break

                                    # Also check direct match
                                    if subject_normalized == filter_normalized:
                                        matches_filter = True

                                    if not matches_filter:
                                        continue
                                # Parse date
                                try:
                                    if '-' in date_str:
                                        day_part, month_part = date_str.split('-', 1)
                                        day_num = int(day_part.strip())
                                        month_name = month_part.strip()

                                        month_names = {
                                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                                            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                                            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
                                        }

                                        month_num = month_names.get(month_name.lower())
                                        if month_num:
                                            # Determine correct year
                                            exam_year = current_year
                                            if current_month <= 6 and month_num >= 9:
                                                exam_year = current_year - 1
                                            elif current_month >= 7 and month_num <= 6:
                                                exam_year = current_year + 1

                                            exam_date = datetime(exam_year, month_num, day_num, tzinfo=timezone.utc)

                                            # Only include future dates
                                            if exam_date >= current_date:
                                                all_upcoming_exams.append({
                                                    'date': exam_date,
                                                    'day': day,
                                                    'date_display': date_str,
                                                    'subject': subject,
                                                    'exam_type': exam_label
                                                })
                                except (ValueError, KeyError):
                                    continue
            except Exception:
                # Skip tabs that can't be read
                continue

        if not all_upcoming_exams:
            return "No upcoming exams found. All scheduled exams may have passed."

        # Sort by date
        all_upcoming_exams.sort(key=lambda x: x['date'])

        # Format as table
        response = f"**📅 UPCOMING EXAMINATION SCHEDULE"
        if subject_filter:
            response += f" - {subject_filter.title()}"
        response += ":**\n\n"
        response += "| Date | Day | Subject | Exam |\n"
        response += "|------|-----|---------|------|\n"

        for exam in all_upcoming_exams:
            response += f"| {exam['date_display']} | {exam['day']} | {exam['subject']} | {exam['exam_type']} |\n"

        response += f"\n*Showing {len(all_upcoming_exams)} upcoming exam(s)*"

        return response

    def get_multi_subject_exam_schedule(self, file_id: str, token: Dict[str, Any], grade: str, subjects: list[str]) -> str:
        """Get exam schedules for multiple subjects and combine them"""
        from datetime import datetime, timezone

        # Get current date for filtering
        current_date = datetime.now(timezone.utc)
        current_year = current_date.year
        current_month = current_date.month

        # Define exam tabs to check
        exam_tabs = [
            ("SA 2 Date Sheet", "SA2"),
            ("Examination Schedule", "General"),
            ("SA1 Date sheet and Syllabus", "SA1")
        ]

        all_upcoming_exams = []

        # Collect exams for all requested subjects
        for subject in subjects:
            subject_exams = []

            for tab_name, exam_label in exam_tabs:
                try:
                    sheet_data = self.extract_sheet_data(file_id, tab_name, token)
                    if sheet_data:
                        # Parse dates from this tab for this subject
                        for row in sheet_data[3:]:  # Skip header rows
                            if row and len(row) >= 4:
                                day = row[1].strip() if len(row) > 1 else ""
                                date_str = row[2].strip() if len(row) > 2 else ""
                                exam_subject = row[3].strip() if len(row) > 3 else ""

                                if date_str and exam_subject and exam_subject.lower() not in ['regular school', 'prep break']:
                                    # Check if this subject matches the requested subject
                                    subject_normalized = exam_subject.lower().strip()
                                    filter_normalized = subject.lower().strip()

                                    # Subject mapping for matching
                                    subject_mapping = {
                                        'math': ['math', 'mathematics', 'maths'],
                                        'english': ['english'],
                                        'science': ['science'],
                                        'hindi': ['hindi'],
                                        'french': ['french'],
                                        'igs': ['igs', 'integrated general studies'],
                                        'social science': ['social science', 'sst', 'social studies']
                                    }

                                    matches_filter = False
                                    for key, variations in subject_mapping.items():
                                        if filter_normalized in variations and subject_normalized in variations:
                                            matches_filter = True
                                            break

                                    if subject_normalized == filter_normalized:
                                        matches_filter = True

                                    if matches_filter:
                                        # Parse date
                                        try:
                                            if '-' in date_str:
                                                day_part, month_part = date_str.split('-', 1)
                                                day_num = int(day_part.strip())
                                                month_name = month_part.strip()

                                                month_names = {
                                                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                                                    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                                                    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
                                                }

                                                month_num = month_names.get(month_name.lower())
                                                if month_num:
                                                    # Determine correct year
                                                    exam_year = current_year
                                                    if current_month <= 6 and month_num >= 9:
                                                        exam_year = current_year - 1
                                                    elif current_month >= 7 and month_num <= 6:
                                                        exam_year = current_year + 1

                                                    exam_date = datetime(exam_year, month_num, day_num, tzinfo=timezone.utc)

                                                    # Only include future dates
                                                    if exam_date >= current_date:
                                                        subject_exams.append({
                                                            'date': exam_date,
                                                            'day': day,
                                                            'date_display': date_str,
                                                            'subject': exam_subject,
                                                            'exam_type': exam_label,
                                                            'requested_subject': subject
                                                        })
                                        except (ValueError, KeyError):
                                            continue
                except Exception:
                    continue

            all_upcoming_exams.extend(subject_exams)

        if not all_upcoming_exams:
            subject_names = [s.title() for s in subjects]
            return f"No upcoming exams found for {', '.join(subject_names)}."

        # Sort by date
        all_upcoming_exams.sort(key=lambda x: x['date'])

        # Group by subject for better display
        exams_by_subject = {}
        for exam in all_upcoming_exams:
            subject = exam['requested_subject']
            if subject not in exams_by_subject:
                exams_by_subject[subject] = []
            exams_by_subject[subject].append(exam)

        # Format as combined response
        subject_names = [s.title() for s in subjects]
        response = f"**📅 UPCOMING EXAMINATION SCHEDULE - {', '.join(subject_names)}:**\n\n"

        for subject in subjects:
            if subject in exams_by_subject and exams_by_subject[subject]:
                subject_exams = exams_by_subject[subject]
                response += f"**{subject.title()}:**\n"
                response += "| Date | Day | Subject | Exam |\n"
                response += "|------|-----|---------|------|\n"

                for exam in subject_exams:
                    response += f"| {exam['date_display']} | {exam['day']} | {exam['subject']} | {exam['exam_type']} |\n"

                response += "\n"

        total_exams = len(all_upcoming_exams)
        response += f"*Showing {total_exams} upcoming exam(s) across {len(subjects)} subject(s)*"

        return response

    def get_subject_teacher_simple(self, subject: str) -> str:
        """Simple subject-to-teacher lookup using known timetable data"""
        # Known teacher assignments from Grade 7 timetable
        teacher_map = {
            'math': 'Mrs. Sumayya',
            'mathematics': 'Mrs. Sumayya',
            'maths': 'Mrs. Sumayya',
            'science': 'Mrs. Krishna and Mr. Mohit',
            'physics': 'Mrs. Krishna and Mr. Mohit',
            'chemistry': 'Mrs. Krishna and Mr. Mohit',
            'biology': 'Mrs. Krishna and Mr. Mohit',
            'english': 'Ms. Harshita',
            'literature': 'Ms. Harshita',
            'grammar': 'Ms. Harshita',
            'hindi': 'Mr. Umesh',
            'hindustani': 'Mr. Umesh',
            'french': 'Ms. Shraddha',
            'français': 'Ms. Shraddha',
            'igs': 'Ms. Rishika',
            'integrated general studies': 'Ms. Rishika',
            'art': 'Ms. Pallavi and Mr. Manoj',
            'art & design': 'Ms. Pallavi and Mr. Manoj',
            'design': 'Ms. Pallavi and Mr. Manoj',
            'football': 'Ms. Akanksha',
            'basketball': 'Mr. Amarnath',
            'rock climbing': 'Mr. Amarnath',
            'cardio': 'Mr. Amarnath',
            'stem': 'Tripto Kochar',
            'computing': 'Tripto Kochar',
            'music': 'Mr. Ankit and Ms. Swati',
            'circle time': 'Ms. Ashita, Mrs. Sumayya, and Mr. Umesh',
            'purpose community': 'Mrs. Krishna, Mrs. Sumayya',
            'research & development': 'Mrs. Krishna, Mrs. Sumayya',
            'theatre': 'Theatre',
            'mindfulness': '',
            'breakfast': '',
            'lunch': '',
            'lib': 'Ms. Poonam and Mr. Vikas'
        }

        subject_lower = subject.lower()
        teacher = teacher_map.get(subject_lower)

        if teacher:
            if len(teacher.split(' and ')) > 1:
                return f"The {subject.title()} teachers are {teacher}."
            else:
                return f"The {subject.title()} teacher is {teacher}."
        else:
            return f"I couldn't find teacher information for {subject.title()}."

    def get_teacher_subjects_simple(self, teacher_name: str) -> str:
        """Simple teacher-to-subjects lookup using known timetable data"""
        teacher_name_lower = teacher_name.lower().strip()

        # Known teacher assignments from Grade 7 timetable (reverse lookup)
        subject_map = {
            'mrs. sumayya': ['Maths', 'Circle Time', 'Purpose Community', 'Research & Development'],
            'sumayya': ['Maths', 'Circle Time', 'Purpose Community', 'Research & Development'],
            'mrs. krishna': ['Science', 'Purpose Community', 'Research & Development'],
            'krishna': ['Science', 'Purpose Community', 'Research & Development'],
            'krishana': ['Science', 'Purpose Community', 'Research & Development'],
            'mrs. krishana': ['Science', 'Purpose Community', 'Research & Development'],
            'mr. mohit': ['Science'],
            'mohit': ['Science'],
            'ms. harshita': ['English'],
            'harshita': ['English'],
            'mr. umesh': ['Hindi', 'Circle Time'],
            'umesh': ['Hindi', 'Circle Time'],
            'ms. shraddha': ['French'],
            'shraddha': ['French'],
            'ms. rishika': ['IGS'],
            'rishika': ['IGS'],
            'ms. pallavi': ['Art & Design'],
            'pallavi': ['Art & Design'],
            'mr. manoj': ['Art & Design'],
            'manoj': ['Art & Design'],
            'ms. akanksha': ['Football'],
            'akanksha': ['Football'],
            'mr. amarnath': ['Basketball', 'Rock Climbing', 'Cardio'],
            'amarnath': ['Basketball', 'Rock Climbing', 'Cardio'],
            'tripto kochar': ['STEM', 'Computing'],
            'mr. ankit': ['Music'],
            'ankit': ['Music'],
            'ms. swati': ['Music'],
            'swati': ['Music'],
            'ms. ashita': ['Circle Time'],
            'ashita': ['Circle Time'],
            'ms. poonam': ['Lib'],
            'poonam': ['Lib'],
            'mr. vikas': ['Lib'],
            'vikas': ['Lib']
        }

        # Normalize teacher name (remove salutations for matching)
        normalized_name = teacher_name_lower
        # Handle salutations with space (e.g., "mrs. krishana")
        if normalized_name.startswith(('mr. ', 'mrs. ', 'ms. ', 'dr. ')):
            normalized_name = normalized_name.split(' ', 1)[1] if ' ' in normalized_name else normalized_name
        # Handle salutations without space (e.g., "mrs.krishana")
        elif normalized_name.startswith(('mr.', 'mrs.', 'ms.', 'dr.')):
            normalized_name = normalized_name.split('.', 1)[1] if '.' in normalized_name else normalized_name

        subjects = subject_map.get(teacher_name_lower) or subject_map.get(normalized_name)

        if subjects:
            if len(subjects) == 1:
                return f"TEACHER_SUBJECT: {teacher_name} teaches {subjects[0]}."
            else:
                subject_list = ", ".join(subjects[:-1]) + " and " + subjects[-1]
                return f"TEACHER_SUBJECT: {teacher_name} teaches {subject_list}."
        else:
            return f"TEACHER_SUBJECT: I couldn't find subject information for {teacher_name} in the Grade 7 timetable."

    def get_teacher_subjects(self, file_id: str, token: Dict[str, Any], grade: str, teacher_name: str) -> str:
        """Find and return the subject(s) taught by a specific teacher from timetable data"""
        try:
            print(f"[DriveChatbot] Looking up subjects taught by teacher: {teacher_name}")

            # Get timetable data - try default sheet first (main sheet contains timetable)
            print(f"[DriveChatbot] Requesting default sheet (main sheet) from file {file_id}")
            sheet_data = self.extract_sheet_data(file_id, "", token)

            if not sheet_data or len(sheet_data) < 3:
                print(f"[DriveChatbot] Main sheet not found or empty, trying 'TT' sheet")
                # Try TT sheet as fallback
                sheet_data = self.extract_sheet_data(file_id, token, "TT")
                if not sheet_data or len(sheet_data) < 3:
                    print(f"[DriveChatbot] TT sheet also not found or empty: {sheet_data}")
                    return f"I couldn't find timetable data for Grade {grade}."

            print(f"[DriveChatbot] Sheet data type: {type(sheet_data)}")
            print(f"[DriveChatbot] Sheet data length: {len(sheet_data) if sheet_data else 0}")

            found_subjects = []

            i = 0
            while i < len(sheet_data):
                row = sheet_data[i]

                if not row or len(row) == 0:
                    i += 1
                    continue

                day_name = row[0].strip() if len(row) > 0 and row[0] else ""

                # Check if this is a day row
                if day_name and day_name.upper() in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
                    # Get subjects for this day
                    subjects = []
                    for cell in row[1:]:
                        subjects.append(cell.strip() if cell else "")

                    # Check if next row has teachers
                    teachers = []
                    next_row = sheet_data[i + 1] if i + 1 < len(sheet_data) else None

                    if (next_row and len(next_row) > 0 and
                        (not next_row[0] or not next_row[0].strip()) and
                        (len(next_row) <= 1 or not next_row[1] or not next_row[1].strip() or next_row[1].strip().upper() not in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"])):

                        # This is a teacher row - extract teacher data
                        for cell in next_row[1:]:
                            teachers.append(cell.strip() if cell else "")
                        i += 1  # Skip the teacher row we just processed
                    else:
                        # No teacher row found, use empty teachers
                        teachers = [""] * len(subjects)

                    # Look for the requested teacher and get the corresponding subject(s)
                    for subj_idx, subj in enumerate(subjects):
                        if subj and subj_idx < len(teachers):
                            teacher_name_in_table = teachers[subj_idx]
                            if teacher_name_in_table:
                                # Handle combined teacher names (e.g., "Mohit/Krishna")
                                if '/' in teacher_name_in_table:
                                    combined_names = [name.strip() for name in teacher_name_in_table.split('/') if name.strip()]
                                    for name in combined_names:
                                        if name and self._teacher_names_match(name, teacher_name) and subj not in found_subjects:
                                            found_subjects.append(subj)
                                else:
                                    # Single teacher name
                                    if self._teacher_names_match(teacher_name_in_table, teacher_name) and subj not in found_subjects:
                                        found_subjects.append(subj)

                i += 1

            if not found_subjects:
                return f"I couldn't find any subjects taught by {teacher_name} in the Grade {grade} timetable."

            if len(found_subjects) == 1:
                return f"TEACHER_SUBJECT: {teacher_name} teaches {found_subjects[0]}."
            else:
                subject_list = ", ".join(found_subjects[:-1]) + " and " + found_subjects[-1]
                return f"TEACHER_SUBJECT: {teacher_name} teaches {subject_list}."

        except Exception as e:
            print(f"[DriveChatbot] Error getting teacher subjects: {e}")
            return f"Sorry, I encountered an error while looking up subjects taught by {teacher_name}."

    def _teacher_names_match(self, table_name: str, query_name: str) -> bool:
        """Check if teacher names match, handling salutations and variations"""
        if not table_name or not query_name:
            return False

        # Normalize both names (remove salutations, extra spaces, case)
        def normalize_name(name: str) -> str:
            name = name.lower().strip()
            # Remove common salutations
            salutations = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.']
            for sal in salutations:
                if name.startswith(sal):
                    name = name[len(sal):].strip()
            return name

        table_normalized = normalize_name(table_name)
        query_normalized = normalize_name(query_name)

        # Exact match
        if table_normalized == query_normalized:
            return True

        # Partial match (one contains the other)
        if table_normalized in query_normalized or query_normalized in table_normalized:
            return True

        return False

    def get_subject_teacher(self, file_id: str, token: Dict[str, Any], grade: str, subject: str) -> str:
        """Find and return the teacher name for a specific subject from timetable data"""
        try:
            # Get the timetable sheet (TT tab)
            sheet_data = self.extract_sheet_data(file_id, "TT", token)
            if not sheet_data:
                return f"Sorry, I couldn't find timetable information for Grade {grade}."

            # Look for the subject in the timetable and get associated teacher
            found_teachers = []

            i = 1  # Start from row 1 (after time slots)
            while i < len(sheet_data):
                row = sheet_data[i]
                if not row or len(row) == 0:
                    i += 1
                    continue

                day_name = row[0].strip() if len(row) > 0 and row[0] else ""

                # Check if this is a day row
                if day_name and day_name.upper() in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
                    # Get subjects for this day
                    subjects = []
                    for cell in row[1:]:
                        subjects.append(cell.strip() if cell else "")

                    # Check if next row has teachers
                    teachers = []
                    next_row = sheet_data[i + 1] if i + 1 < len(sheet_data) else None

                    if (next_row and len(next_row) > 0 and
                        (not next_row[0] or not next_row[0].strip()) and
                        (len(next_row) <= 1 or not next_row[1] or not next_row[1].strip() or next_row[1].strip().upper() not in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"])):

                        # This is a teacher row - extract teacher data
                        for cell in next_row[1:]:
                            teachers.append(cell.strip() if cell else "")
                        i += 1  # Skip the teacher row we just processed
                    else:
                        # No teacher row found, use empty teachers
                        teachers = [""] * len(subjects)

                    # Look for the requested subject and get the corresponding teacher
                    for subj_idx, subj in enumerate(subjects):
                        if subj and self._subjects_match(subj, subject) and subj_idx < len(teachers):
                            teacher_name = teachers[subj_idx]
                            if teacher_name:
                                # Handle combined teacher names (e.g., "Mohit/Krishna")
                                if '/' in teacher_name:
                                    # Split combined names and add each one
                                    combined_names = [name.strip() for name in teacher_name.split('/') if name.strip()]
                                    for name in combined_names:
                                        if name and name not in found_teachers:
                                            found_teachers.append(name)
                                else:
                                    # Single teacher name
                                    if teacher_name not in found_teachers:
                                        found_teachers.append(teacher_name)

                i += 1

            if not found_teachers:
                return f"I couldn't find a teacher for {subject.title()} in the Grade {grade} timetable."

            # Remove duplicates and format response
            unique_teachers = list(set(found_teachers))
            formatted_teachers = [self._format_teacher_name(teacher) for teacher in unique_teachers]

            if len(formatted_teachers) == 1:
                return f"TEACHER_INFO: The {subject.title()} teacher is {formatted_teachers[0]}."
            else:
                teacher_list = ", ".join(formatted_teachers[:-1]) + " and " + formatted_teachers[-1]
                return f"TEACHER_INFO: The {subject.title()} teachers are {teacher_list}."

        except Exception as e:
            print(f"[DriveChatbot] Error getting subject teacher: {e}")
            return f"Sorry, I encountered an error while looking up the {subject.title()} teacher."

    def _subjects_match(self, timetable_subject: str, requested_subject: str) -> bool:
        """Check if timetable subject matches the requested subject"""
        # Normalize both subjects
        timetable_norm = timetable_subject.lower().strip()
        requested_norm = requested_subject.lower().strip()

        # Subject mapping for matching variations
        subject_mapping = {
            'math': ['math', 'mathematics', 'maths'],
            'english': ['english'],
            'science': ['science'],
            'hindi': ['hindi'],
            'french': ['french'],
            'igs': ['igs', 'integrated general studies'],
            'social science': ['social science', 'sst', 'social studies'],
            'history': ['history'],
            'geography': ['geography'],
            'economics': ['economics'],
            'biology': ['biology'],
            'physics': ['physics'],
            'chemistry': ['chemistry']
        }

        # Check if subjects match through mapping
        for key, variations in subject_mapping.items():
            if requested_norm in variations and timetable_norm in variations:
                return True

        # Direct match
        return timetable_norm == requested_norm

    def _format_teacher_name(self, teacher_name: str) -> str:
        """Format teacher name with appropriate salutation based on gender"""
        if not teacher_name or teacher_name.strip() == "":
            return teacher_name

        name = teacher_name.strip()
        name_lower = name.lower()

        # Common male name indicators (Indian names)
        male_indicators = [
            'kumar', 'singh', 'sharma', 'verma', 'gupta', 'jain', 'patel', 'shah',
            'mohit', 'rohit', 'amit', 'sumit', 'rahul', 'vikas', 'suresh', 'ramesh',
            'rajesh', 'sanjay', 'ajay', 'vijay', 'sachin', 'arjun', 'karan', 'aman',
            'ankur', 'deepak', 'manoj', 'pankaj', 'raj', 'ram', 'shyam', 'hari',
            'govind', 'arun', 'sunil', 'anil', 'vinod', 'mahesh', 'naresh',
            'dinesh', 'ravi', 'rajiv', 'sandeep', 'nitin', 'ashok', 'vinay', 'atul',
            'umesh', 'amarnath'
        ]

        # Common female name indicators (Indian names)
        female_indicators = [
            'kumari', 'kavita', 'priya', 'kiran', 'rekha', 'sunita', 'anita', 'rita',
            'geeta', 'neeta', 'meeta', 'sheetal', 'pooja', 'kajal', 'anjali', 'kavya',
            'shraddha', 'neha', 'priyanka', 'deepika', 'pallavi', 'swati', 'anju',
            'sarika', 'manju', 'indu', 'usha', 'asha', 'lata', 'suman', 'amita',
            'seema', 'reema', 'veena', 'meena', 'sudha', 'pushpa', 'madhuri', 'nandini',
            'vidya', 'pratibha', 'shobha', 'aruna', 'sharda', 'sushma', 'maya', 'radha',
            'kanti', 'kanta', 'smita', 'nita', 'sangeeta', 'shanti', 'shashi', 'manisha',
            'anamika', 'kiran', 'rekha', 'sunita', 'anita', 'rita', 'geeta', 'neeta',
            'krishna'  # Can be female in Indian contexts
        ]

        # Check for exact male name matches first
        for male_name in male_indicators:
            if male_name in name_lower:
                return f"Mr. {name}"

        # Check for exact female name matches
        for female_name in female_indicators:
            if female_name in name_lower:
                return f"Mrs. {name}"

        # Gender detection based on name endings (Indian naming patterns)
        # Female names often end with 'a', 'i', 'ee', etc.
        female_endings = ['a', 'i', 'ee', 'ya', 'ti', 'vi', 'mi', 'ri', 'pi', 'ki', 'li', 'ni', 'si']

        # Male names often end with 'u', 'o', or consonants
        male_endings = ['u', 'o']

        # Check female endings
        if any(name_lower.endswith(ending) for ending in female_endings):
            return f"Mrs. {name}"

        # Check male endings
        if any(name_lower.endswith(ending) for ending in male_endings):
            return f"Mr. {name}"

        # For names that don't match patterns, default to Mr. (more common in professional contexts)
        # But be more conservative - if unsure, use the name without salutation
        return name

# Test the integrator
if __name__ == "__main__":
    integrator = DriveChatbotIntegrator()

    test_queries = [
        "When is SA1 exam for grade 7?",  # This should work with G7 data
        "When is SA2 exam for grade 7?",  # This should work with G7 data - FEBRUARY dates
        "What is the syllabus for SA2 in grade 7?",  # This should work with G7 data
        "Show me the timetable for grade 7",  # This should work with G7 data
        "Grade 7 exam schedule"  # This should work with G7 data
    ]

    print("Chatbot Integration Test Results:")
    print("=" * 50)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            response = integrator.get_exam_info(query)
            print(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")

        print("-" * 30)
