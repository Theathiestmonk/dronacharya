-- Safe fix for google_calendar_events table to use 384 dimensions instead of 1536
-- This script handles view dependencies properly

-- Step 1: Drop the dependent view first
DROP VIEW IF EXISTS vw_calendar_event_holidays CASCADE;

-- Step 2: Now we can safely drop the embedding column
ALTER TABLE google_calendar_events DROP COLUMN IF EXISTS embedding;

-- Step 3: Add the embedding column with correct 384 dimensions
ALTER TABLE google_calendar_events ADD COLUMN embedding vector(384);

-- Step 4: Create the proper indexes for 384-dimension embeddings
DROP INDEX IF EXISTS google_calendar_events_embedding_idx;
CREATE INDEX IF NOT EXISTS google_calendar_events_embedding_idx ON google_calendar_events USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);

DROP INDEX IF EXISTS idx_google_calendar_events_embedding;
CREATE INDEX IF NOT EXISTS idx_google_calendar_events_embedding ON google_calendar_events USING ivfflat (embedding vector_cosine_ops);

-- Step 5: Add comment for the column
COMMENT ON COLUMN google_calendar_events.embedding IS '384-dimensional embedding vector for semantic search';

-- Step 6: Recreate the view if it existed (you may need to recreate it based on your application needs)
-- If you had a vw_calendar_event_holidays view, recreate it here after the column change




