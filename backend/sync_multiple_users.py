#!/usr/bin/env python3
"""
Sync classroom data for multiple users in prakriti.org.in domain
This script takes a list of user emails and syncs classroom data for each
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Configuration - Add all teacher emails here
USERS_TO_SYNC = [
    "dummy@learners.prakriti.org.in",
    # Add more teacher emails as needed
    # "teacher1@learners.prakriti.org.in",
    # "teacher2@learners.prakriti.org.in",
    # "teacher3@learners.prakriti.org.in",
]

async def sync_user_data(user_email: str, service: str = "classroom"):
    """Sync data for a specific user"""
    print(f"\n🔄 Syncing {service} data for: {user_email}")

    try:
        from app.routes.admin import sync_dwd

        class MockRequest:
            def __init__(self, email):
                self.user_email = email

        request = MockRequest(user_email)
        result = await sync_dwd(service, request)

        if result.get('success'):
            summary = result.get('summary', {})
            total_items = sum(summary.values())
            print(f"✅ {user_email}: Synced {total_items} {service} items")
            return result
        else:
            print(f"❌ {user_email}: {service} sync failed")
            return result

    except Exception as e:
        print(f"❌ {user_email}: Error - {e}")
        return {"success": False, "error": str(e)}

async def sync_all_users():
    """Sync classroom data for all users in the list"""
    print("=" * 60)
    print("SYNCING CLASSROOM DATA FOR MULTIPLE USERS")
    print("=" * 60)

    total_stats = {
        "courses": 0, "teachers": 0, "students": 0,
        "coursework": 0, "submissions": 0, "announcements": 0
    }

    successful_syncs = 0

    for i, user_email in enumerate(USERS_TO_SYNC, 1):
        print(f"\n[USER {i}/{len(USERS_TO_SYNC)}]")

        result = await sync_user_data(user_email, "classroom")

        if result.get('success'):
            successful_syncs += 1
            summary = result.get('summary', {})
            for key in total_stats:
                total_stats[key] += summary.get(key, 0)

        # Small delay to avoid rate limits
        await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("MULTI-USER SYNC COMPLETE")
    print("=" * 60)

    total_items = sum(total_stats.values())
    print(f"Users processed: {len(USERS_TO_SYNC)}")
    print(f"Successful syncs: {successful_syncs}")
    print(f"Total items synced: {total_items}")

    if total_items > 0:
        print("\n✅ SUCCESS: Classroom data synced for entire domain!")
        print("All courses, teachers, students, and announcements are now in Supabase.")
    else:
        print("\n❌ No data was synced. Check user emails and permissions.")

    return {
        "success": total_items > 0,
        "users_processed": len(USERS_TO_SYNC),
        "successful_syncs": successful_syncs,
        "total_items": total_items,
        "stats": total_stats
    }

def update_user_list():
    """Update the user list - add your teacher emails here"""
    print("Current user list:")
    for i, email in enumerate(USERS_TO_SYNC, 1):
        print(f"  {i}. {email}")

    print("\nTo add more users, edit the USERS_TO_SYNC list in this file.")
    print("Add all teacher emails from learners.prakriti.org.in domain.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        update_user_list()
    else:
        asyncio.run(sync_all_users())




