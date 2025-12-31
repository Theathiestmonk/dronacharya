"""
Embedding Generator Service
Automatically generates embeddings for new records in vectorized tables
"""
from typing import Optional
from app.services.vector_search_service import VectorSearchService
from supabase_config import get_supabase_client


class EmbeddingGenerator:
    """Service to automatically generate embeddings for new records"""
    
    def __init__(self):
        """Initialize the embedding generator"""
        self.vector_service = VectorSearchService()
        self.supabase = get_supabase_client()
    
    def generate_for_web_crawler(self, record_id: str) -> bool:
        """
        Generate embedding for a web_crawler_data record
        
        Args:
            record_id: UUID of the record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('web_crawler_data').select('*').eq('id', record_id).single().execute()
            
            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in web_crawler_data")
                return False
            
            row = result.data
            
            # Combine relevant text fields
            title = row.get('title', '') or ''
            description = row.get('description', '') or ''
            main_content = (row.get('main_content', '') or '')[:8000]  # Limit to 8000 chars
            
            text = f"{title} {description} {main_content}".strip()
            
            if not text:
                print(f"[EmbeddingGenerator] No text content for web_crawler_data record {record_id}")
                return False
            
            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)
            
            # Update record
            self.supabase.table('web_crawler_data').update({
                'embedding': embedding
            }).eq('id', record_id).execute()
            
            print(f"[EmbeddingGenerator] ✅ Generated embedding for web_crawler_data: {row.get('url', record_id)}")
            return True
            
        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for web_crawler_data {record_id}: {e}")
            return False
    
    def generate_for_team_member(self, record_id: str) -> bool:
        """
        Generate embedding for a team_member_data record
        
        Args:
            record_id: UUID of the record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('team_member_data').select('*').eq('id', record_id).single().execute()
            
            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in team_member_data")
                return False
            
            row = result.data
            
            # Combine relevant text fields
            name = row.get('name', '') or ''
            title = row.get('title', '') or ''
            description = row.get('description', '') or ''
            details = row.get('details', '') or ''
            full_content = row.get('full_content', '') or ''
            
            text = f"{name} {title} {description} {details} {full_content}".strip()
            
            if not text:
                print(f"[EmbeddingGenerator] No text content for team_member_data record {record_id}")
                return False
            
            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)
            
            # Update record
            self.supabase.table('team_member_data').update({
                'embedding': embedding
            }).eq('id', record_id).execute()
            
            print(f"[EmbeddingGenerator] ✅ Generated embedding for team_member: {name}")
            return True
            
        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for team_member_data {record_id}: {e}")
            return False
    
    def generate_for_coursework(self, record_id: str) -> bool:
        """
        Generate embedding for a google_classroom_coursework record
        
        Args:
            record_id: UUID of the record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('google_classroom_coursework').select('*').eq('id', record_id).single().execute()
            
            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in google_classroom_coursework")
                return False
            
            row = result.data
            
            # Combine relevant text fields
            title = row.get('title', '') or ''
            description = (row.get('description', '') or '')[:8000]  # Limit to 8000 chars
            
            text = f"{title} {description}".strip()
            
            if not text:
                print(f"[EmbeddingGenerator] No text content for coursework record {record_id}")
                return False
            
            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)
            
            # Update record
            self.supabase.table('google_classroom_coursework').update({
                'embedding': embedding
            }).eq('id', record_id).execute()
            
            print(f"[EmbeddingGenerator] ✅ Generated embedding for coursework: {title[:60]}...")
            return True
            
        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for coursework {record_id}: {e}")
            return False
    
    def generate_for_announcement(self, record_id: str) -> bool:
        """
        Generate embedding for a google_classroom_announcements record
        
        Args:
            record_id: UUID of the record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('google_classroom_announcements').select('*').eq('id', record_id).single().execute()
            
            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in google_classroom_announcements")
                return False
            
            row = result.data
            
            # Get announcement text
            text = (row.get('text', '') or '').strip()
            
            if not text:
                print(f"[EmbeddingGenerator] No text content for announcement record {record_id}")
                return False
            
            # Limit text length
            text = text[:8000]
            
            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)
            
            # Update record
            self.supabase.table('google_classroom_announcements').update({
                'embedding': embedding
            }).eq('id', record_id).execute()
            
            preview = text[:60].replace('\n', ' ')
            print(f"[EmbeddingGenerator] ✅ Generated embedding for announcement: {preview}...")
            return True
            
        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for announcement {record_id}: {e}")
            return False

    def generate_for_course(self, record_id: str) -> bool:
        """
        Generate embedding for a google_classroom_courses record

        Args:
            record_id: UUID of the record

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('google_classroom_courses').select('*').eq('id', record_id).single().execute()

            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in google_classroom_courses")
                return False

            row = result.data

            # Combine relevant text fields
            name = row.get('name', '') or ''
            description = row.get('description', '') or ''
            section = row.get('section', '') or ''
            room = row.get('room', '') or ''

            text = f"{name} {description} {section} {room}".strip()

            if not text:
                print(f"[EmbeddingGenerator] No text content for course record {record_id}")
                return False

            # Limit text length
            text = text[:8000]

            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)

            # Update record
            self.supabase.table('google_classroom_courses').update({
                'embedding': embedding
            }).eq('id', record_id).execute()

            preview = text[:60].replace('\n', ' ')
            print(f"[EmbeddingGenerator] ✅ Generated embedding for course: {preview}...")
            return True

        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for course {record_id}: {e}")
            return False

    def generate_for_teacher(self, record_id: str) -> bool:
        """
        Generate embedding for a google_classroom_teachers record

        Args:
            record_id: UUID of the record

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('google_classroom_teachers').select('*').eq('id', record_id).single().execute()

            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in google_classroom_teachers")
                return False

            row = result.data

            # Get profile information
            profile = row.get('profile', {}) or {}
            name = profile.get('name', {}).get('fullName', '') or ''
            email = profile.get('emailAddress', '') or ''

            text = f"{name} {email}".strip()

            if not text:
                print(f"[EmbeddingGenerator] No text content for teacher record {record_id}")
                return False

            # Limit text length
            text = text[:8000]

            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)

            # Update record
            self.supabase.table('google_classroom_teachers').update({
                'embedding': embedding
            }).eq('id', record_id).execute()

            preview = text[:60].replace('\n', ' ')
            print(f"[EmbeddingGenerator] ✅ Generated embedding for teacher: {preview}...")
            return True

        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for teacher {record_id}: {e}")
            return False

    def generate_for_student(self, record_id: str) -> bool:
        """
        Generate embedding for a google_classroom_students record

        Args:
            record_id: UUID of the record

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('google_classroom_students').select('*').eq('id', record_id).single().execute()

            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in google_classroom_students")
                return False

            row = result.data

            # Get profile information
            profile = row.get('profile', {}) or {}
            name = profile.get('name', {}).get('fullName', '') or ''
            email = profile.get('emailAddress', '') or ''

            text = f"{name} {email}".strip()

            if not text:
                print(f"[EmbeddingGenerator] No text content for student record {record_id}")
                return False

            # Limit text length
            text = text[:8000]

            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)

            # Update record
            self.supabase.table('google_classroom_students').update({
                'embedding': embedding
            }).eq('id', record_id).execute()

            preview = text[:60].replace('\n', ' ')
            print(f"[EmbeddingGenerator] ✅ Generated embedding for student: {preview}...")
            return True

        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for student {record_id}: {e}")
            return False

    def generate_for_submission(self, record_id: str) -> bool:
        """
        Generate embedding for a google_classroom_submissions record

        Args:
            record_id: UUID of the record

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('google_classroom_submissions').select('*').eq('id', record_id).single().execute()

            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in google_classroom_submissions")
                return False

            row = result.data

            # Get submission content (if any text content exists)
            # Submissions might not have much text, but we can include state and other metadata
            state = row.get('state', '') or ''
            course_work_type = row.get('course_work_type', '') or ''

            text = f"Submission state: {state} Type: {course_work_type}".strip()

            if not text or text == "Submission state:  Type: ":
                print(f"[EmbeddingGenerator] No meaningful content for submission record {record_id}")
                return False

            # Limit text length
            text = text[:8000]

            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)

            # Update record
            self.supabase.table('google_classroom_submissions').update({
                'embedding': embedding
            }).eq('id', record_id).execute()

            preview = text[:60].replace('\n', ' ')
            print(f"[EmbeddingGenerator] ✅ Generated embedding for submission: {preview}...")
            return True

        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for submission {record_id}: {e}")
            return False

    def generate_for_calendar_event(self, record_id: str) -> bool:
        """
        Generate embedding for a google_calendar_events record

        Args:
            record_id: UUID of the record

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('google_calendar_events').select('*').eq('id', record_id).single().execute()

            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in google_calendar_events")
                return False

            row = result.data

            # Combine relevant text fields
            summary = row.get('summary', '') or ''
            description = row.get('description', '') or ''
            location = row.get('location', '') or ''

            text = f"{summary} {description} {location}".strip()

            if not text:
                print(f"[EmbeddingGenerator] No text content for calendar event record {record_id}")
                return False

            # Limit text length
            text = text[:8000]

            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)

            # Update record
            self.supabase.table('google_calendar_events').update({
                'embedding': embedding
            }).eq('id', record_id).execute()

            preview = text[:60].replace('\n', ' ')
            print(f"[EmbeddingGenerator] ✅ Generated embedding for calendar event: {preview}...")
            return True

        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for calendar event {record_id}: {e}")
            return False

    def generate_for_calendar(self, record_id: str) -> bool:
        """
        Generate embedding for a google_calendar_calendars record

        Args:
            record_id: UUID of the record

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('google_calendar_calendars').select('*').eq('id', record_id).single().execute()

            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in google_calendar_calendars")
                return False

            row = result.data

            # Combine relevant text fields
            summary = row.get('summary', '') or ''
            description = row.get('description', '') or ''

            text = f"{summary} {description}".strip()

            if not text:
                print(f"[EmbeddingGenerator] No text content for calendar record {record_id}")
                return False

            # Limit text length
            text = text[:8000]

            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)

            # Update record
            self.supabase.table('google_calendar_calendars').update({
                'embedding': embedding
            }).eq('id', record_id).execute()

            preview = text[:60].replace('\n', ' ')
            print(f"[EmbeddingGenerator] ✅ Generated embedding for calendar: {preview}...")
            return True

        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for calendar {record_id}: {e}")
            return False

    def generate_for_user_profile(self, record_id: str) -> bool:
        """
        Generate embedding for a user_profiles record

        Args:
            record_id: UUID of the record

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the record
            result = self.supabase.table('user_profiles').select('*').eq('id', record_id).single().execute()

            if not result.data:
                print(f"[EmbeddingGenerator] Record {record_id} not found in user_profiles")
                return False

            row = result.data

            # Combine relevant text fields
            first_name = row.get('first_name', '') or ''
            last_name = row.get('last_name', '') or ''
            email = row.get('email', '') or ''
            bio = row.get('bio', '') or ''
            role = row.get('role', '') or ''
            grade = row.get('grade', '') or ''

            text = f"{first_name} {last_name} {email} {bio} {role} {grade}".strip()

            if not text:
                print(f"[EmbeddingGenerator] No text content for user profile record {record_id}")
                return False

            # Limit text length
            text = text[:8000]

            # Generate embedding
            embedding = self.vector_service.generate_embedding(text)

            # Update record
            self.supabase.table('user_profiles').update({
                'embedding': embedding
            }).eq('id', record_id).execute()

            preview = text[:60].replace('\n', ' ')
            print(f"[EmbeddingGenerator] ✅ Generated embedding for user profile: {preview}...")
            return True

        except Exception as e:
            print(f"[EmbeddingGenerator] ❌ Error generating embedding for user profile {record_id}: {e}")
            return False

    def regenerate_all_embeddings(self) -> dict:
        """
        Regenerate embeddings for all records across all tables that support embeddings

        Returns:
            Dictionary with counts of processed records per table
        """
        results = {
            'web_crawler_data': 0,
            'team_member_data': 0,
            'google_classroom_courses': 0,
            'google_classroom_teachers': 0,
            'google_classroom_students': 0,
            'google_classroom_coursework': 0,
            'google_classroom_submissions': 0,
            'google_classroom_announcements': 0,
            'google_calendar_calendars': 0,
            'google_calendar_events': 0,
            'user_profiles': 0,
            'errors': 0
        }

        tables_and_methods = [
            ('web_crawler_data', self.generate_for_web_crawler),
            ('team_member_data', self.generate_for_team_member),
            ('google_classroom_courses', self.generate_for_course),
            ('google_classroom_teachers', self.generate_for_teacher),
            ('google_classroom_students', self.generate_for_student),
            ('google_classroom_coursework', self.generate_for_coursework),
            ('google_classroom_submissions', self.generate_for_submission),
            ('google_classroom_announcements', self.generate_for_announcement),
            ('google_calendar_calendars', self.generate_for_calendar),
            ('google_calendar_events', self.generate_for_calendar_event),
            ('user_profiles', self.generate_for_user_profile),
        ]

        for table_name, method in tables_and_methods:
            try:
                print(f"[EmbeddingGenerator] 🔄 Regenerating embeddings for {table_name}...")

                # Get all records for this table
                records = self.supabase.table(table_name).select('id').execute()

                if records.data:
                    for record in records.data:
                        record_id = record['id']
                        try:
                            success = method(str(record_id))
                            if success:
                                results[table_name] += 1
                        except Exception as e:
                            print(f"[EmbeddingGenerator] ❌ Error regenerating embedding for {table_name} record {record_id}: {e}")
                            results['errors'] += 1

                print(f"[EmbeddingGenerator] ✅ Completed {table_name}: {results[table_name]} embeddings generated")

            except Exception as e:
                print(f"[EmbeddingGenerator] ❌ Error processing table {table_name}: {e}")
                results['errors'] += 1

        print(f"[EmbeddingGenerator] 🎉 Embedding regeneration complete!")
        print(f"[EmbeddingGenerator] 📊 Total embeddings generated: {sum(results.values()) - results['errors']}")
        print(f"[EmbeddingGenerator] ❌ Total errors: {results['errors']}")

        return results


# Singleton instance
_embedding_generator = None

def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create singleton instance of EmbeddingGenerator"""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator





















