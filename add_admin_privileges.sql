-- Add admin privileges column to user_profiles table
-- This separates admin system privileges from user roles (student/teacher/parent)

-- Add admin_privileges column
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS admin_privileges BOOLEAN DEFAULT false;

-- Add index for admin privileges
CREATE INDEX IF NOT EXISTS idx_user_profiles_admin_privileges ON user_profiles(admin_privileges);

-- Update the role constraint to remove 'admin' if it exists
-- First, let's check if there are any users with 'admin' role and convert them
UPDATE user_profiles 
SET admin_privileges = true, role = 'teacher'
WHERE role = 'admin';

-- Now update the constraint to only allow student, teacher, parent
ALTER TABLE user_profiles 
DROP CONSTRAINT IF EXISTS user_profiles_role_check;

ALTER TABLE user_profiles 
ADD CONSTRAINT user_profiles_role_check 
CHECK (role IN ('student', 'teacher', 'parent'));

-- Create a policy for admin access
CREATE POLICY "Admins can view all profiles" ON user_profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles up 
            WHERE up.user_id = auth.uid() 
            AND up.admin_privileges = true
        )
    );

CREATE POLICY "Admins can update all profiles" ON user_profiles
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM user_profiles up 
            WHERE up.user_id = auth.uid() 
            AND up.admin_privileges = true
        )
    );

-- Create a view for admin management
CREATE OR REPLACE VIEW admin_user_view AS
SELECT 
    up.*,
    au.email as auth_email,
    au.email_confirmed_at,
    au.last_sign_in_at,
    CASE 
        WHEN up.admin_privileges = true THEN 'Admin'
        ELSE up.role
    END as display_role
FROM user_profiles up
LEFT JOIN auth.users au ON up.user_id = au.id
WHERE up.is_active = true;

-- Grant permissions
GRANT ALL ON admin_user_view TO authenticated;






















