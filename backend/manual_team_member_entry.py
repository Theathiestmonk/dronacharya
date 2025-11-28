"""
Manual Team Member Data Entry Script
Use this to manually add team member data that couldn't be extracted automatically
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from supabase_config import get_supabase_client
from app.services.embedding_generator import get_embedding_generator

load_dotenv()

def add_team_member_manually(name, title="", description="", details="", full_content=""):
    """
    Manually add a team member to the database
    
    Args:
        name: Full name of the team member
        title: Their title/role (e.g., "Facilitator", "Director")
        description: Short description (first paragraph)
        details: Additional details
        full_content: Complete popup content
    """
    supabase = get_supabase_client()
    
    if not supabase:
        print("[ERROR] Supabase client not available")
        return False
    
    # Truncate fields to fit database constraints
    name = name[:255] if name else ""
    title = title[:255] if title else ""
    description = description[:500] if description else ""
    details = details[:2000] if details else ""
    full_content = full_content[:5000] if full_content else ""
    
    # Prepare data entry
    team_member_entry = {
        'name': name,
        'title': title if title else None,
        'description': description if description else None,
        'details': details if details else None,
        'full_content': full_content if full_content else None,
        'source_url': 'https://prakriti.edu.in/team/',
        'crawled_date': datetime.now().strftime('%Y-%m-%d'),
        'is_active': True
    }
    
    try:
        # Upsert (insert or update if exists)
        # Use 'name' as conflict key to update existing rows instead of creating duplicates
        result = supabase.table('team_member_data').upsert(
            team_member_entry,
            on_conflict='name'
        ).execute()
        
        # Generate embedding for the new/updated record
        if result.data and len(result.data) > 0:
            record_id = result.data[0].get('id')
            if record_id:
                try:
                    embedding_gen = get_embedding_generator()
                    embedding_gen.generate_for_team_member(record_id)
                except Exception as e:
                    print(f"[WARNING] Failed to generate embedding: {e}")
        
        print(f"[OK] Successfully stored team member: {name}")
        return True
    except Exception as e:
        print(f"[ERROR] Error storing {name}: {e}")
        return False


def add_multiple_team_members(members_data):
    """
    Add multiple team members at once
    
    Args:
        members_data: List of dictionaries, each containing:
            - name (required)
            - title (optional)
            - description (optional)
            - details (optional)
            - full_content (optional)
    """
    print("=" * 60)
    print("Manual Team Member Data Entry")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Members to add: {len(members_data)}")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for member in members_data:
        name = member.get('name', '')
        if not name:
            print(f"[ERROR] Skipping member with no name")
            error_count += 1
            continue
        
        print(f"\nAdding: {name}")
        success = add_team_member_manually(
            name=name,
            title=member.get('title', ''),
            description=member.get('description', ''),
            details=member.get('details', ''),
            full_content=member.get('full_content', '')
        )
        
        if success:
            success_count += 1
        else:
            error_count += 1
    
    print("\n" + "=" * 60)
    print("Entry Summary")
    print("=" * 60)
    print(f"[OK] Successfully added: {success_count} members")
    print(f"[ERROR] Errors: {error_count} members")
    print(f"Total: {len(members_data)} members")
    print("=" * 60)


if __name__ == "__main__":
    # Example: Add missing team members
    # Replace this with actual data from the website
    
    missing_members = [
        {
            "name": "Priyanka Oberoi",
            "title": "Facilitator Art & Design and Design & Technology Disciplines",
            "description": "",  # Add description here
            "details": "",  # Add details here
            "full_content": ""  # Add full popup content here
        },
        {
            "name": "Ritu Martin",
            "title": "Senior Primary Facilitator Sciences",
            "description": "",  # Add description here
            "details": "",  # Add details here
            "full_content": ""  # Add full popup content here
        },
        {
            "name": "Shuchi Mishra",
            "title": "IGCSE English Facilitator",
            "description": "",  # Add description here
            "details": "",  # Add details here
            "full_content": ""  # Add full popup content here
        },
        {
            "name": "Gunjan Bhatia",
            "title": "Early Years Programme Facilitator",
            "description": "",  # Add description here
            "details": "",  # Add details here
            "full_content": ""  # Add full popup content here
        }
    ]
    
    # Uncomment and fill in the data, then run:
    # add_multiple_team_members(missing_members)
    
    print("=" * 60)
    print("Manual Team Member Entry Script")
    print("=" * 60)
    print("\nTo use this script:")
    print("1. Edit the 'missing_members' list above")
    print("2. Fill in the details for each member")
    print("3. Uncomment the last line: add_multiple_team_members(missing_members)")
    print("4. Run: python manual_team_member_entry.py")
    print("\nOr use the function directly:")
    print("  add_team_member_manually(name='...', title='...', description='...', ...)")
    print("=" * 60)




