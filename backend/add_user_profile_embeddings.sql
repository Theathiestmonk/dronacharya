-- Add embedding column to user_profiles table for onboarding profile data
-- Run this in Supabase SQL Editor

-- Add embedding column to user_profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Create index for the embedding column
CREATE INDEX IF NOT EXISTS idx_user_profiles_embedding
ON user_profiles USING ivfflat (embedding vector_cosine_ops);

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS match_user_profiles(vector(384), float, int);

-- Create search function for user profiles
CREATE FUNCTION match_user_profiles(
  query_embedding vector(384),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  user_id uuid,
  first_name text,
  last_name text,
  email text,
  role text,
  grade text,
  learning_goals text,
  interests text,
  subjects text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    up.id,
    up.user_id,
    up.first_name,
    up.last_name,
    up.email,
    up.role,
    up.grade,
    up.learning_goals,
    up.interests::text,
    up.subjects::text,
    1 - (up.embedding <=> query_embedding) as similarity
  FROM user_profiles up
  WHERE up.embedding IS NOT NULL
    AND up.is_active = true
    AND 1 - (up.embedding <=> query_embedding) > match_threshold
  ORDER BY up.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
