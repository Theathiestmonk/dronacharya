#!/usr/bin/env python3
"""
Generate embeddings for user profile records
"""
from supabase_config import get_supabase_client
from app.services.embedding_generator import EmbeddingGenerator

def generate_user_profile_embeddings():
    supabase = get_supabase_client()
    if not supabase:
        print("Could not connect to Supabase")
        return

    # Get user_profiles records without embeddings
    result = supabase.table('user_profiles').select('id, first_name, last_name, role').is_('embedding', 'null').execute()

    if result.data:
        print(f'Found {len(result.data)} user profile records without embeddings')

        gen = EmbeddingGenerator()
        success_count = 0

        for record in result.data:
            success = gen.generate_for_user_profile(record['id'])
            if success:
                success_count += 1
                print(f'Generated embedding for: {record["first_name"]} {record["last_name"]} ({record["role"]})')
            else:
                print(f'Failed to generate embedding for: {record["first_name"]} {record["last_name"]}')

        print(f'Successfully generated embeddings for {success_count}/{len(result.data)} user profiles')
    else:
        print('All user profile records already have embeddings')

if __name__ == "__main__":
    generate_user_profile_embeddings()




