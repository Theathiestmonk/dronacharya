"""
Vector Search Service for semantic similarity search using sentence-transformers embeddings and pgvector
"""
import os
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from supabase_config import get_supabase_client
from dotenv import load_dotenv

load_dotenv()


class VectorSearchService:
    """Service for generating embeddings and performing semantic similarity search"""

    def __init__(self):
        """Initialize the vector search service"""
        self.supabase = get_supabase_client()
        # Use sentence-transformers/all-MiniLM-L6-v2 for 384 dimensions (matches database schema)
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.embedding_dimension = 384
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using sentence-transformers

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            # Generate embedding using sentence-transformers
            embedding = self.embedding_model.encode(text.strip())
            return embedding.tolist()  # Convert numpy array to list
        except Exception as e:
            print(f"[VectorSearch] Error generating embedding: {e}")
            raise
    
    def search_web_content(
        self, 
        query: str, 
        limit: int = 5, 
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Semantic search in web_crawler_data table
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching web content records with similarity scores
        """
        try:
            query_embedding = self.generate_embedding(query)
            
            result = self.supabase.rpc(
                'match_web_content',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': threshold,
                    'match_count': limit
                }
            ).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"[VectorSearch] Error searching web content: {e}")
            return []
    
    def search_team_members(
        self, 
        query: str, 
        limit: int = 5, 
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Semantic search in team_member_data table
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching team member records with similarity scores
        """
        try:
            query_embedding = self.generate_embedding(query)
            
            result = self.supabase.rpc(
                'match_team_members',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': threshold,
                    'match_count': limit
                }
            ).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"[VectorSearch] Error searching team members: {e}")
            return []
    
    def search_coursework(
        self, 
        query: str, 
        limit: int = 5, 
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Semantic search in google_classroom_coursework table
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching coursework records with similarity scores
        """
        try:
            query_embedding = self.generate_embedding(query)
            
            result = self.supabase.rpc(
                'match_coursework',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': threshold,
                    'match_count': limit
                }
            ).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"[VectorSearch] Error searching coursework: {e}")
            return []
    
    def search_announcements(
        self, 
        query: str, 
        limit: int = 5, 
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Semantic search in google_classroom_announcements table
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching announcement records with similarity scores
        """
        try:
            query_embedding = self.generate_embedding(query)
            
            result = self.supabase.rpc(
                'match_announcements',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': threshold,
                    'match_count': limit
                }
            ).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"[VectorSearch] Error searching announcements: {e}")
            return []
    
    def search_all(
        self, 
        query: str, 
        limit_per_table: int = 3,
        threshold: float = 0.7
    ) -> Dict[str, List[Dict]]:
        """
        Search across all vectorized tables
        
        Args:
            query: Search query text
            limit_per_table: Maximum results per table
            threshold: Minimum similarity score (0-1)
            
        Returns:
            Dictionary with results from each table:
            {
                'web_content': [...],
                'team_members': [...],
                'coursework': [...],
                'announcements': [...]
            }
        """
        return {
            'web_content': self.search_web_content(query, limit_per_table, threshold),
            'team_members': self.search_team_members(query, limit_per_table, threshold),
            'coursework': self.search_coursework(query, limit_per_table, threshold),
            'announcements': self.search_announcements(query, limit_per_table, threshold)
        }


# Singleton instance
_vector_search_service = None

def get_vector_search_service() -> VectorSearchService:
    """Get or create singleton instance of VectorSearchService"""
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService()
    return _vector_search_service





















