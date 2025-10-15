-- Web Crawler Data Storage Schema
-- This table stores crawled website data for faster chatbot responses

-- Main table for storing crawled content
CREATE TABLE IF NOT EXISTS web_crawler_data (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT,
  description TEXT,
  main_content TEXT,
  headings JSONB DEFAULT '[]'::jsonb,
  links JSONB DEFAULT '[]'::jsonb,
  content_type VARCHAR(50) DEFAULT 'general', -- 'general', 'team', 'calendar', 'news', 'article', 'academic', 'admission', 'contact', 'testimonial'
  query_keywords TEXT[], -- Array of keywords this content is relevant for
  relevance_score INTEGER DEFAULT 0, -- Score based on how relevant this content is
  crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  crawled_date DATE, -- Regular column for date
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  
  -- Constraints
  UNIQUE(url, crawled_date) -- One crawl per URL per day
);

-- Table for storing team member specific data
CREATE TABLE IF NOT EXISTS team_member_data (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  title VARCHAR(255),
  description TEXT,
  details TEXT,
  full_content TEXT,
  image_url TEXT,
  source_url TEXT,
  crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  crawled_date DATE, -- Regular column for date
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  
  -- Constraints
  UNIQUE(name, crawled_date) -- One entry per person per day
);

-- Table for storing calendar events
CREATE TABLE IF NOT EXISTS calendar_event_data (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  event_title VARCHAR(500),
  event_date DATE,
  event_time TIME,
  event_description TEXT,
  event_type VARCHAR(100), -- 'upcoming', 'past', 'festival', 'academic', 'sports'
  source_url TEXT,
  crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  
  -- Constraints
  UNIQUE(event_title, event_date, source_url)
);

-- Table for storing search cache
CREATE TABLE IF NOT EXISTS search_cache (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  query_hash VARCHAR(64) NOT NULL, -- Hash of the search query
  query_text TEXT NOT NULL,
  cached_results JSONB NOT NULL,
  result_count INTEGER DEFAULT 0,
  cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours'),
  is_active BOOLEAN DEFAULT true,
  
  -- Constraints
  UNIQUE(query_hash)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_web_crawler_data_url ON web_crawler_data(url);
CREATE INDEX IF NOT EXISTS idx_web_crawler_data_content_type ON web_crawler_data(content_type);
CREATE INDEX IF NOT EXISTS idx_web_crawler_data_crawled_at ON web_crawler_data(crawled_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_crawler_data_keywords ON web_crawler_data USING GIN(query_keywords);
CREATE INDEX IF NOT EXISTS idx_web_crawler_data_active ON web_crawler_data(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_team_member_data_name ON team_member_data(name);
CREATE INDEX IF NOT EXISTS idx_team_member_data_crawled_at ON team_member_data(crawled_at DESC);
CREATE INDEX IF NOT EXISTS idx_team_member_data_active ON team_member_data(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_calendar_event_data_date ON calendar_event_data(event_date);
CREATE INDEX IF NOT EXISTS idx_calendar_event_data_type ON calendar_event_data(event_type);
CREATE INDEX IF NOT EXISTS idx_calendar_event_data_crawled_at ON calendar_event_data(crawled_at DESC);
CREATE INDEX IF NOT EXISTS idx_calendar_event_data_active ON calendar_event_data(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_search_cache_query_hash ON search_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_cache_expires_at ON search_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_search_cache_active ON search_cache(is_active) WHERE is_active = true;

-- Triggers for updated_at and crawled_date
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to set crawled_date from crawled_at
CREATE OR REPLACE FUNCTION set_crawled_date()
RETURNS TRIGGER AS $$
BEGIN
    NEW.crawled_date = NEW.crawled_at::date;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for web_crawler_data
CREATE TRIGGER set_web_crawler_data_crawled_date
    BEFORE INSERT OR UPDATE ON web_crawler_data 
    FOR EACH ROW EXECUTE FUNCTION set_crawled_date();

CREATE TRIGGER update_web_crawler_data_updated_at 
    BEFORE UPDATE ON web_crawler_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Triggers for team_member_data
CREATE TRIGGER set_team_member_data_crawled_date
    BEFORE INSERT OR UPDATE ON team_member_data 
    FOR EACH ROW EXECUTE FUNCTION set_crawled_date();

CREATE TRIGGER update_team_member_data_updated_at 
    BEFORE UPDATE ON team_member_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Triggers for calendar_event_data
CREATE TRIGGER update_calendar_event_data_updated_at 
    BEFORE UPDATE ON calendar_event_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS)
ALTER TABLE web_crawler_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_member_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_event_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_cache ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Allow authenticated users to read all data
CREATE POLICY "Allow read access to web crawler data" ON web_crawler_data
    FOR SELECT USING (true);

CREATE POLICY "Allow read access to team member data" ON team_member_data
    FOR SELECT USING (true);

CREATE POLICY "Allow read access to calendar event data" ON calendar_event_data
    FOR SELECT USING (true);

CREATE POLICY "Allow read access to search cache" ON search_cache
    FOR SELECT USING (true);

-- Grant permissions
GRANT ALL ON web_crawler_data TO authenticated;
GRANT ALL ON team_member_data TO authenticated;
GRANT ALL ON calendar_event_data TO authenticated;
GRANT ALL ON search_cache TO authenticated;

-- Functions for data management
CREATE OR REPLACE FUNCTION cleanup_old_crawler_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete data older than 7 days
    DELETE FROM web_crawler_data 
    WHERE crawled_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM team_member_data 
    WHERE crawled_at < NOW() - INTERVAL '7 days';
    
    DELETE FROM calendar_event_data 
    WHERE crawled_at < NOW() - INTERVAL '7 days';
    
    DELETE FROM search_cache 
    WHERE expires_at < NOW();
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get fresh data (crawled today)
CREATE OR REPLACE FUNCTION get_fresh_crawler_data(p_content_type VARCHAR DEFAULT NULL)
RETURNS TABLE (
    id UUID,
    url TEXT,
    title TEXT,
    description TEXT,
    main_content TEXT,
    content_type VARCHAR,
    query_keywords TEXT[],
    crawled_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wcd.id,
        wcd.url,
        wcd.title,
        wcd.description,
        wcd.main_content,
        wcd.content_type,
        wcd.query_keywords,
        wcd.crawled_at
    FROM web_crawler_data wcd
    WHERE wcd.is_active = true
    AND wcd.crawled_at >= CURRENT_DATE
    AND (p_content_type IS NULL OR wcd.content_type = p_content_type)
    ORDER BY wcd.relevance_score DESC, wcd.crawled_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to search content by keywords
CREATE OR REPLACE FUNCTION search_crawler_content(p_keywords TEXT[])
RETURNS TABLE (
    id UUID,
    url TEXT,
    title TEXT,
    description TEXT,
    main_content TEXT,
    content_type VARCHAR,
    relevance_score INTEGER,
    crawled_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wcd.id,
        wcd.url,
        wcd.title,
        wcd.description,
        wcd.main_content,
        wcd.content_type,
        wcd.relevance_score,
        wcd.crawled_at
    FROM web_crawler_data wcd
    WHERE wcd.is_active = true
    AND wcd.crawled_at >= CURRENT_DATE - INTERVAL '1 day'
    AND wcd.query_keywords && p_keywords
    ORDER BY wcd.relevance_score DESC, wcd.crawled_at DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION cleanup_old_crawler_data() TO authenticated;
GRANT EXECUTE ON FUNCTION get_fresh_crawler_data(VARCHAR) TO authenticated;
GRANT EXECUTE ON FUNCTION search_crawler_content(TEXT[]) TO authenticated;
