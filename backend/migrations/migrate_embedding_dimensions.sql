-- Migration: Change embedding columns from 1536 to 384 dimensions
-- This migration supports switching from OpenAI embeddings to sentence-transformers/all-MiniLM-L6-v2

-- Step 1: Add new 384-dimension embedding columns
ALTER TABLE web_crawler_data ADD COLUMN IF NOT EXISTS embedding_384 vector(384);
ALTER TABLE team_member_data ADD COLUMN IF NOT EXISTS embedding_384 vector(384);
ALTER TABLE google_classroom_coursework ADD COLUMN IF NOT EXISTS embedding_384 vector(384);
ALTER TABLE google_classroom_announcements ADD COLUMN IF NOT EXISTS embedding_384 vector(384);

-- Step 2: Create indexes for the new columns (for performance during migration)
CREATE INDEX IF NOT EXISTS idx_web_crawler_data_embedding_384 ON web_crawler_data USING ivfflat (embedding_384 vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_team_member_data_embedding_384 ON team_member_data USING ivfflat (embedding_384 vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_google_classroom_coursework_embedding_384 ON google_classroom_coursework USING ivfflat (embedding_384 vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_google_classroom_announcements_embedding_384 ON google_classroom_announcements USING ivfflat (embedding_384 vector_cosine_ops);

-- Step 3: Update vector search functions to support both dimensions during transition
-- Note: The actual regeneration of embeddings will be done by a Python script

-- Step 4: After embeddings are regenerated, run these commands to switch to new columns:

-- ALTER TABLE web_crawler_data DROP COLUMN IF EXISTS embedding;
-- ALTER TABLE web_crawler_data RENAME COLUMN embedding_384 TO embedding;
--
-- ALTER TABLE team_member_data DROP COLUMN IF EXISTS embedding;
-- ALTER TABLE team_member_data RENAME COLUMN embedding_384 TO embedding;
--
-- ALTER TABLE google_classroom_coursework DROP COLUMN IF EXISTS embedding;
-- ALTER TABLE google_classroom_coursework RENAME COLUMN embedding_384 TO embedding;
--
-- ALTER TABLE google_classroom_announcements DROP COLUMN IF EXISTS embedding;
-- ALTER TABLE google_classroom_announcements RENAME COLUMN embedding_384 TO embedding;

-- Step 5: Recreate indexes on the renamed columns
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_web_crawler_data_embedding ON web_crawler_data USING ivfflat (embedding vector_cosine_ops);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_team_member_data_embedding ON team_member_data USING ivfflat (embedding vector_cosine_ops);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_google_classroom_coursework_embedding ON google_classroom_coursework USING ivfflat (embedding vector_cosine_ops);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_google_classroom_announcements_embedding ON google_classroom_announcements USING ivfflat (embedding vector_cosine_ops);

-- Verification queries (run after migration):
-- SELECT 'web_crawler_data' as table_name, count(*) as records_with_embeddings FROM web_crawler_data WHERE embedding IS NOT NULL;
-- SELECT 'team_member_data' as table_name, count(*) as records_with_embeddings FROM team_member_data WHERE embedding IS NOT NULL;
-- SELECT 'google_classroom_coursework' as table_name, count(*) as records_with_embeddings FROM google_classroom_coursework WHERE embedding IS NOT NULL;
-- SELECT 'google_classroom_announcements' as table_name, count(*) as records_with_embeddings FROM google_classroom_announcements WHERE embedding IS NOT NULL;




