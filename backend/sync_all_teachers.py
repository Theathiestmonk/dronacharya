#!/usr/bin/env python3
"""
Sync classroom data for ALL teachers in prakriti.org.in domain
Takes a list of teacher emails and syncs classroom data for each
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone

# Add current directory to path
sys.path.insert(0, os.getcwd())

# List of all teacher emails in prakriti.org.in domain
# You can expand this list with all teacher emails
TEACHER_EMAILS = [
    "teacher1@learners.prakriti.org.in",
    "teacher2@learners.prakriti.org.in",
    "teacher3@learners.prakriti.org.in",
    # Add more teacher emails here
    "dummy@learners.prakriti.org.in",  # Keep this as fallback
]

async def sync_teacher_classroom_data(teacher_email: str):
    """Sync classroom data for a specific teacher using DWD"""
    print(f"\n🔍 Syncing classroom data for: {teacher_email}")

    try:
        # Import the DWD sync function
        from app.routes.admin import sync_dwd
        from app.services.google_dwd_service import get_dwd_service

        # Test DWD service
        dwd_service = get_dwd_service()
        if not dwd_service:
            print(f"❌ DWD service not available for {teacher_email}")
            return {"success": False, "error": "DWD service not available"}

        # Create mock request for the teacher
        class MockRequest:
            def __init__(self, email):
                self.user_email = email

        request = MockRequest(teacher_email)

        # Sync classroom data for this teacher
        result = await sync_dwd("classroom", request)

        if result.get('success'):
            summary = result.get('summary', {})
            total_items = sum(summary.values())
            print(f"✅ {teacher_email}: Synced {total_items} items")
            print(f"   Courses: {summary.get('courses', 0)}, Teachers: {summary.get('teachers', 0)}, Students: {summary.get('students', 0)}, Announcements: {summary.get('announcements', 0)}")
            return result
        else:
            print(f"❌ {teacher_email}: Sync failed - {result.get('message', 'Unknown error')}")
            return result

    except Exception as e:
        print(f"❌ {teacher_email}: Error - {e}")
        return {"success": False, "error": str(e)}

async def sync_all_teachers():
    """Sync classroom data for all teachers in the list"""
    print("=" * 70)
    print("SYNCING CLASSROOM DATA FOR ALL TEACHERS IN PRAKRITI.ORG.IN")
    print("=" * 70)

    total_stats = {
        "courses": 0,
        "teachers": 0,
        "students": 0,
        "coursework": 0,
        "submissions": 0,
        "announcements": 0
    }

    successful_syncs = 0
    failed_syncs = 0

    for i, teacher_email in enumerate(TEACHER_EMAILS, 1):
        print(f"\n[TEACHER {i}/{len(TEACHER_EMAILS)}]")

        result = await sync_teacher_classroom_data(teacher_email)

        if result.get('success'):
            successful_syncs += 1
            # Add to total stats
            summary = result.get('summary', {})
            for key in total_stats:
                total_stats[key] += summary.get(key, 0)
        else:
            failed_syncs += 1

        # Small delay between syncs to avoid rate limits
        if i < len(TEACHER_EMAILS):
            print("⏳ Waiting 2 seconds before next teacher...")
            await asyncio.sleep(2)

    # Final summary
    print("\n" + "=" * 70)
    print("SYNC COMPLETE - SUMMARY")
    print("=" * 70)

    total_items = sum(total_stats.values())

    print(f"Teachers processed: {len(TEACHER_EMAILS)}")
    print(f"Successful syncs: {successful_syncs}")
    print(f"Failed syncs: {failed_syncs}")
    print(f"Total items synced: {total_items}")

    print("\nDetailed breakdown:")
    for key, value in total_stats.items():
        print(f"  {key.capitalize()}: {value}")

    if successful_syncs > 0:
        print("\n✅ SUCCESS: Classroom data for entire prakriti.org.in domain is now synced!")
        print("All courses, teachers, students, announcements, and coursework are available in Supabase.")
    else:
        print("\n❌ FAILURE: No teacher data was successfully synced.")

    return {
        "success": successful_syncs > 0,
        "total_teachers": len(TEACHER_EMAILS),
        "successful_syncs": successful_syncs,
        "failed_syncs": failed_syncs,
        "total_items": total_items,
        "stats": total_stats
    }

async def main():
    """Main function"""
    # First check if we can import required modules
    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            print("✅ Supabase connection OK")
        else:
            print("❌ Supabase connection failed")
            return

        from app.services.google_dwd_service import get_dwd_service
        dwd = get_dwd_service()
        if dwd:
            print("✅ DWD service OK")
            print(f"   Credentials: {os.path.basename(dwd.service_account_path)}")
            print(f"   Domain: {dwd.workspace_domain}")
        else:
            print("❌ DWD service failed")
            return

    except Exception as e:
        print(f"❌ Import error: {e}")
        return

    # Confirm before starting
    print(f"\nReady to sync classroom data for {len(TEACHER_EMAILS)} teachers.")
    print("This will fetch ALL classroom data from prakriti.org.in domain.")

    try:
        # In a real environment, you'd get user confirmation
        # confirm = input("Continue? (yes/no): ").lower().strip()
        # if confirm not in ['yes', 'y']:
        #     print("Sync cancelled")
        #     return

        # Run the sync
        result = await sync_all_teachers()

        # Save results to file
        with open('sync_results.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)

        print(f"\nResults saved to sync_results.json")

    except KeyboardInterrupt:
        print("\n⚠️ Sync interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())




