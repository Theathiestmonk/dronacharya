#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

import supabase_config
supabase = supabase_config.get_supabase_client()

if supabase:
    try:
        # Read the migration SQL
        migration_path = os.path.join(os.path.dirname(__file__), 'migrations', 'fix_varchar_limits.sql')
        with open(migration_path, 'r') as f:
            sql_content = f.read()

        print("Applying VARCHAR limits migration...")
        print("SQL to execute:")
        print(sql_content)
        print("\n" + "="*50)

        # Execute the SQL using rpc call
        result = supabase.rpc('exec_sql', {'sql': sql_content}).execute()

        print("✅ Migration applied successfully!")
        print("Result:", result)

    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        print("You may need to run this SQL manually in Supabase SQL Editor:")
        print("\nCopy and paste this SQL:")
        migration_path = os.path.join(os.path.dirname(__file__), 'migrations', 'fix_varchar_limits.sql')
        with open(migration_path, 'r') as f:
            print(f.read())

else:
    print('❌ Failed to connect to Supabase')
    print("Please run the SQL manually in Supabase SQL Editor:")
    migration_path = os.path.join(os.path.dirname(__file__), 'migrations', 'fix_varchar_limits.sql')
    with open(migration_path, 'r') as f:
        print(f.read())


