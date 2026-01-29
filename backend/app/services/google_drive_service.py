"""
Google Drive Service for Exam File Access

Uses Domain-Wide Delegation to access exam files shared with admin account
"""

import os
import io
import json
import re
from typing import Dict, List, Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError


class GoogleDriveService:
    """Service for accessing Google Drive files via Domain-Wide Delegation"""

    def __init__(self):
        self.dwd_service = None
        self._init_dwd_service()

    def _init_dwd_service(self):
        """Initialize DWD service for Drive access"""
        try:
            from .google_dwd_service import GoogleDWDService
            self.dwd_service = GoogleDWDService()
        except ImportError:
            print("Error: GoogleDWDService not found")
            self.dwd_service = None

    def get_drive_service(self, user_email: str):
        """Get authenticated Drive service for a user via DWD"""
        if not self.dwd_service:
            return None

        try:
            # Get delegated credentials for the user
            delegated_credentials = self.dwd_service.get_delegated_credentials(user_email)
            if not delegated_credentials:
                print(f"Failed to get delegated credentials for {user_email}")
                return None

            # Clear any scopes that might have been added during credential creation
            if hasattr(delegated_credentials, '_scopes') and delegated_credentials._scopes:
                delegated_credentials._scopes = None
            if hasattr(delegated_credentials, 'scopes') and delegated_credentials.scopes:
                try:
                    delegated_credentials = delegated_credentials.with_scopes(None)
                except:
                    pass

            # Build Drive service
            return build('drive', 'v3', credentials=delegated_credentials, cache_discovery=False)

        except Exception as e:
            print(f"Error creating Drive service for {user_email}: {e}")
            return None

    def search_exam_files(self, admin_email: str, query: str = None, max_results: int = 20) -> List[Dict]:
        """Search for exam-related files in admin's Drive"""
        drive_service = self.get_drive_service(admin_email)
        if not drive_service:
            return []

        try:
            # Default exam-related keywords if no specific query
            if not query:
                exam_keywords = [
                    'exam', 'examination', 'test', 'assessment', 'schedule', 'timetable',
                    'results', 'marks', 'grades', 'score', 'paper', 'question paper',
                    'final', 'midterm', 'quiz', 'evaluation', 'report card', 'infosheet',
                    'info sheet', 'info', 'sheet', 'timetable', 'time table', 'date sheet',
                    'syllabus', 'sa1', 'sa2', 'fa1', 'fa2', 'fa3', 'fa4',
                    'g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9', 'g10', 'g11', 'g12',
                    'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'grade11', 'grade12'
                ]
                query_parts = [f"name contains '{kw}'" for kw in exam_keywords]
                search_query = f"({' or '.join(query_parts)}) and trashed = false"
            else:
                search_query = f"name contains '{query}' and trashed = false"

            # Search for relevant file types
            search_query += " and (mimeType = 'application/pdf' or mimeType = 'application/vnd.google-apps.document' or mimeType = 'application/vnd.google-apps.spreadsheet' or mimeType = 'text/plain' or mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType = 'application/vnd.ms-excel')"

            results = drive_service.files().list(
                q=search_query,
                spaces='drive',
                fields='files(id, name, mimeType, modifiedTime, createdTime, size, webViewLink, shared)',
                orderBy='modifiedTime desc',
                pageSize=max_results
            ).execute()

            files = results.get('files', [])
            print(f"Found {len(files)} exam-related files for {admin_email}")

            # Add file type info for easier processing
            for file in files:
                file['file_type'] = self._get_file_type_display(file['mimeType'])

            return files

        except HttpError as e:
            error_msg = f"Drive API error: {e}"
            print(error_msg)
            if 'access_denied' in str(e).lower():
                print("Check if drive.readonly scope is authorized in Google Workspace Admin Console")
            return []
        except Exception as e:
            print(f"Error searching Drive files: {e}")
            return []

    def get_file_content(self, admin_email: str, file_id: str, file_metadata: Dict = None) -> Optional[str]:
        """Download and extract text content from a Drive file"""
        drive_service = self.get_drive_service(admin_email)
        if not drive_service:
            return None

        try:
            # Get file metadata if not provided
            if not file_metadata:
                file_metadata = drive_service.files().get(fileId=file_id).execute()

            mime_type = file_metadata.get('mimeType', '')
            file_name = file_metadata.get('name', 'Unknown')

            print(f"Extracting content from: {file_name} ({mime_type})")

            # Handle different file types
            if mime_type == 'application/vnd.google-apps.document':
                # Export Google Doc as plain text
                request = drive_service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
                content = self._download_content(request)

            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                # Export Google Sheet as CSV
                request = drive_service.files().export_media(
                    fileId=file_id,
                    mimeType='text/csv'
                )
                content = self._download_content(request)

            elif mime_type == 'application/pdf':
                # For PDFs, we need PyPDF2 (install with: pip install PyPDF2)
                request = drive_service.files().get_media(fileId=file_id)
                pdf_data = self._download_content(request, as_bytes=True)

                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
                    content = ""
                    for page in pdf_reader.pages:
                        content += page.extract_text() + "\n"
                except ImportError:
                    content = "PDF processing requires PyPDF2 library. Install with: pip install PyPDF2"
                except Exception as e:
                    content = f"Error reading PDF: {e}"

            else:
                # For other text files
                request = drive_service.files().get_media(fileId=file_id)
                content = self._download_content(request)

            if content and content.strip():
                print(f"Successfully extracted {len(content)} characters from {file_name}")
                return content.strip()
            else:
                print(f"No content extracted from {file_name}")
                return None

        except HttpError as e:
            print(f"Drive API error downloading {file_id}: {e}")
            return None
        except Exception as e:
            print(f"Error downloading file {file_id}: {e}")
            return None

    def _download_content(self, request, as_bytes: bool = False) -> Optional[Any]:
        """Download file content from Drive"""
        try:
            if as_bytes:
                file_content = io.BytesIO()
            else:
                file_content = io.BytesIO()

            downloader = MediaIoBaseDownload(file_content, request)
            done = False

            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"Download {int(status.progress() * 100)}%")

            file_content.seek(0)

            if as_bytes:
                return file_content.read()
            else:
                return file_content.read().decode('utf-8', errors='ignore')

        except Exception as e:
            print(f"Error downloading content: {e}")
            return None

    def _get_file_type_display(self, mime_type: str) -> str:
        """Get human-readable file type"""
        type_map = {
            'application/pdf': 'PDF',
            'application/vnd.google-apps.document': 'Google Doc',
            'application/vnd.google-apps.spreadsheet': 'Google Sheet',
            'text/plain': 'Text File',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word Doc',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel Sheet'
        }
        return type_map.get(mime_type, 'Unknown')

    def get_exam_info_from_files(self, admin_email: str, query: str = None, max_files: int = 5) -> List[Dict]:
        """Get exam information from files, including content extraction"""
        files = self.search_exam_files(admin_email, query, max_files)

        if not files:
            return []

        exam_info = []
        for file in files:
            file_id = file['id']
            file_name = file['name']

            # Extract content
            content = self.get_file_content(admin_email, file_id, file)

            exam_data = {
                'file_id': file_id,
                'file_name': file_name,
                'file_type': file.get('file_type', 'Unknown'),
                'modified_time': file.get('modifiedTime'),
                'shared': file.get('shared', False),
                'web_link': file.get('webViewLink'),
                'content': content,
                'content_length': len(content) if content else 0
            }

            exam_info.append(exam_data)

        return exam_info

    def search_files_by_url(self, admin_email: str, drive_url: str) -> Optional[Dict]:
        """Search for a specific file by Drive URL and extract content"""
        file_id = self._extract_file_id_from_url(drive_url)
        if not file_id:
            return None

        drive_service = self.get_drive_service(admin_email)
        if not drive_service:
            return None

        try:
            # Get file metadata
            file_metadata = drive_service.files().get(fileId=file_id).execute()

            # Extract content
            content = self.get_file_content(admin_email, file_id, file_metadata)

            return {
                'file_id': file_id,
                'file_name': file_metadata.get('name'),
                'file_type': self._get_file_type_display(file_metadata.get('mimeType', '')),
                'content': content,
                'web_link': file_metadata.get('webViewLink')
            }

        except Exception as e:
            print(f"Error accessing file from URL {drive_url}: {e}")
            return None

    def _extract_file_id_from_url(self, url: str) -> Optional[str]:
        """Extract file ID from Google Drive URL"""
        import re

        # Handle different Drive URL formats
        patterns = [
            r'/file/d/([a-zA-Z0-9-_]+)',  # /file/d/FILE_ID
            r'id=([a-zA-Z0-9-_]+)',       # id=FILE_ID
            r'/folders/([a-zA-Z0-9-_]+)', # /folders/FOLDER_ID
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None


