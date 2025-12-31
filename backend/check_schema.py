#!/usr/bin/env python3
"""
Check the current database schema for embedding columns
"""
from supabase_config import get_supabase_client

def check_embedding_columns():
    supabase = get_supabase_client()
    if not supabase:
        print("Could not connect to Supabase")
        return

    tables = ['google_classroom_announcements', 'google_classroom_coursework', 'web_crawler_data', 'team_member_data']

    for table in tables:
        try:
            result = supabase.table('information_schema.columns').select('table_name, column_name, data_type').filter('table_name', 'eq', table).filter('column_name', 'eq', 'embedding').execute()
            if result.data:
                for row in result.data:
                    print(f"{row['table_name']}.{row['column_name']}: {row['data_type']}")
            else:
                print(f"{table}.embedding: NOT FOUND")
        except Exception as e:
            print(f"Error checking {table}: {e}")

if __name__ == "__main__":
    check_embedding_columns()




