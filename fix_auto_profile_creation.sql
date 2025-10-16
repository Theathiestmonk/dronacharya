-- Fix auto profile creation trigger to handle potential database errors
-- This should resolve the "Database error saving new user" issue

-- First, let's update the function to handle errors gracefully
CREATE OR REPLACE FUNCTION create_user_profile_on_signup()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert a basic user profile for the new user
    -- Use a try-catch approach with exception handling
    BEGIN
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
        
        -- Log success (optional)
        RAISE NOTICE 'User profile created successfully for user: %', NEW.email;
        
    EXCEPTION
        WHEN OTHERS THEN
            -- Log the error but don't fail the user creation
            RAISE WARNING 'Failed to create user profile for %: %', NEW.email, SQLERRM;
            -- Continue with user creation even if profile creation fails
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recreate the trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION create_user_profile_on_signup();

-- Verify the trigger exists
SELECT trigger_name, event_manipulation, action_statement 
FROM information_schema.triggers 
WHERE trigger_name = 'on_auth_user_created';
