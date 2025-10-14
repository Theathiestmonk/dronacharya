# Quick Start Guide

## The loading issue has been fixed! 🎉

The page was stuck on loading because the authentication system was trying to connect to Supabase without proper environment variables. I've added fallback handling so the app works even without Supabase configured.

## How to run the app:

### Option 1: Without Authentication (Simplest)
1. Just run the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. The app will work perfectly without any environment variables
3. Users can use the chatbot immediately without login

### Option 2: With Full Authentication Features
1. Set up Supabase (optional):
   - Create a Supabase project
   - Run the SQL from `database_schema.sql`
   - Add environment variables to `.env.local`:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
   ```

2. Set up Google OAuth (optional):
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google+ API
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Set authorized redirect URIs to: `https://your-project-ref.supabase.co/auth/v1/callback`
   - Copy the Client ID and Client Secret
   - In your Supabase dashboard, go to Authentication → Providers
   - Enable Google provider and add your OAuth credentials

3. Run the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m uvicorn app.main:app --reload --port 8000
   ```

3. Run the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## What's Fixed:

✅ **No More Loading Issues**: App loads immediately even without Supabase
✅ **Graceful Fallbacks**: Authentication features disabled when Supabase not available
✅ **Public Access**: Anyone can use the chatbot without login
✅ **Optional Login**: Users can still login for personalized experience
✅ **Error Handling**: Proper timeout and error handling

## Features Available:

### Without Supabase:
- ✅ Full chatbot functionality
- ✅ Public access for all users
- ✅ All school information and features
- ❌ User authentication
- ❌ Personalized responses
- ❌ User profiles

### With Supabase:
- ✅ Everything above PLUS:
- ✅ User registration and login
- ✅ Google OAuth sign-in
- ✅ Personalized chatbot responses
- ✅ User profiles and onboarding
- ✅ Role-based experiences

The app is now much more robust and will work in any configuration! 🚀
