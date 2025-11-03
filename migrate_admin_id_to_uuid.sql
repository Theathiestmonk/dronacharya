-- Migration: Change admin_id from INTEGER to UUID to work with user_profiles
-- Run this in Supabase SQL Editor

-- Step 1: Backup existing data (optional but recommended)
-- CREATE TABLE google_integrations_backup AS SELECT * FROM google_integrations;
-- CREATE TABLE classroom_data_backup AS SELECT * FROM classroom_data;
-- CREATE TABLE calendar_data_backup AS SELECT * FROM calendar_data;

-- Step 2: Drop foreign key constraints temporarily
ALTER TABLE google_integrations DROP CONSTRAINT IF EXISTS google_integrations_admin_id_fkey;
ALTER TABLE classroom_data DROP CONSTRAINT IF EXISTS classroom_data_admin_id_fkey;
ALTER TABLE calendar_data DROP CONSTRAINT IF EXISTS calendar_data_admin_id_fkey;

-- Step 3: Get first admin UUID for mapping
DO $$
DECLARE
    first_admin_uuid UUID;
BEGIN
    -- Get the first admin UUID
    SELECT id INTO first_admin_uuid 
    FROM user_profiles 
    WHERE admin_privileges = true 
    LIMIT 1;
    
    -- If no admin found, create a mapping
    IF first_admin_uuid IS NULL THEN
        RAISE EXCEPTION 'No admin user found. Please ensure at least one user has admin_privileges=true';
    END IF;
    
    -- For google_integrations: Map all existing admin_ids to the first admin UUID
    EXECUTE format('ALTER TABLE google_integrations ALTER COLUMN admin_id TYPE UUID USING %L::UUID', first_admin_uuid);

    -- For classroom_data
    EXECUTE format('ALTER TABLE classroom_data ALTER COLUMN admin_id TYPE UUID USING %L::UUID', first_admin_uuid);

    -- For calendar_data
    EXECUTE format('ALTER TABLE calendar_data ALTER COLUMN admin_id TYPE UUID USING %L::UUID', first_admin_uuid);
    
    RAISE NOTICE 'Successfully migrated all admin_id columns to UUID: %', first_admin_uuid;
END $$;

-- Step 4: Re-add foreign key constraints to user_profiles
ALTER TABLE google_integrations 
  ADD CONSTRAINT google_integrations_admin_id_fkey 
  FOREIGN KEY (admin_id) REFERENCES user_profiles(id) ON DELETE CASCADE;

ALTER TABLE classroom_data 
  ADD CONSTRAINT classroom_data_admin_id_fkey 
  FOREIGN KEY (admin_id) REFERENCES user_profiles(id) ON DELETE CASCADE;

ALTER TABLE calendar_data 
  ADD CONSTRAINT calendar_data_admin_id_fkey 
  FOREIGN KEY (admin_id) REFERENCES user_profiles(id) ON DELETE CASCADE;

-- Step 5: Verify the changes
SELECT 
  table_name,
  column_name,
  data_type
FROM information_schema.columns
WHERE table_name IN ('google_integrations', 'classroom_data', 'calendar_data')
  AND column_name = 'admin_id';

-- Success message
SELECT 'Migration completed! All admin_id columns are now UUID type and reference user_profiles table.' as status;


