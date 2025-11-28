"""
Daily crawl script - Only crawls essential pages (10 pages instead of 100+)
Run this daily to keep essential pages fresh in the database
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.web_crawler_agent import WebCrawlerAgent
from app.config.essential_pages import ESSENTIAL_PRAKRITI_PAGES, PAGE_CONTENT_TYPES
from supabase_config import get_supabase_client
from app.services.embedding_generator import get_embedding_generator

load_dotenv()

def crawl_essential_pages():
    """Crawl only essential pages and store in database"""
    print("=" * 60)
    print("Starting Essential Pages Crawl")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Pages to crawl: {len(ESSENTIAL_PRAKRITI_PAGES)}")
    print("=" * 60)
    
    crawler = WebCrawlerAgent()
    supabase = get_supabase_client()
    
    if not supabase:
        print("[ERROR] Error: Supabase client not available")
        return
    
    crawled_count = 0
    error_count = 0
    
    for url in ESSENTIAL_PRAKRITI_PAGES:
        try:
            print(f"\nCrawling: {url}")
            
                # Extract content - SKIP link following to only crawl essential pages
                content = crawler.extract_content_from_url(url, query="", skip_link_following=True)
            
            if 'error' in content:
                print(f"[ERROR] Error crawling {url}: {content['error']}")
                error_count += 1
                continue
            
            # Get content type
            content_type = PAGE_CONTENT_TYPES.get(url, 'general')
            
            # Extract keywords from content
            keywords = []
            if content.get('title'):
                keywords.extend(content['title'].lower().split()[:5])
            if content.get('description'):
                keywords.extend(content['description'].lower().split()[:5])
            
            # Prepare data for database
            cache_data = {
                'url': url,
                'title': content.get('title', ''),
                'description': content.get('description', ''),
                'main_content': content.get('main_content', '')[:50000],  # Limit size
                'headings': content.get('headings', []),
                'links': content.get('links', [])[:50],  # Limit links
                'content_type': content_type,
                'query_keywords': list(set(keywords))[:10],  # Limit to 10 keywords
                'relevance_score': len(keywords),
                'is_active': True
            }
            
            # Store in database
            # First, check if record exists for this URL (most recent active record)
            existing = supabase.table('web_crawler_data').select('id').eq('url', url).eq('is_active', True).order('crawled_at', desc=True).limit(1).execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing record (keep same ID and crawled_date, but update content and crawled_at)
                record_id = existing.data[0]['id']
                # Don't update crawled_date - keep the original date
                # Only update the content and timestamps
                update_data = {
                    'title': cache_data['title'],
                    'description': cache_data['description'],
                    'main_content': cache_data['main_content'],
                    'headings': cache_data['headings'],
                    'links': cache_data['links'],
                    'content_type': cache_data['content_type'],
                    'query_keywords': cache_data['query_keywords'],
                    'relevance_score': cache_data['relevance_score'],
                    'crawled_at': datetime.now().isoformat(),  # Update timestamp
                    'updated_at': datetime.now().isoformat()
                }
                result = supabase.table('web_crawler_data').update(update_data).eq('id', record_id).execute()
                # Get the updated record
                updated_record = supabase.table('web_crawler_data').select('*').eq('id', record_id).single().execute()
                result.data = [updated_record.data] if updated_record.data else []
                print(f"[UPDATE] Updated existing record for: {url}")
            else:
                # Insert new record (only if no existing record found)
                result = supabase.table('web_crawler_data').insert(cache_data).select('id').execute()
                print(f"[INSERT] Created new record for: {url}")
            
            # Generate embedding for the new/updated record
            if result.data and len(result.data) > 0:
                record_id = result.data[0].get('id')
                if record_id:
                    try:
                        embedding_gen = get_embedding_generator()
                        embedding_gen.generate_for_web_crawler(record_id)
                    except Exception as e:
                        print(f"[WARNING] Failed to generate embedding: {e}")
            
            crawled_count += 1
            print(f"[OK] Successfully crawled and stored: {url}")
            print(f"   Content type: {content_type}")
            print(f"   Keywords: {len(cache_data['query_keywords'])}")
            
            # Small delay to avoid overwhelming server
            time.sleep(1)
            
        except Exception as e:
            print(f"[ERROR] Error processing {url}: {str(e)}")
            error_count += 1
            continue
    
    print("\n" + "=" * 60)
    print("Crawl Summary")
    print("=" * 60)
    print(f"[OK] Successfully crawled: {crawled_count} pages")
    print(f"[ERROR] Errors: {error_count} pages")
    print(f"Total pages: {len(ESSENTIAL_PRAKRITI_PAGES)}")
    print("=" * 60)

if __name__ == "__main__":
    crawl_essential_pages()

