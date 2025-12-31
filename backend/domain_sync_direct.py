#!/usr/bin/env python3
"""
Direct domain-wide Google Classroom sync for Prakriti.org.in
"""

import os
import sys
import json
from datetime import datetime, timezone

# Add current directory to path
sys.path.insert(0, os.getcwd())

async def run_direct_domain_sync():
    """Run domain sync directly"""
    print("=" * 60)
    print("DIRECT DOMAIN SYNC FOR PRAKRITI.ORG.IN")
    print("=" * 60)

    try:
        # Import the sync function directly
        from app.routes.admin import sync_domain_classroom_data

        # Use admin email from prakriti.org.in domain for DWD
        admin_email = "dummy@learners.prakriti.org.in"

        print(f"Starting domain sync for: {admin_email}")
        print("This will sync ALL classroom data from prakriti.org.in...")

        start_time = datetime.now()

        # Run the sync
        result = await sync_domain_classroom_data(admin_email)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(".1f")
        print("\nResult:")
        print(json.dumps(result, indent=2))

        if result.get('success'):
            print("\n" + "=" * 60)
            print("SUCCESS: Domain sync completed!")
            print("All classroom data from prakriti.org.in synced to Supabase")
            print("=" * 60)

            summary = result.get('summary', {})
            print(f"Courses: {summary.get('courses', 0)}")
            print(f"Teachers: {summary.get('teachers', 0)}")
            print(f"Students: {summary.get('students', 0)}")
            print(f"Coursework: {summary.get('coursework', 0)}")
            print(f"Submissions: {summary.get('submissions', 0)}")
            print(f"Announcements: {summary.get('announcements', 0)}")

            return True
        else:
            print(f"\nFAILED: {result.get('message', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    print("Starting direct domain sync...")
    success = asyncio.run(run_direct_domain_sync())
    print(f"\nExit code: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
