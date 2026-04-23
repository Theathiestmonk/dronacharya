-- AI chat engagement analytics: one row per successful chatbot API response (Option A, plan).
-- Run in Supabase SQL Editor or via migration tooling.
-- Metric: "engagement" = count of completed AI responses logged server-side (excludes failed requests).

CREATE TABLE IF NOT EXISTS public.ai_chat_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  user_id uuid NULL REFERENCES auth.users(id) ON DELETE SET NULL,
  is_authenticated boolean NOT NULL DEFAULT false,
  source text NOT NULL DEFAULT 'web'
);

COMMENT ON TABLE public.ai_chat_events IS 'One row per successful /chatbot response; used for school-wide engagement analytics (not per-message content).';
COMMENT ON COLUMN public.ai_chat_events.is_authenticated IS 'True if request included a signed-in user_id.';
COMMENT ON COLUMN public.ai_chat_events.source IS 'Client channel, e.g. web, embed.';

CREATE INDEX IF NOT EXISTS idx_ai_chat_events_created_at ON public.ai_chat_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_chat_events_user_id ON public.ai_chat_events (user_id) WHERE user_id IS NOT NULL;

-- RLS: no policies for anonymous/authenticated JWT — only service role (backend) reads/writes.
ALTER TABLE public.ai_chat_events ENABLE ROW LEVEL SECURITY;
