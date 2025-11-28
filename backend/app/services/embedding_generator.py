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


# Singleton instance
_embedding_generator = None

def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create singleton instance of EmbeddingGenerator"""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator





