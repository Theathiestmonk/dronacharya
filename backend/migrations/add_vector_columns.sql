-- Migration: Add vector embeddings for semantic search
-- This enables fast, intelligent semantic search using OpenAI embeddings and pgvector

-- =============================================
-- 1. ENABLE pgvector EXTENSION
-- =============================================

CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================
-- 2. ADD EMBEDDING COLUMNS TO TABLES
-- =============================================

-- Add embedding column to web_crawler_data
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'web_crawler_data' 
        AND column_name = 'embedding'
    ) THEN
        ALTER TABLE web_crawler_data 
        ADD COLUMN embedding vector(1536);
        RAISE NOTICE 'Added embedding column to web_crawler_data';
    END IF;
END $$;

-- Add embedding column to team_member_data
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'team_member_data' 
        AND column_name = 'embedding'
    ) THEN
        ALTER TABLE team_member_data 
        ADD COLUMN embedding vector(1536);
        RAISE NOTICE 'Added embedding column to team_member_data';
    END IF;
END $$;

-- Add embedding column to google_classroom_coursework
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'google_classroom_coursework' 
        AND column_name = 'embedding'
    ) THEN
        ALTER TABLE google_classroom_coursework 
        ADD COLUMN embedding vector(1536);
        RAISE NOTICE 'Added embedding column to google_classroom_coursework';
    END IF;
END $$;

-- Add embedding column to google_classroom_announcements
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'google_classroom_announcements' 
        AND column_name = 'embedding'
    ) THEN
        ALTER TABLE google_classroom_announcements 
        ADD COLUMN embedding vector(1536);
        RAISE NOTICE 'Added embedding column to google_classroom_announcements';
    END IF;
END $$;

-- =============================================
-- 3. CREATE HNSW INDEXES FOR FAST SIMILARITY SEARCH
-- =============================================

-- Index for web_crawler_data
CREATE INDEX IF NOT EXISTS web_crawler_data_embedding_idx 
ON web_crawler_data 
USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL AND is_active = true;

-- Index for team_member_data
CREATE INDEX IF NOT EXISTS team_member_data_embedding_idx 
ON team_member_data 
USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL AND is_active = true;

-- Index for google_classroom_coursework
CREATE INDEX IF NOT EXISTS google_classroom_coursework_embedding_idx 
ON google_classroom_coursework 
USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

-- Index for google_classroom_announcements
CREATE INDEX IF NOT EXISTS google_classroom_announcements_embedding_idx 
ON google_classroom_announcements 
USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

-- =============================================
-- 4. CREATE SIMILARITY SEARCH FUNCTIONS
-- =============================================

-- Function to search web_crawler_data by embedding
CREATE OR REPLACE FUNCTION match_web_content(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  url text,
  title text,
  description text,
  main_content text,
  content_type varchar,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    wcd.id,
    wcd.url,
    wcd.title,
    wcd.description,
    wcd.main_content,
    wcd.content_type,
    1 - (wcd.embedding <=> query_embedding) as similarity
  FROM web_crawler_data wcd
  WHERE wcd.is_active = true
    AND wcd.embedding IS NOT NULL
    AND 1 - (wcd.embedding <=> query_embedding) > match_threshold
  ORDER BY wcd.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Function to search team_member_data by embedding
CREATE OR REPLACE FUNCTION match_team_members(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  name varchar,
  title varchar,
  description text,
  details text,
  full_content text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    tmd.id,
    tmd.name,
    tmd.title,
    tmd.description,
    tmd.details,
    tmd.full_content,
    1 - (tmd.embedding <=> query_embedding) as similarity
  FROM team_member_data tmd
  WHERE tmd.is_active = true
    AND tmd.embedding IS NOT NULL
    AND 1 - (tmd.embedding <=> query_embedding) > match_threshold
  ORDER BY tmd.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Function to search google_classroom_coursework by embedding
CREATE OR REPLACE FUNCTION match_coursework(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  course_id uuid,
  title varchar,
  description text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    gcw.id,
    gcw.course_id,
    gcw.title,
    gcw.description,
    1 - (gcw.embedding <=> query_embedding) as similarity
  FROM google_classroom_coursework gcw
  WHERE gcw.embedding IS NOT NULL
    AND 1 - (gcw.embedding <=> query_embedding) > match_threshold
  ORDER BY gcw.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Function to search google_classroom_announcements by embedding
CREATE OR REPLACE FUNCTION match_announcements(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  course_id uuid,
  text text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    gca.id,
    gca.course_id,
    gca.text,
    1 - (gca.embedding <=> query_embedding) as similarity
  FROM google_classroom_announcements gca
  WHERE gca.embedding IS NOT NULL
    AND 1 - (gca.embedding <=> query_embedding) > match_threshold
  ORDER BY gca.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- =============================================
-- 5. GRANT PERMISSIONS
-- =============================================

GRANT EXECUTE ON FUNCTION match_web_content(vector, float, int) TO authenticated;
GRANT EXECUTE ON FUNCTION match_team_members(vector, float, int) TO authenticated;
GRANT EXECUTE ON FUNCTION match_coursework(vector, float, int) TO authenticated;
GRANT EXECUTE ON FUNCTION match_announcements(vector, float, int) TO authenticated;

-- =============================================
-- NOTES
-- =============================================
-- 1. Embedding dimension: 1536 (OpenAI text-embedding-3-small)
-- 2. HNSW indexes provide fast approximate nearest neighbor search
-- 3. Cosine similarity: 1 - (embedding <=> query_embedding)
-- 4. Default threshold: 0.7 (70% similarity)
-- 5. Functions filter by is_active where applicable
-- 6. All changes are additive (no data loss)





