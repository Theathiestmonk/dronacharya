"""
Cleanup script - Removes non-essential pages from database
Run this once to clean up existing database
"""

import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config.essential_pages import ESSENTIAL_PRAKRITI_PAGES
from supabase_config import get_supabase_client

load_dotenv()

def cleanup_non_essential_pages():
    """Remove all non-essential pages from web_crawler_data table"""
    print("=" * 60)
    print("🧹 Cleaning Up Non-Essential Pages")
    print("=" * 60)
    
    supabase = get_supabase_client()
    
    if not supabase:
        print("❌ Error: Supabase client not available")
        return
    
    try:
        # Get all pages from database
        all_pages = supabase.table('web_crawler_data')\
            .select('id, url, title')\
            .eq('is_active', True)\
            .execute()
        
        if not all_pages.data:
            print("✅ No pages found in database")
            return
        
        print(f"📊 Found {len(all_pages.data)} pages in database")
        
        # Find non-essential pages
        essential_urls_set = set(ESSENTIAL_PRAKRITI_PAGES)
        non_essential_pages = [
            page for page in all_pages.data 
            if page['url'] not in essential_urls_set
        ]
        
        if not non_essential_pages:
            print("✅ All pages are essential - no cleanup needed")
            return
        
        print(f"🗑️  Found {len(non_essential_pages)} non-essential pages to remove")
        
        # Show what will be deleted
        print("\n📋 Pages to be removed:")
        for page in non_essential_pages[:10]:  # Show first 10
            print(f"   - {page['url']}")
        if len(non_essential_pages) > 10:
            print(f"   ... and {len(non_essential_pages) - 10} more")
        
        # Confirm deletion
        response = input("\n❓ Delete these pages? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cleanup cancelled")
            return
        
        # Mark as inactive (soft delete)
        non_essential_ids = [page['id'] for page in non_essential_pages]
        
        for page_id in non_essential_ids:
            supabase.table('web_crawler_data')\
                .update({'is_active': False})\
                .eq('id', page_id)\
                .execute()
        
        print(f"\n✅ Successfully removed {len(non_essential_pages)} non-essential pages")
        print(f"📊 Remaining essential pages: {len(all_pages.data) - len(non_essential_pages)}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_non_essential_pages()








