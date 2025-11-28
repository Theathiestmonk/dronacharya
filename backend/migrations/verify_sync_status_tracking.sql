-- Verify and add sync status tracking columns if needed
-- This migration ensures all tables have proper timestamp columns for sync status

-- Check and add last_synced_at index to google_classroom_courses if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'google_classroom_courses' 
        AND indexname = 'idx_google_classroom_courses_last_synced'
    ) THEN
        CREATE INDEX idx_google_classroom_courses_last_synced 
        ON google_classroom_courses(last_synced_at DESC) 
        WHERE last_synced_at IS NOT NULL;
        RAISE NOTICE 'Added index on last_synced_at for google_classroom_courses';
    END IF;
END $$;

-- Check and add last_synced_at index to google_calendar_events if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'google_calendar_events' 
        AND indexname = 'idx_google_calendar_events_last_synced'
    ) THEN
        CREATE INDEX idx_google_calendar_events_last_synced 
        ON google_calendar_events(last_synced_at DESC) 
        WHERE last_synced_at IS NOT NULL;
        RAISE NOTICE 'Added index on last_synced_at for google_calendar_events';
    END IF;
END $$;

-- Check and add crawled_at index to web_crawler_data if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'web_crawler_data' 
        AND indexname = 'idx_web_crawler_data_crawled_at'
    ) THEN
        CREATE INDEX idx_web_crawler_data_crawled_at 
        ON web_crawler_data(crawled_at DESC) 
        WHERE crawled_at IS NOT NULL AND is_active = true;
        RAISE NOTICE 'Added index on crawled_at for web_crawler_data';
    END IF;
END $$;

-- Note: The columns (last_synced_at, crawled_at) should already exist in the tables
-- This migration only adds indexes for better query performance



