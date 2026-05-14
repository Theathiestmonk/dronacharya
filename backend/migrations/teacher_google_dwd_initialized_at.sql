-- One-time onboarding DWD bootstrap for teachers (set by Next.js /api/user-profile after sync attempts).
-- Apply in Supabase SQL Editor alongside other migrations.

ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS teacher_google_dwd_initialized_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN public.user_profiles.teacher_google_dwd_initialized_at IS
  'Set after first onboarding-triggered Classroom+Calendar DWD sync was requested for this teacher.';
