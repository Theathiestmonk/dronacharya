import os
import json
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class WebCrawlerCacheManager:
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and Service Role Key must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Local SQLite database for caching
        self.cache_db_path = Path("web_crawler_cache.db")
        self.init_local_cache()
        
        # Cache settings
        self.cache_duration_hours = 24  # 24 hours cache
        self.max_cache_size = 1000  # Maximum number of cached items
        
    def init_local_cache(self):
        """Initialize local SQLite cache database"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Create cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS web_crawler_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT UNIQUE NOT NULL,
                    query_text TEXT NOT NULL,
                    content_type TEXT,
                    results TEXT NOT NULL, -- JSON string
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_query_hash ON web_crawler_cache(query_hash)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_expires_at ON web_crawler_cache(expires_at)
            ''')
            
            conn.commit()
            conn.close()
            
            print("[CacheManager] Local cache database initialized")
            
        except Exception as e:
            print(f"[CacheManager] Error initializing local cache: {e}")
    
    def get_query_hash(self, query: str) -> str:
        """Generate hash for query caching"""
        return hashlib.md5(query.lower().encode()).hexdigest()
    
    def is_cache_valid(self, expires_at: str) -> bool:
        """Check if cache entry is still valid"""
        try:
            expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            return datetime.now() < expires
        except:
            return False
    
    def get_from_local_cache(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get data from local cache if available and valid"""
        try:
            query_hash = self.get_query_hash(query)
            
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT results, expires_at FROM web_crawler_cache 
                WHERE query_hash = ? AND expires_at > CURRENT_TIMESTAMP
            ''', (query_hash,))
            
            result = cursor.fetchone()
            
            if result:
                results_json, expires_at = result
                results = json.loads(results_json)
                
                # Update access count and last accessed
                cursor.execute('''
                    UPDATE web_crawler_cache 
                    SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP
                    WHERE query_hash = ?
                ''', (query_hash,))
                
                conn.commit()
                conn.close()
                
                print(f"[CacheManager] Found valid cache for query: {query}")
                return results
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"[CacheManager] Error getting from local cache: {e}")
            return None
    
    def store_in_local_cache(self, query: str, results: List[Dict[str, Any]], content_type: str = None) -> bool:
        """Store data in local cache"""
        try:
            query_hash = self.get_query_hash(query)
            expires_at = datetime.now() + timedelta(hours=self.cache_duration_hours)
            
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Insert or replace cache entry
            cursor.execute('''
                INSERT OR REPLACE INTO web_crawler_cache 
                (query_hash, query_text, content_type, results, expires_at, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            ''', (query_hash, query, content_type, json.dumps(results), expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            
            print(f"[CacheManager] Stored in local cache: {query}")
            return True
            
        except Exception as e:
            print(f"[CacheManager] Error storing in local cache: {e}")
            return False
    
    def get_from_supabase(self, query: str) -> List[Dict[str, Any]]:
        """Get data from Supabase database"""
        try:
            # Extract keywords from query
            keywords = self.extract_keywords_from_query(query)
            
            # Search using the stored function
            result = self.supabase.rpc('search_crawler_content', {'p_keywords': keywords}).execute()
            
            if result.data:
                print(f"[CacheManager] Found {len(result.data)} results from Supabase for query: {query}")
                return result.data
            
            return []
            
        except Exception as e:
            print(f"[CacheManager] Error getting from Supabase: {e}")
            return []
    
    def get_fresh_data_from_supabase(self, content_type: str = None) -> List[Dict[str, Any]]:
        """Get fresh data (crawled today) from Supabase"""
        try:
            result = self.supabase.rpc('get_fresh_crawler_data', {'p_content_type': content_type}).execute()
            
            if result.data:
                print(f"[CacheManager] Found {len(result.data)} fresh results from Supabase")
                return result.data
            
            return []
            
        except Exception as e:
            print(f"[CacheManager] Error getting fresh data from Supabase: {e}")
            return []
    
    def extract_keywords_from_query(self, query: str) -> List[str]:
        """Extract relevant keywords from user query"""
        query_lower = query.lower()
        keywords = []
        
        # Add query words as keywords
        words = query_lower.split()
        keywords.extend([word for word in words if len(word) > 2])
        
        # Add specific keyword mappings
        keyword_mappings = {
            'team': ['team', 'staff', 'faculty', 'teacher', 'member'],
            'calendar': ['calendar', 'event', 'holiday', 'schedule'],
            'news': ['news', 'latest', 'recent', 'update'],
            'article': ['article', 'philosophy', 'roots', 'learning'],
            'academic': ['academic', 'curriculum', 'program', 'igcse'],
            'admission': ['admission', 'fee', 'apply', 'enroll'],
            'contact': ['contact', 'location', 'address', 'phone'],
            'testimonial': ['testimonial', 'parent', 'feedback', 'review']
        }
        
        for category, category_keywords in keyword_mappings.items():
            if any(keyword in query_lower for keyword in category_keywords):
                keywords.extend(category_keywords)
        
        return list(set(keywords))  # Remove duplicates
    
    def get_enhanced_response(self, query: str) -> str:
        """Get enhanced response using local cache first, then Supabase"""
        print(f"[CacheManager] Getting enhanced response for: {query}")
        
        # Try local cache first
        cached_results = self.get_from_local_cache(query)
        
        if cached_results:
            print(f"[CacheManager] Using cached data for query: {query}")
            return self.format_search_results(cached_results, query)
        
        # If not in cache, get from Supabase
        print(f"[CacheManager] Cache miss, fetching from Supabase for query: {query}")
        supabase_results = self.get_from_supabase(query)
        
        if supabase_results:
            # Store in local cache for future use
            self.store_in_local_cache(query, supabase_results)
            return self.format_search_results(supabase_results, query)
        
        # If no data found anywhere, return helpful message
        return f"""## Information Not Available

I'm sorry, but the information you're looking for is not currently available in our stored data. 

Our system crawls the website daily to keep information fresh. Please try again later or contact us directly for more information.

*Source: [prakriti.edu.in](https://prakriti.edu.in)*"""
    
    def format_search_results(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format search results for display"""
        if not results:
            return ""
        
        formatted_info = "## Web Search Results\n\n"
        
        for i, result in enumerate(results[:5]):  # Limit to top 5 results
            formatted_info += f"### Result {i+1}\n"
            
            if result.get('title'):
                formatted_info += f"**Title**: {result['title']}\n"
            
            if result.get('description'):
                formatted_info += f"**Description**: {result['description'][:200]}...\n"
            
            if result.get('main_content'):
                # Extract relevant sentences
                sentences = result['main_content'].split('.')
                relevant_sentences = []
                query_words = query.lower().split()
                
                for sentence in sentences:
                    sentence_lower = sentence.lower()
                    if any(word in sentence_lower for word in query_words):
                        relevant_sentences.append(sentence.strip())
                
                if relevant_sentences:
                    formatted_info += f"**Relevant Content**: {' '.join(relevant_sentences[:3])}\n"
            
            if result.get('url'):
                formatted_info += f"*Source: [{result['url']}]({result['url']})*\n\n"
        
        return formatted_info
    
    def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Delete expired entries
            cursor.execute('DELETE FROM web_crawler_cache WHERE expires_at < CURRENT_TIMESTAMP')
            deleted_count = cursor.rowcount
            
            # If cache is too large, delete oldest entries
            cursor.execute('SELECT COUNT(*) FROM web_crawler_cache')
            count = cursor.fetchone()[0]
            
            if count > self.max_cache_size:
                excess = count - self.max_cache_size
                cursor.execute('''
                    DELETE FROM web_crawler_cache 
                    WHERE id IN (
                        SELECT id FROM web_crawler_cache 
                        ORDER BY last_accessed ASC 
                        LIMIT ?
                    )
                ''', (excess,))
                deleted_count += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"[CacheManager] Cleaned up {deleted_count} expired cache entries")
            
        except Exception as e:
            print(f"[CacheManager] Error cleaning up cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            conn = sqlite3.connect(self.cache_db_path)
            cursor = conn.cursor()
            
            # Total entries
            cursor.execute('SELECT COUNT(*) FROM web_crawler_cache')
            total_entries = cursor.fetchone()[0]
            
            # Valid entries
            cursor.execute('SELECT COUNT(*) FROM web_crawler_cache WHERE expires_at > CURRENT_TIMESTAMP')
            valid_entries = cursor.fetchone()[0]
            
            # Most accessed queries
            cursor.execute('''
                SELECT query_text, access_count 
                FROM web_crawler_cache 
                ORDER BY access_count DESC 
                LIMIT 5
            ''')
            top_queries = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'expired_entries': total_entries - valid_entries,
                'top_queries': top_queries
            }
            
        except Exception as e:
            print(f"[CacheManager] Error getting cache stats: {e}")
            return {}

# Global instance
cache_manager = WebCrawlerCacheManager()

def get_web_enhanced_response(query: str) -> str:
    """Get web-enhanced response using cache manager"""
    try:
        return cache_manager.get_enhanced_response(query)
    except Exception as e:
        print(f"[CacheManager] Error getting enhanced response: {e}")
        return ""

def cleanup_cache():
    """Clean up expired cache entries"""
    try:
        cache_manager.cleanup_expired_cache()
    except Exception as e:
        print(f"[CacheManager] Error cleaning up cache: {e}")

def get_cache_stats():
    """Get cache statistics"""
    try:
        return cache_manager.get_cache_stats()
    except Exception as e:
        print(f"[CacheManager] Error getting cache stats: {e}")
        return {}
