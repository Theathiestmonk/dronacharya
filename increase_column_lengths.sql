-- 1. Drop dependent views first (PostgreSQL requirement)
DROP VIEW IF EXISTS admin_user_view;
DROP VIEW IF EXISTS user_profile_view;

-- 2. Increase the length of the grade and preferred_language columns
ALTER TABLE user_profiles 
ALTER COLUMN grade TYPE VARCHAR(20),
ALTER COLUMN preferred_language TYPE VARCHAR(20);

-- 3. Recreate user_profile_view
CREATE OR REPLACE VIEW user_profile_view AS
SELECT 
    up.*,
    au.email as auth_email,
    au.email_confirmed_at,
    au.last_sign_in_at
FROM user_profiles up
LEFT JOIN auth.users au ON up.user_id = au.id;

-- 4. Recreate admin_user_view
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

-- 5. Restore permissions
GRANT ALL ON user_profile_view TO authenticated;
GRANT ALL ON admin_user_view TO authenticated;

