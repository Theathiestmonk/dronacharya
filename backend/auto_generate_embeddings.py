#!/usr/bin/env python3
"""
Automatic embedding generation for all tables
Checks for records without embeddings and generates them
"""
from supabase_config import get_supabase_client
from app.services.embedding_generator import EmbeddingGenerator

def auto_generate_embeddings():
    """
    Automatically generate embeddings for any records that don't have them
    """
    supabase = get_supabase_client()
    if not supabase:
        print("Could not connect to Supabase")
        return

    embedding_gen = EmbeddingGenerator()
    total_processed = 0

    # Tables to check for missing embeddings
    tables_to_check = [
        ('google_classroom_coursework', 'generate_for_coursework'),
        ('google_classroom_announcements', 'generate_for_announcement'),
        ('user_profiles', 'generate_for_user_profile'),
        ('team_member_data', 'generate_for_team_member'),
        ('web_crawler_data', 'generate_for_web_crawler'),
        ('google_calendar_events', 'generate_for_calendar_event'),
        ('google_classroom_submissions', 'generate_for_submission')
    ]

    for table_name, method_name in tables_to_check:
        try:
            # Get records without embeddings (limit to avoid memory issues)
            result = supabase.table(table_name).select('id').is_('embedding', 'null').limit(50).execute()

            if result.data:
                print(f"Found {len(result.data)} {table_name} records without embeddings")

                for record in result.data:
                    try:
                        method = getattr(embedding_gen, method_name)
                        success = method(record['id'])
                        if success:
                            total_processed += 1
                            print(f"[SUCCESS] Generated embedding for {table_name}: {record['id']}")
                        else:
                            print(f"[FAILED] Failed to generate embedding for {table_name}: {record['id']}")
                    except Exception as e:
                        print(f"[ERROR] Error generating embedding for {table_name} {record['id']}: {e}")
            else:
                print(f"[OK] All {table_name} records have embeddings")

        except Exception as e:
            print(f"Error checking {table_name}: {e}")

    print(f"\n[SUCCESS] Auto-embedding generation complete! Processed {total_processed} records")

if __name__ == "__main__":
    auto_generate_embeddings()
