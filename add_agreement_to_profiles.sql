-- Add agreement timestamp to user profiles
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS agreed_to_terms_at TIMESTAMP WITH TIME ZONE;

-- 2. Update the auto-profile creation trigger to handle both Google and Email signups
CREATE OR REPLACE FUNCTION create_user_profile_on_signup()
RETURNS TRIGGER AS $$
DECLARE
    agreement_time TIMESTAMP WITH TIME ZONE;
BEGIN
    -- AUTOMATIC AGREEMENT LOGIC:
    -- 1. If provider is Google, set agreement to NOW() automatically
    -- 2. If provider is email, take it from the signup form metadata
    IF (NEW.raw_app_meta_data->>'provider' = 'google') THEN
        agreement_time := NOW();
    ELSE
        agreement_time := (NEW.raw_user_meta_data->>'agreed_to_terms_at')::TIMESTAMP WITH TIME ZONE;
    END IF;

    BEGIN
        INSERT INTO user_profiles (
            user_id,
            email,
            role,
            first_name,
            last_name,
            is_active,
            onboarding_completed,
            agreed_to_terms_at
        ) VALUES (
            NEW.id,
            NEW.email,
            'student',
            COALESCE(NEW.raw_user_meta_data->>'first_name', 'User'),
            COALESCE(NEW.raw_user_meta_data->>'last_name', 'User'),
            true,
            false,
            agreement_time
        );
        
        RAISE NOTICE 'User profile created with agreement status for user: %', NEW.email;
        
    EXCEPTION
        WHEN OTHERS THEN
            RAISE WARNING 'Failed to create user profile for %: %', NEW.email, SQLERRM;
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

