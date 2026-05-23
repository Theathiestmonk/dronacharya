from dotenv import load_dotenv
import os
import sys

sys.path.append('/home/dhruv/prakriti/dronacharya/backend')
os.chdir('/home/dhruv/prakriti/dronacharya/backend')

load_dotenv()

from supabase_config import get_supabase_client
supabase = get_supabase_client()

print("Fetching web_crawler_data...")
data = supabase.table('web_crawler_data').select('id, url, title, main_content').execute()
count = 0
for row in data.data:
    if 'cisce' in str(row['main_content']).lower() or 'cisce' in str(row['title']).lower():
        print(f"Deleting web_crawler_data id {row['id']} (URL: {row['url']})")
        supabase.table('web_crawler_data').delete().eq('id', row['id']).execute()
        count += 1
    
print(f"Done! Deleted {count} records containing 'cisce' from web_crawler_data.")

try:
    print("Checking for response cache...")
    response_data = supabase.table('search_cache').select('id').execute()
    for row in response_data.data:
        supabase.table('search_cache').delete().eq('id', row['id']).execute()
    print("Cleared search_cache")
except Exception as e:
    print(f"Failed to clear search_cache: {e}")

try:
    print("Checking for query cache...")
    query_data = supabase.table('query_cache').select('id').execute()
    for row in query_data.data:
        supabase.table('query_cache').delete().eq('id', row['id']).execute()
    print("Cleared query_cache")
except Exception as e:
    print(f"Failed to clear query_cache: {e}")
