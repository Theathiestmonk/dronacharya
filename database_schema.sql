-- User Profiles Table
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'teacher', 'parent')),
  email VARCHAR(255) NOT NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  gender VARCHAR(20) CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
  phone VARCHAR(20),
  date_of_birth DATE,
  profile_picture_url TEXT,
  
  -- Student specific fields
  grade VARCHAR(10),
  student_id VARCHAR(50),
  subjects TEXT[], -- Array of subjects
  learning_goals TEXT,
  interests TEXT[],
  learning_style VARCHAR(50),
  special_needs TEXT,
  emergency_contact_name VARCHAR(100),
  emergency_contact_phone VARCHAR(20),
  
  -- Teacher specific fields
  employee_id VARCHAR(50),
  department VARCHAR(100),
  subjects_taught TEXT[], -- Array of subjects taught
  years_of_experience INTEGER,
  qualifications TEXT,
  specializations TEXT[],
  office_location VARCHAR(100),
  office_hours TEXT,
  
  -- Parent specific fields
  relationship_to_student VARCHAR(50), -- 'mother', 'father', 'guardian', etc.
  occupation VARCHAR(100),
  workplace VARCHAR(100),
  preferred_contact_method VARCHAR(20), -- 'email', 'phone', 'sms'
  communication_preferences TEXT,
  
  -- Common fields
  address TEXT,
  city VARCHAR(100),
  state VARCHAR(100),
  postal_code VARCHAR(20),
  country VARCHAR(100) DEFAULT 'India',
  preferred_language VARCHAR(10) DEFAULT 'en',
  timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
  
  -- System fields
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  onboarding_completed BOOLEAN DEFAULT false,
  
  -- Constraints
  UNIQUE(user_id),
  UNIQUE(email)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON user_profiles(role);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_grade ON user_profiles(grade) WHERE grade IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_user_profiles_department ON user_profiles(department) WHERE department IS NOT NULL;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view their own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Create a view for easy access to user data
CREATE OR REPLACE VIEW user_profile_view AS
SELECT 
    up.*,
    au.email as auth_email,
    au.email_confirmed_at,
    au.last_sign_in_at
FROM user_profiles up
LEFT JOIN auth.users au ON up.user_id = au.id;

-- Grant permissions
GRANT ALL ON user_profiles TO authenticated;
GRANT ALL ON user_profile_view TO authenticated;
