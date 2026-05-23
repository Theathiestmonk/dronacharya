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
for row in data.data:
    if 'didac' in str(row['main_content']).lower() or 'didac' in str(row['title']).lower():
        print(f"Found DIDAC in web_crawler_data id {row['id']} (URL: {row['url']})")
        print(f"Title: {row['title']}")
        print(f"Content preview: {str(row['main_content'])[:200]}")
