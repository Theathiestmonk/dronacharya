# AI engagement analytics

## What we measure

- **Engagement** is defined as one count per **successful** response from the school’s **chatbot API** (`POST /chatbot`). This is logged in the `ai_chat_events` table (no message text stored by default).
- **Signed-in users with old data**: the admin **Analytics** view also **merges in** an estimate from `public.chat_sessions` (number of `sender: "bot"` messages in each row’s `messages` JSON, bucketed to a calendar day from session timestamps). This fills the chart when `ai_chat_events` is still empty, and is **excluded** for sessions that were last updated **after** the first server `ai_chat_events` row so the same activity is not double counted.
- **Not included**: failed requests, client-only errors, or traffic that never hits the backend.
- **Guests** (no signed-in user) are only counted in `ai_chat_events` when the API runs; `chat_sessions` is usually signed-in only.

## Where to view (client / school staff)

1. **In-app (recommended)**  
   Sign in with an account that has **admin** access, then open:  
   **`/admin/analytics`**  
   Example: `https://<your-app-domain>/admin/analytics`  
   You will see:
   - Totals for the **last 7 days** vs the **previous 7 days**
   - **Percent change** week over week (when the previous week had data)
   - A **daily line chart** with a **range control** (e.g. 28 / 42 / 90 days). The app syncs the choice to the URL as `?days=`, so you can bookmark or share a link.
   - **Export CSV** (current view): KPIs, one row per day in the line chart, and (if available) all question-theme rows. UTF-8 with BOM for Excel.
   - **Question theme** analytics: keyword buckets over **user** lines in saved `chat_sessions` (same broad lookback as the backend), with summary stats — **top category**, **share in “General / other”** (no keyword match), and **average user messages per session** — plus a horizontal bar chart (top 12 categories by count). This is an estimate, not a transcript, and is tuned for school topics (homework, exams, schedule, Prakriti, etc.); you can adjust keywords in `backend/app/utils/ai_chat_analytics.py`.

2. **Supabase (advanced)**  
   In the Supabase project → **SQL Editor**, you can query aggregates, for example:

   ```sql
   -- Daily counts for the last 14 days (UTC)
   select
     date_trunc('day', created_at at time zone 'UTC')::date as day,
     count(*) as responses
   from public.ai_chat_events
   where created_at >= now() - interval '14 days'
   group by 1
   order by 1;
   ```

   You can connect the same database to **Metabase**, **Grafana**, or a spreadsheet via a read-only role (set up in Supabase / your infra policy).

## Deployment note

Apply the table to your database by running the SQL in:

`backend/migrations/ai_chat_events.sql`

Until that migration has been applied, inserts from the API are ignored (fail open) and charts may be empty.
