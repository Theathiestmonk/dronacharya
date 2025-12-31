-- Fix google_calendar_events table to use 384 dimensions instead of 1536
-- This script updates the embedding column to use the correct dimensions

-- First, drop the existing embedding column if it exists
ALTER TABLE google_calendar_events DROP COLUMN IF EXISTS embedding;

-- Add the embedding column with correct 384 dimensions
ALTER TABLE google_calendar_events ADD COLUMN embedding vector(384);

-- Create the proper index for 384-dimension embeddings
DROP INDEX IF EXISTS google_calendar_events_embedding_idx;
CREATE INDEX IF NOT EXISTS google_calendar_events_embedding_idx ON google_calendar_events USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);

-- Also create ivfflat index for better performance
DROP INDEX IF EXISTS idx_google_calendar_events_embedding;
CREATE INDEX IF NOT EXISTS idx_google_calendar_events_embedding ON google_calendar_events USING ivfflat (embedding vector_cosine_ops);

-- Update any existing comment
COMMENT ON COLUMN google_calendar_events.embedding IS '384-dimensional embedding vector for semantic search';




