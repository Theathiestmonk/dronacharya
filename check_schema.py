#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

import supabase_config
supabase = supabase_config.get_supabase_client()

if supabase:
    print("=== COURSEWORK TABLE SCHEMA ===")
    result = supabase.table('information_schema.columns').select('column_name, data_type, character_maximum_length').filter('table_name', 'eq', 'google_classroom_coursework').execute()
    for col in result.data:
        col_name = col['column_name']
        data_type = col['data_type']
        max_len = col['character_maximum_length'] or 'NULL'
        print(f'  {col_name}: {data_type}({max_len})')

    print("\n=== SUBMISSIONS TABLE SCHEMA ===")
    result2 = supabase.table('information_schema.columns').select('column_name, data_type, character_maximum_length').filter('table_name', 'eq', 'google_classroom_submissions').execute()
    for col in result2.data:
        col_name = col['column_name']
        data_type = col['data_type']
        max_len = col['character_maximum_length'] or 'NULL'
        print(f'  {col_name}: {data_type}({max_len})')

    print("\n=== ALL VARCHAR(20) COLUMNS IN DATABASE ===")
    result3 = supabase.table('information_schema.columns').select('table_name, column_name, data_type, character_maximum_length').filter('character_maximum_length', 'eq', 20).filter('data_type', 'ilike', '%varchar%').execute()
    for col in result3.data:
        table_name = col['table_name']
        col_name = col['column_name']
        data_type = col['data_type']
        max_len = col['character_maximum_length']
        print(f'  {table_name}.{col_name}: {data_type}({max_len})')

else:
    print('Failed to connect to Supabase')


