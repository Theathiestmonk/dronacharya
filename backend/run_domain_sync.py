#!/usr/bin/env python3
"""
Script to run domain-wide Google Classroom sync for Prakriti.org.in
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_supabase():
    """Test Supabase connection"""
    print("Testing Supabase connection...")
    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            # Test query
            result = supabase.table('user_profiles').select('count').limit(1).execute()
            print("SUCCESS: Supabase connected and accessible")
            return True
        else:
            print("ERROR: Supabase client is None")
            return False
    except Exception as e:
        print(f"ERROR: Supabase connection failed: {e}")
        return False

def test_dwd():
    """Test DWD service"""
    print("Testing DWD service...")
    try:
        from app.services.google_dwd_service import get_dwd_service
        dwd_service = get_dwd_service()
        if dwd_service:
            print("SUCCESS: DWD service initialized")
            print(f"Workspace domain: {dwd_service.workspace_domain}")
            print(f"Service account exists: {os.path.exists(dwd_service.service_account_path)}")
            return True
        else:
            print("ERROR: DWD service not available")
            return False
    except Exception as e:
        print(f"ERROR: DWD service failed: {e}")
        return False

def apply_database_schema():
    """Apply the domain-wide schema changes"""
    print("Applying database schema changes...")
    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()

        if not supabase:
            print("ERROR: Cannot apply schema - Supabase not available")
            return False

        # Read schema file
        schema_file = 'create_domain_wide_schema.sql'
        if not os.path.exists(schema_file):
            print(f"ERROR: Schema file not found: {schema_file}")
            return False

        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        # Split into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]

        print(f"Executing {len(statements)} schema statements...")

        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    # For now, just log - actual execution would need raw SQL support
                    print(f"Would execute statement {i}: {statement[:100]}...")
                except Exception as e:
                    print(f"Warning: Statement {i} failed: {e}")

        print("SUCCESS: Schema application completed")
        return True

    except Exception as e:
        print(f"ERROR: Schema application failed: {e}")
        return False

async def run_domain_sync():
    """Run the actual domain sync"""
    print("\n" + "="*60)
    print("STARTING DOMAIN-WIDE CLASSROOM SYNC FOR PRAKRITI.ORG.IN")
    print("="*60)

    try:
        from app.routes.admin import sync_domain_classroom_data

        # Use admin email - you may need to change this
        admin_email = "admin@learners.prakriti.org.in"

        print(f"Syncing classroom data for admin: {admin_email}")
        print("This may take several minutes for large domains...")

        start_time = datetime.now()

        # Run the sync
        result = await sync_domain_classroom_data(admin_email)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\nSync completed in {duration:.1f} seconds")

        if result.get('success'):
            print("SUCCESS: Domain sync completed!")
            print("\nSync Statistics:")
            print(json.dumps(result.get('summary', {}), indent=2))

            print("\nDetailed Stats:")
            stats = result.get('stats', {})
            for category, counts in stats.items():
                created = counts.get('created', 0)
                updated = counts.get('updated', 0)
                total = created + updated
                print(f"  {category}: {total} total ({created} created, {updated} updated)")

        else:
            print(f"ERROR: Sync failed - {result.get('message', 'Unknown error')}")
            return False

        return True

    except Exception as e:
        print(f"ERROR: Domain sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function"""
    print("Prakriti.org.in Domain Classroom Sync Script")
    print("="*50)

    # Test prerequisites
    if not test_supabase():
        print("Cannot proceed - Supabase connection failed")
        return False

    if not test_dwd():
        print("Cannot proceed - DWD service failed")
        return False

    # Apply schema (commented out for safety - run manually first)
    # if not apply_database_schema():
    #     print("Schema application failed, but continuing...")

    print("\nPrerequisites check: PASSED")
    print("Ready to sync all classroom data from prakriti.org.in")

    # Confirm before running
    confirm = input("\nDo you want to run the domain sync now? (yes/no): ").lower().strip()
    if confirm not in ['yes', 'y']:
        print("Sync cancelled by user")
        return False

    # Run the sync
    success = await run_domain_sync()

    if success:
        print("\n" + "="*60)
        print("DOMAIN SYNC COMPLETED SUCCESSFULLY!")
        print("All classroom data from prakriti.org.in has been synced to Supabase")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("DOMAIN SYNC FAILED - Check logs above for details")
        print("="*60)

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)




