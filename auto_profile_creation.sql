-- Create a function to automatically create user profile on signup
CREATE OR REPLACE FUNCTION create_user_profile_on_signup()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert a basic user profile for the new user
    INSERT INTO user_profiles (
        user_id,
        email,
        role,
        first_name,
        last_name,
        is_active,
        onboarding_completed
    ) VALUES (
        NEW.id,
        NEW.email,
        'student', -- Default role, can be changed later
        COALESCE(NEW.raw_user_meta_data->>'first_name', 'User'),
        COALESCE(NEW.raw_user_meta_data->>'last_name', 'User'),
        true,
        false -- Not completed onboarding yet
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to run the function after user signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION create_user_profile_on_signup();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON user_profiles TO postgres, anon, authenticated, service_role;
GRANT ALL ON auth.users TO postgres, anon, authenticated, service_role;



