# Web Crawler Setup Instructions

## 1. Install Dependencies
```bash
cd backend
pip install -r crawler_requirements.txt
```

## 2. Set Environment Variables
Add these to your `.env` file:
```bash
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

## 3. Run SQL Schema
Execute the SQL from `web_crawler_data_schema.sql` in your Supabase SQL editor to create the tables.

## 4. Test Daily Crawl
```bash
cd backend
python daily_crawl_scheduler.py
```

## 5. Set Up Cron Job (Linux/Mac)
Add this to your crontab to run daily at 2 AM:
```bash
0 2 * * * cd /path/to/your/project/backend && python daily_crawl_scheduler.py
```

## 6. Set Up Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to daily at 2:00 AM
4. Set action to start program: `python`
5. Add arguments: `daily_crawl_scheduler.py`
6. Set start in: `C:\path\to\your\project\backend`

## 7. Update Your Chatbot
Replace the import in your chatbot route:
```python
# Old import
from app.agents.web_crawler_agent import get_web_enhanced_response

# New import
from app.agents.web_crawler_agent_updated import get_web_enhanced_response
```

## Benefits:
- ✅ Faster chatbot responses (uses stored data)
- ✅ Reduced server load (no live crawling on each query)
- ✅ Better data consistency (daily crawl ensures fresh data)
- ✅ Improved user experience (faster response times)
- ✅ Scalable solution (can handle more users)

## How It Works:
1. **Daily Crawl**: Runs at 2 AM daily, crawls all URLs and stores in Supabase
2. **Fast Response**: Chatbot queries use stored data instead of live crawling
3. **Smart Caching**: Search results are cached for 24 hours
4. **Data Management**: Old data is automatically cleaned up after 7 days
5. **Keyword Search**: Content is indexed by keywords for fast retrieval
