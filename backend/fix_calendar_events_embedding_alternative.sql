-- Alternative approach: Update existing column instead of dropping it
-- This preserves any existing data and dependencies

-- Step 1: Check current column type and modify it
-- Note: PostgreSQL doesn't allow direct ALTER TYPE for vector columns with different dimensions
-- So we need to use a different approach

-- Create a temporary column with new dimensions
ALTER TABLE google_calendar_events ADD COLUMN embedding_new vector(384);

-- Copy data if any exists (though embeddings are typically regenerated)
-- UPDATE google_calendar_events SET embedding_new = embedding WHERE embedding IS NOT NULL;

-- Drop the old indexes
DROP INDEX IF EXISTS google_calendar_events_embedding_idx;
DROP INDEX IF EXISTS idx_google_calendar_events_embedding;

-- Drop the old column (this should work now since we have a new column)
ALTER TABLE google_calendar_events DROP COLUMN IF EXISTS embedding;

-- Rename the new column to the original name
ALTER TABLE google_calendar_events RENAME COLUMN embedding_new TO embedding;

-- Create the proper indexes for 384-dimension embeddings
CREATE INDEX IF NOT EXISTS google_calendar_events_embedding_idx ON google_calendar_events USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_google_calendar_events_embedding ON google_calendar_events USING ivfflat (embedding vector_cosine_ops);

-- Add comment for the column
COMMENT ON COLUMN google_calendar_events.embedding IS '384-dimensional embedding vector for semantic search';




