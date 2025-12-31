#!/usr/bin/env python3
"""
Check embedding status across different tables
"""
from supabase_config import get_supabase_client

def check_embeddings():
    supabase = get_supabase_client()
    if not supabase:
        print("Could not connect to Supabase")
        return

    # Check team_member_data embeddings
    result = supabase.table('team_member_data').select('id, name, embedding').limit(5).execute()
    print('Team member data records:')
    for record in result.data:
        has_embedding = 'YES' if record['embedding'] else 'NO'
        print(f'  {record["name"]}: embedding={has_embedding}')

    # Check calendar events
    cal_result = supabase.table('google_calendar_events').select('id, summary').limit(3).execute()
    print(f'\nCalendar events found: {len(cal_result.data)}')

    # Check submissions
    sub_result = supabase.table('google_classroom_submissions').select('id, submission_id').limit(3).execute()
    print(f'Submissions found: {len(sub_result.data)}')

if __name__ == "__main__":
    check_embeddings()




