-- Add embedding columns to calendar events and submissions tables
-- Run this in Supabase SQL Editor

-- Add embedding column to google_calendar_events
ALTER TABLE google_calendar_events ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Add embedding column to google_classroom_submissions
ALTER TABLE google_classroom_submissions ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Create indexes for the new embedding columns
CREATE INDEX IF NOT EXISTS idx_google_calendar_events_embedding
ON google_calendar_events USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_google_classroom_submissions_embedding
ON google_classroom_submissions USING ivfflat (embedding vector_cosine_ops);




