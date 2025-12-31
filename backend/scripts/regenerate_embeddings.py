#!/usr/bin/env python3
"""
Script to regenerate all existing embeddings using sentence-transformers/all-MiniLM-L6-v2
This updates the new 384-dimension columns with embeddings from the sentence-transformers model
"""

import os
import sys
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_config import get_supabase_client
from app.services.vector_search_service import VectorSearchService

def regenerate_embeddings_for_table(table_name: str, id_column: str, text_column: str,
                                  embedding_column: str = 'embedding_384', batch_size: int = 50):
    """
    Regenerate embeddings for a specific table

    Args:
        table_name: Name of the table to process
        id_column: Primary key column name
        text_column: Column containing text to embed
        embedding_column: Column to store new embeddings
        batch_size: Number of records to process at once
    """
    print(f"\n🔄 Processing table: {table_name}")
    print(f"   Text column: {text_column}")
    print(f"   Embedding column: {embedding_column}")

    supabase = get_supabase_client()
    vector_service = VectorSearchService()

    # Get total count
    count_result = supabase.table(table_name).select(id_column, {count: 'exact'}).execute()
    total_records = count_result.count if hasattr(count_result, 'count') else 0

    print(f"   Total records: {total_records}")

    if total_records == 0:
        print(f"   ⏭️ No records to process for {table_name}")
        return 0

    # Process in batches
    processed = 0
    successful = 0
    failed = 0

    for offset in range(0, total_records, batch_size):
        try:
            # Fetch batch of records
            result = supabase.table(table_name).select(f'{id_column}, {text_column}').range(offset, offset + batch_size - 1).execute()

            if not result.data:
                break

            batch_processed = 0
            batch_successful = 0
            batch_failed = 0

            for record in result.data:
                record_id = record[id_column]
                text = record[text_column]

                if not text or not text.strip():
                    print(f"     ⚠️ Skipping record {record_id} - empty text")
                    continue

                try:
                    # Generate new embedding
                    embedding = vector_service.generate_embedding(text)

                    # Update record with new embedding
                    supabase.table(table_name).update({
                        embedding_column: embedding
                    }).eq(id_column, record_id).execute()

                    batch_successful += 1
                    print(f"     ✅ Processed record {record_id}")

                except Exception as e:
                    print(f"     ❌ Failed to process record {record_id}: {e}")
                    batch_failed += 1

                batch_processed += 1

            processed += batch_processed
            successful += batch_successful
            failed += batch_failed

            print(f"   📊 Batch {offset//batch_size + 1}: {batch_processed} processed, {batch_successful} successful, {batch_failed} failed")

            # Small delay between batches to avoid overwhelming the service
            if offset + batch_size < total_records:
                time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Error processing batch at offset {offset}: {e}")
            break

    print(f"   📈 {table_name} summary: {processed} processed, {successful} successful, {failed} failed")
    return successful

def main():
    """Main function to regenerate all embeddings"""
    print("=" * 70)
    print("REGENERATE EMBEDDINGS WITH SENTENCE-TRANSFORMERS")
    print("=" * 70)
    print(f"Started at: {datetime.now().isoformat()}")

    try:
        # Test services
        print("\n🧪 Testing services...")
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Supabase connection failed")
            return 1

        vector_service = VectorSearchService()
        print("✅ Services initialized")

        # Test embedding generation
        test_embedding = vector_service.generate_embedding("This is a test sentence for embedding generation.")
        print(f"✅ Embedding generation works (dimension: {len(test_embedding)})")

        # Define tables to process
        tables_config = [
            {
                'table': 'web_crawler_data',
                'id_column': 'id',
                'text_column': 'title',  # Primary text field
                'secondary_text': 'description'  # Combine with main_content if available
            },
            {
                'table': 'team_member_data',
                'id_column': 'id',
                'text_column': 'name',
                'secondary_text': 'title'
            },
            {
                'table': 'google_classroom_coursework',
                'id_column': 'id',
                'text_column': 'title',
                'secondary_text': 'description'
            },
            {
                'table': 'google_classroom_announcements',
                'id_column': 'id',
                'text_column': 'text',
                'secondary_text': None
            }
        ]

        total_successful = 0

        # Process each table
        for config in tables_config:
            try:
                # For tables with secondary text, we need special handling
                if config.get('secondary_text'):
                    # Custom processing for tables with combined text
                    successful = regenerate_combined_text_table(
                        config['table'],
                        config['id_column'],
                        config['text_column'],
                        config['secondary_text']
                    )
                else:
                    # Standard single-column processing
                    successful = regenerate_embeddings_for_table(
                        config['table'],
                        config['id_column'],
                        config['text_column']
                    )

                total_successful += successful

            except Exception as e:
                print(f"❌ Error processing table {config['table']}: {e}")

        print("\n" + "=" * 70)
        print("REGENERATION COMPLETE")
        print("=" * 70)
        print(f"Finished at: {datetime.now().isoformat()}")
        print(f"Total embeddings regenerated: {total_successful}")

        if total_successful > 0:
            print("\n✅ SUCCESS: All embeddings have been regenerated with sentence-transformers!")
            print("Next steps:")
            print("1. Run the migration script to switch to new embedding columns")
            print("2. Update vector search functions if needed")
            print("3. Test semantic search functionality")
            return 0
        else:
            print("\n⚠️ WARNING: No embeddings were regenerated")
            return 1

    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

def regenerate_combined_text_table(table_name: str, id_column: str,
                                  primary_column: str, secondary_column: str):
    """Regenerate embeddings for tables that combine multiple text columns"""
    print(f"\n🔄 Processing combined-text table: {table_name}")
    print(f"   Primary: {primary_column}, Secondary: {secondary_column}")

    supabase = get_supabase_client()
    vector_service = VectorSearchService()

    # Get total count
    count_result = supabase.table(table_name).select(id_column, {count: 'exact'}).execute()
    total_records = count_result.count if hasattr(count_result, 'count') else 0

    print(f"   Total records: {total_records}")

    if total_records == 0:
        return 0

    processed = 0
    successful = 0

    # Process in smaller batches for combined text
    batch_size = 25

    for offset in range(0, total_records, batch_size):
        result = supabase.table(table_name).select(f'{id_column}, {primary_column}, {secondary_column}').range(offset, offset + batch_size - 1).execute()

        if not result.data:
            break

        for record in result.data:
            record_id = record[id_column]

            # Combine text from multiple columns
            primary_text = record.get(primary_column, '') or ''
            secondary_text = record.get(secondary_column, '') or ''

            # For web_crawler_data, also include main_content
            if table_name == 'web_crawler_data':
                main_content = record.get('main_content', '') or ''
                # Limit main_content to avoid extremely long texts
                if main_content:
                    main_content = main_content[:4000]  # Limit to 4000 chars
                combined_text = f"{primary_text} {secondary_text} {main_content}".strip()
            else:
                combined_text = f"{primary_text} {secondary_text}".strip()

            if not combined_text:
                print(f"     ⚠️ Skipping record {record_id} - no text content")
                continue

            try:
                # Generate embedding
                embedding = vector_service.generate_embedding(combined_text)

                # Update record
                supabase.table(table_name).update({
                    'embedding_384': embedding
                }).eq(id_column, record_id).execute()

                successful += 1
                print(f"     ✅ Processed record {record_id}")

            except Exception as e:
                print(f"     ❌ Failed to process record {record_id}: {e}")

            processed += 1

        print(f"   📊 Batch {offset//batch_size + 1}: {len(result.data)} processed")

        # Longer delay for combined text processing
        if offset + batch_size < total_records:
            time.sleep(1)

    print(f"   📈 {table_name} summary: {processed} processed, {successful} successful")
    return successful

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)




