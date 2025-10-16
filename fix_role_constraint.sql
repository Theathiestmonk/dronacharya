-- Fix role constraint to allow 'admin' role
-- This fixes the "Database error saving new user" issue

-- Update the role constraint to include 'admin'
ALTER TABLE user_profiles 
DROP CONSTRAINT IF EXISTS user_profiles_role_check;

ALTER TABLE user_profiles 
ADD CONSTRAINT user_profiles_role_check 
CHECK (role IN ('student', 'teacher', 'parent', 'admin'));

-- Verify the constraint was updated (simplified query)
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'user_profiles'::regclass 
AND conname = 'user_profiles_role_check';
