#!/usr/bin/env python3
"""
Generate embeddings for team member data records
"""
from supabase_config import get_supabase_client
from app.services.embedding_generator import EmbeddingGenerator

def generate_team_embeddings():
    supabase = get_supabase_client()
    if not supabase:
        print("Could not connect to Supabase")
        return

    # Get team_member_data records without embeddings
    result = supabase.table('team_member_data').select('id, name').is_('embedding', 'null').execute()

    if result.data:
        print(f'Found {len(result.data)} team member records without embeddings')

        gen = EmbeddingGenerator()
        success_count = 0

        for record in result.data:
            success = gen.generate_for_team_member(record['id'])
            if success:
                success_count += 1
                print(f'Generated embedding for: {record["name"]}')
            else:
                print(f'Failed to generate embedding for: {record["name"]}')

        print(f'Successfully generated embeddings for {success_count}/{len(result.data)} records')
    else:
        print('All team member records already have embeddings')

if __name__ == "__main__":
    generate_team_embeddings()




