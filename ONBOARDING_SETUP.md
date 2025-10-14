# Onboarding System Setup Guide

This guide will help you set up the comprehensive onboarding system for the Prakriti School chatbot.

## Overview

The onboarding system includes:
- **Role-based forms** for Students, Teachers, and Parents
- **Personalized chatbot responses** based on user profiles
- **Supabase integration** for data storage
- **Multi-step form flow** with validation

## Database Setup

### 1. Create Supabase Project
1. Go to [Supabase](https://supabase.com) and create a new project
2. Note down your project URL and anon key

### 2. Run Database Schema
Execute the SQL commands from `database_schema.sql` in your Supabase SQL editor:

```sql
-- Copy and paste the entire content of database_schema.sql
-- This will create the user_profiles table with all necessary fields
```

### 3. Environment Variables
Add these to your `.env.local` file:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Backend Configuration
BACKEND_URL=http://localhost:8000
```

## Features

### 1. Role-Based Onboarding Forms

#### Student Form Fields:
- Basic info (name, phone, address)
- Grade and Student ID
- Subjects and Learning Goals
- Interests and Learning Style
- Special Needs
- Emergency Contact

#### Teacher Form Fields:
- Basic info (name, phone, address)
- Employee ID and Department
- Subjects Taught
- Years of Experience
- Qualifications and Specializations
- Office Location and Hours

#### Parent Form Fields:
- Basic info (name, phone, address)
- Relationship to Student
- Occupation and Workplace
- Preferred Contact Method
- Communication Preferences

### 2. Personalized Chatbot Responses

The chatbot now uses user profile data to provide personalized responses:
- Addresses users by their first name
- Tailors responses to their role (student/teacher/parent)
- References their grade, subjects, or department
- Considers their learning goals and interests
- Uses their preferred learning style for study suggestions

### 3. Multi-Step Form Flow

1. **Step 1**: Role selection (Student/Teacher/Parent)
2. **Step 2**: Basic information (name, contact, address)
3. **Step 3**: Role-specific information
4. **Completion**: Profile saved to Supabase

## File Structure

```
frontend/src/
├── components/
│   ├── OnboardingForm.tsx          # Main onboarding form component
│   ├── AuthFormWithOnboarding.tsx  # Auth form with onboarding integration
│   └── Chatbot.tsx                 # Updated chatbot with personalization
├── providers/
│   ├── AuthProvider.tsx            # Authentication and profile management
│   └── SupabaseProvider.tsx        # Supabase client provider
└── pages/api/
    ├── chatbot.ts                  # Updated API with user profile integration
    └── user-profile.ts             # User profile CRUD operations

backend/app/agents/
└── chatbot_agent.py                # Updated with personalized system prompts

database_schema.sql                 # Complete database schema
```

## Usage

### 1. User Registration Flow
1. User visits the application
2. If not authenticated, shows login/signup form
3. After authentication, checks if onboarding is completed
4. If not completed, shows role selection and onboarding form
5. After completion, user can access the personalized chatbot

### 2. Personalized Chatbot
- Chatbot responses are tailored based on user profile
- Students get grade-appropriate advice
- Teachers get department-specific information
- Parents get child-focused guidance

## API Endpoints

### User Profile API (`/api/user-profile`)
- `GET /api/user-profile?user_id={id}` - Get user profile
- `POST /api/user-profile` - Create user profile
- `PUT /api/user-profile` - Update user profile
- `DELETE /api/user-profile?user_id={id}` - Delete user profile

### Chatbot API (`/api/chatbot`)
- `POST /api/chatbot` - Send message with user profile context
- Automatically fetches user profile and includes in backend request

## Customization

### Adding New Fields
1. Update the database schema in `database_schema.sql`
2. Add field to the appropriate interface in `OnboardingForm.tsx`
3. Add form field in the corresponding role section
4. Update the backend system prompt in `chatbot_agent.py`

### Modifying Form Steps
1. Update the `currentStep` logic in `OnboardingForm.tsx`
2. Add new step content functions
3. Update the `canProceed()` validation logic

### Customizing Personalization
1. Modify the personalization section in `chatbot_agent.py`
2. Add new profile fields to the system prompt
3. Update the frontend to pass additional data

## Security

- Row Level Security (RLS) enabled on user_profiles table
- Users can only access their own profile data
- Service role key used for backend operations
- Input validation on all form fields

## Testing

1. **Test Registration Flow**:
   - Create new user accounts
   - Complete onboarding for each role
   - Verify profile data is saved correctly

2. **Test Personalization**:
   - Send messages as different user types
   - Verify responses are personalized
   - Check that role-specific information is referenced

3. **Test Form Validation**:
   - Try submitting incomplete forms
   - Verify required field validation
   - Test step progression logic

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Verify Supabase credentials
   - Check if RLS policies are correct
   - Ensure service role key has proper permissions

2. **Form Validation Issues**:
   - Check TypeScript types are correct
   - Verify field names match database schema
   - Test form state management

3. **Personalization Not Working**:
   - Verify user profile is being fetched
   - Check backend system prompt includes personalization
   - Ensure user_id is being passed correctly

### Debug Steps

1. Check browser console for errors
2. Verify Supabase data in dashboard
3. Check backend logs for personalization data
4. Test API endpoints directly

## Future Enhancements

- **Profile Picture Upload**: Add image upload functionality
- **Advanced Preferences**: More detailed user preferences
- **Analytics**: Track user engagement and form completion
- **Email Notifications**: Send welcome emails after onboarding
- **Profile Editing**: Allow users to update their profiles
- **Admin Dashboard**: Manage user profiles and analytics
