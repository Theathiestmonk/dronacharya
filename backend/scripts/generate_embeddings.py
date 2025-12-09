"""
Batch embedding generation script
Generates embeddings for all existing records in vectorized tables
"""
import os
import sys
import argparse
from typing import Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_search_service import VectorSearchService
from supabase_config import get_supabase_client

load_dotenv()


def generate_team_member_embeddings(service: VectorSearchService, supabase, limit: Optional[int] = None):
    """Generate embeddings for team_member_data records"""
    print("\n" + "=" * 60)
    print("Processing team_member_data")
    print("=" * 60)
    
    # Query records without embeddings
    query = supabase.table('team_member_data').select('*').eq('is_active', True).is_('embedding', 'null')
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    
    if not result.data:
        print("No records found without embeddings")
        return 0
    
    total = len(result.data)
    print(f"Found {total} records to process")
    
    success_count = 0
    error_count = 0
    
    for idx, row in enumerate(result.data, 1):
        try:
            # Combine relevant text fields
            name = row.get('name', '') or ''
            title = row.get('title', '') or ''
            description = row.get('description', '') or ''
            details = row.get('details', '') or ''
            full_content = row.get('full_content', '') or ''
            
            # Combine all text fields
            text = f"{name} {title} {description} {details} {full_content}".strip()
            
            if not text:
                print(f"[{idx}/{total}] Skipping {name}: No text content")
                continue
            
            # Generate embedding
            embedding = service.generate_embedding(text)
            
            # Update record
            supabase.table('team_member_data').update({
                'embedding': embedding
            }).eq('id', row['id']).execute()
            
            success_count += 1
            print(f"[{idx}/{total}] ✅ Generated embedding for: {name}")
            
        except Exception as e:
            error_count += 1
            print(f"[{idx}/{total}] ❌ Error processing {row.get('name', 'Unknown')}: {e}")
            continue
    
    print(f"\n✅ Success: {success_count}, ❌ Errors: {error_count}")
    return success_count


def generate_web_content_embeddings(service: VectorSearchService, supabase, limit: Optional[int] = None):
    """Generate embeddings for web_crawler_data records"""
    print("\n" + "=" * 60)
    print("Processing web_crawler_data")
    print("=" * 60)
    
    # Query records without embeddings
    query = supabase.table('web_crawler_data').select('*').eq('is_active', True).is_('embedding', 'null')
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    
    if not result.data:
        print("No records found without embeddings")
        return 0
    
    total = len(result.data)
    print(f"Found {total} records to process")
    
    success_count = 0
    error_count = 0
    
    for idx, row in enumerate(result.data, 1):
        try:
            # Combine relevant text fields
            title = row.get('title', '') or ''
            description = row.get('description', '') or ''
            main_content = (row.get('main_content', '') or '')[:8000]  # Limit to 8000 chars
            
            # Combine all text fields
            text = f"{title} {description} {main_content}".strip()
            
            if not text:
                print(f"[{idx}/{total}] Skipping {row.get('url', 'Unknown')}: No text content")
                continue
            
            # Generate embedding
            embedding = service.generate_embedding(text)
            
            # Update record
            supabase.table('web_crawler_data').update({
                'embedding': embedding
            }).eq('id', row['id']).execute()
            
            success_count += 1
            url = row.get('url', 'Unknown')
            print(f"[{idx}/{total}] ✅ Generated embedding for: {url[:60]}...")
            
        except Exception as e:
            error_count += 1
            print(f"[{idx}/{total}] ❌ Error processing {row.get('url', 'Unknown')}: {e}")
            continue
    
    print(f"\n✅ Success: {success_count}, ❌ Errors: {error_count}")
    return success_count


def generate_coursework_embeddings(service: VectorSearchService, supabase, limit: Optional[int] = None):
    """Generate embeddings for google_classroom_coursework records"""
    print("\n" + "=" * 60)
    print("Processing google_classroom_coursework")
    print("=" * 60)
    
    # Query records without embeddings
    query = supabase.table('google_classroom_coursework').select('*').is_('embedding', 'null')
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    
    if not result.data:
        print("No records found without embeddings")
        return 0
    
    total = len(result.data)
    print(f"Found {total} records to process")
    
    success_count = 0
    error_count = 0
    
    for idx, row in enumerate(result.data, 1):
        try:
            # Combine relevant text fields
            title = row.get('title', '') or ''
            description = (row.get('description', '') or '')[:8000]  # Limit to 8000 chars
            
            # Combine all text fields
            text = f"{title} {description}".strip()
            
            if not text:
                print(f"[{idx}/{total}] Skipping {title}: No text content")
                continue
            
            # Generate embedding
            embedding = service.generate_embedding(text)
            
            # Update record
            supabase.table('google_classroom_coursework').update({
                'embedding': embedding
            }).eq('id', row['id']).execute()
            
            success_count += 1
            print(f"[{idx}/{total}] ✅ Generated embedding for: {title[:60]}...")
            
        except Exception as e:
            error_count += 1
            print(f"[{idx}/{total}] ❌ Error processing {row.get('title', 'Unknown')}: {e}")
            continue
    
    print(f"\n✅ Success: {success_count}, ❌ Errors: {error_count}")
    return success_count


def generate_announcement_embeddings(service: VectorSearchService, supabase, limit: Optional[int] = None):
    """Generate embeddings for google_classroom_announcements records"""
    print("\n" + "=" * 60)
    print("Processing google_classroom_announcements")
    print("=" * 60)
    
    # Query records without embeddings
    query = supabase.table('google_classroom_announcements').select('*').is_('embedding', 'null')
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    
    if not result.data:
        print("No records found without embeddings")
        return 0
    
    total = len(result.data)
    print(f"Found {total} records to process")
    
    success_count = 0
    error_count = 0
    
    for idx, row in enumerate(result.data, 1):
        try:
            # Get announcement text
            text = (row.get('text', '') or '').strip()
            
            if not text:
                print(f"[{idx}/{total}] Skipping announcement {row.get('id', 'Unknown')}: No text content")
                continue
            
            # Limit text length
            text = text[:8000]
            
            # Generate embedding
            embedding = service.generate_embedding(text)
            
            # Update record
            supabase.table('google_classroom_announcements').update({
                'embedding': embedding
            }).eq('id', row['id']).execute()
            
            success_count += 1
            preview = text[:60].replace('\n', ' ')
            print(f"[{idx}/{total}] ✅ Generated embedding for: {preview}...")
            
        except Exception as e:
            error_count += 1
            print(f"[{idx}/{total}] ❌ Error processing announcement: {e}")
            continue
    
    print(f"\n✅ Success: {success_count}, ❌ Errors: {error_count}")
    return success_count


def main():
    """Main function to generate embeddings for all tables"""
    parser = argparse.ArgumentParser(description='Generate embeddings for vectorized tables')
    parser.add_argument(
        '--table',
        choices=['team_member_data', 'web_crawler_data', 'google_classroom_coursework', 
                 'google_classroom_announcements', 'all'],
        default='all',
        help='Table to process (default: all)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of records to process (for testing)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Batch Embedding Generation Script")
    print("=" * 60)
    
    try:
        service = VectorSearchService()
        supabase = get_supabase_client()
        
        total_success = 0
        
        if args.table == 'all' or args.table == 'team_member_data':
            total_success += generate_team_member_embeddings(service, supabase, args.limit)
        
        if args.table == 'all' or args.table == 'web_crawler_data':
            total_success += generate_web_content_embeddings(service, supabase, args.limit)
        
        if args.table == 'all' or args.table == 'google_classroom_coursework':
            total_success += generate_coursework_embeddings(service, supabase, args.limit)
        
        if args.table == 'all' or args.table == 'google_classroom_announcements':
            total_success += generate_announcement_embeddings(service, supabase, args.limit)
        
        print("\n" + "=" * 60)
        print(f"✅ Total embeddings generated: {total_success}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()





















