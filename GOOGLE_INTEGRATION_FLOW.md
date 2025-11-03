# Google Classroom & Calendar Integration Flow

## Complete Connection Flow

### Step 1: User Initiates Connection
**Location:** `AdminDashboard.tsx`

1. Admin user clicks "Connect Google Services" button
2. Function: `connectGoogleService('both')` is called
3. Passes current user's email: `profile?.email` (e.g., `dummy@learners.prakriti.org.in`)

### Step 2: Generate OAuth URL
**Flow:** Frontend → Next.js API → FastAPI Backend

1. **Frontend** (`AdminDashboard.tsx`):
   ```typescript
   GET /api/admin/auth-url?service=both&email=dummy@learners.prakriti.org.in
   ```

2. **Next.js API** (`/api/admin/auth-url.ts`):
   - Proxies request to FastAPI backend
   - `GET http://localhost:8000/api/admin/auth-url?service=both`

3. **FastAPI Backend** (`backend/app/routes/admin.py`):
   - Reads `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from backend `.env`
   - Generates OAuth URL with scopes:
     - **Classroom:** `https://www.googleapis.com/auth/classroom.courses.readonly`
     - **Classroom:** `https://www.googleapis.com/auth/classroom.rosters.readonly`
     - **Calendar:** `https://www.googleapis.com/auth/calendar.readonly`
     - **Calendar:** `https://www.googleapis.com/auth/calendar.events.readonly`
   - Includes `redirect_uri`: `http://localhost:3000/admin/callback`
   - Returns OAuth URL

4. **Frontend**: Redirects user to Google OAuth consent screen

### Step 3: Google OAuth Authorization
**Location:** Google's servers

1. User sees Google consent screen
2. User grants permissions for Classroom and Calendar
3. Google redirects back with:
   - `code`: Authorization code (temporary, one-time use)
   - `state`: Service type (`both`, `classroom`, or `calendar`)
   - `error`: (if user denied)

### Step 4: Handle OAuth Callback
**Flow:** Google → Frontend Callback Page → Next.js API → Supabase

1. **Google Redirects To:**
   ```
   http://localhost:3000/admin/callback?code=AUTH_CODE&state=both
   ```

2. **Frontend Callback Page** (`/admin/callback/page.tsx`):
   - Waits for user profile to load (with retry mechanism)
   - Extracts `code` and `state` from URL
   - Gets current user's email from `useAuth()` context
   - Sends to Next.js API:
   ```typescript
   POST /api/admin/callback
   Body: {
     code: "AUTH_CODE",
     state: "both",
     adminEmail: "dummy@learners.prakriti.org.in"
   }
   ```

3. **Next.js API** (`/api/admin/callback.ts`):
   - **Validates:** Requires `adminEmail` (no fallback to first admin)
   - **Finds Admin:** Queries `user_profiles` table:
     ```sql
     SELECT * FROM user_profiles 
     WHERE email = 'dummy@learners.prakriti.org.in' 
       AND admin_privileges = true 
       AND is_active = true
     ```
   - **Exchanges Code:** Calls Google Token API:
     ```typescript
     POST https://oauth2.googleapis.com/token
     Body: {
       client_id: GOOGLE_CLIENT_ID,
       client_secret: GOOGLE_CLIENT_SECRET,
       code: "AUTH_CODE",
       grant_type: "authorization_code",
       redirect_uri: "http://localhost:3000/admin/callback"
     }
     ```
   - **Receives Tokens:**
     ```json
     {
       "access_token": "ya29...",
       "refresh_token": "1//0g...",
       "expires_in": 3600,
       "scope": "https://www.googleapis.com/auth/classroom...",
       "token_type": "Bearer"
     }
     ```

4. **Store in Supabase** (`google_integrations` table):
   - **Deactivates** old integrations for this admin
   - **Inserts** new integration records:
     ```typescript
     // For 'both' service, creates 2 records:
     
     // Record 1: Classroom
     INSERT INTO google_integrations (
       admin_id,           // UUID from user_profiles.id
       service_type,       // 'classroom'
       access_token,       // OAuth access token
       refresh_token,      // OAuth refresh token
       token_expires_at,   // Current time + expires_in
       scope,              // Classroom scopes
       is_active           // true
     )
     
     // Record 2: Calendar
     INSERT INTO google_integrations (
       admin_id,           // Same UUID
       service_type,       // 'calendar'
       access_token,       // Same access token
       refresh_token,      // Same refresh token
       token_expires_at,   // Current time + expires_in
       scope,              // Calendar scopes
       is_active           // true
     )
     ```

5. **Success Response:**
   ```json
   {
     "success": true,
     "message": "Integration completed successfully for dummy@learners.prakriti.org.in"
   }
   ```

6. **Frontend:** Redirects to `/admin?connected=true`

---

## Data Stored in Supabase

### 1. `google_integrations` Table

**Schema:**
```sql
CREATE TABLE google_integrations (
  id SERIAL PRIMARY KEY,
  admin_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
  service_type VARCHAR(20) CHECK (service_type IN ('classroom', 'calendar')),
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  scope TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Example Data Stored:**
```json
{
  "id": 25,
  "admin_id": "4acd852f-c769-48ee-8da6-23c1dbaf53c9",  // User's UUID
  "service_type": "classroom",
  "access_token": "ya29.a0ATi6K2...",  // Valid for ~1 hour
  "refresh_token": "1//0g1n6KmQ1...",  // Valid indefinitely
  "token_expires_at": "2025-10-29T09:43:59.053341+00:00",
  "scope": "https://www.googleapis.com/auth/classroom.courses.readonly https://www.googleapis.com/auth/classroom.rosters.readonly",
  "is_active": true,
  "created_at": "2025-10-29T08:44:00.615643+00:00",
  "updated_at": "2025-10-29T08:44:00.615643+00:00"
}
```

**Notes:**
- Each admin can have **2 active integrations** (one for classroom, one for calendar)
- `admin_id` links to `user_profiles.id` (UUID)
- `access_token` expires in ~1 hour, `refresh_token` doesn't expire
- `is_active` flag allows soft deletion

---

### 2. Data Sync Flow

### Step 1: User Clicks "Sync Classroom Data" or "Sync Calendar Data"

**Location:** `AdminDashboard.tsx`

```typescript
POST /api/admin/sync/classroom
// or
POST /api/admin/sync/calendar

Body: {
  adminEmail: "dummy@learners.prakriti.org.in"
}
```

### Step 2: Next.js Sync API (`/api/admin/sync/[service].ts`)

1. **Find Admin Profile:**
   - Checks if provided email has `admin_privileges=true`
   - Falls back to first available admin if not found

2. **Get Active Integration:**
   ```sql
   SELECT * FROM google_integrations
   WHERE admin_id = 'CURRENT_USER_UUID'
     AND service_type = 'classroom'  -- or 'calendar'
     AND is_active = true
   LIMIT 1
   ```

3. **Check Token Expiry:**
   - If expired, refresh token (TODO: currently skipped)

4. **Fetch from Google API:**

   **For Classroom:**
   ```typescript
   GET https://classroom.googleapis.com/v1/courses
   Headers: {
     Authorization: `Bearer ${access_token}`
   }
   ```

   **For Calendar:**
   ```typescript
   GET https://www.googleapis.com/calendar/v3/calendars/primary/events
     ?timeMin=2025-10-29T00:00:00Z
     &timeMax=2025-11-28T00:00:00Z
     &singleEvents=true
     &orderBy=startTime
   Headers: {
     Authorization: `Bearer ${access_token}`
   }
   ```

5. **Store in Supabase:**

### `classroom_data` Table

**Schema:**
```sql
CREATE TABLE classroom_data (
  id SERIAL PRIMARY KEY,
  admin_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
  course_id VARCHAR(255) NOT NULL,
  course_name VARCHAR(500) NOT NULL,
  course_description TEXT,
  course_room VARCHAR(500),
  course_section VARCHAR(500),
  course_state VARCHAR(50),
  teacher_email VARCHAR(255),
  student_count INTEGER DEFAULT 0,
  raw_data JSONB,  -- Full course object from Google API
  last_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Example Data:**
```json
{
  "id": 1,
  "admin_id": "4acd852f-c769-48ee-8da6-23c1dbaf53c9",
  "course_id": "1234567890",
  "course_name": "Mathematics 101",
  "course_description": "Introduction to Mathematics",
  "course_room": "Room 205",
  "course_section": "Section A",
  "course_state": "ACTIVE",
  "teacher_email": "teacher@school.com",
  "student_count": 25,
  "raw_data": { /* Full Google Classroom course object */ },
  "last_synced": "2025-10-29T08:44:00.000Z"
}
```

### `calendar_data` Table

**Schema:**
```sql
CREATE TABLE calendar_data (
  id SERIAL PRIMARY KEY,
  admin_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
  event_id VARCHAR(255) NOT NULL,
  event_title VARCHAR(500),
  event_description TEXT,
  event_start TIMESTAMP WITH TIME ZONE,
  event_end TIMESTAMP WITH TIME ZONE,
  event_location VARCHAR(500),
  event_status VARCHAR(50),
  calendar_id VARCHAR(255) DEFAULT 'primary',
  raw_data JSONB,  -- Full event object from Google API
  last_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Example Data:**
```json
{
  "id": 1,
  "admin_id": "4acd852f-c769-48ee-8da6-23c1dbaf53c9",
  "event_id": "abc123def456",
  "event_title": "Team Meeting",
  "event_description": "Weekly team sync",
  "event_start": "2025-10-30T10:00:00Z",
  "event_end": "2025-10-30T11:00:00Z",
  "event_location": "Conference Room A",
  "event_status": "CONFIRMED",
  "calendar_id": "primary",
  "raw_data": { /* Full Google Calendar event object */ },
  "last_synced": "2025-10-29T08:44:00.000Z"
}
```

**Sync Process:**
1. **Deletes** existing data for current admin
2. **Inserts** new synced data
3. Each sync **replaces** all previous data (not incremental)

---

## Integration Status Check Flow

### API: `GET /api/admin/integrations?email=dummy@learners.prakriti.org.in`

**Location:** `/api/admin/integrations.ts`

**Process:**
1. Finds admin profile by email with `admin_privileges=true`
2. Checks for integrations:
   ```sql
   -- First: Check current user's integrations
   SELECT * FROM google_integrations
   WHERE admin_id = 'CURRENT_USER_UUID'
     AND is_active = true
   
   -- Fallback: If none found, check all admins
   SELECT * FROM google_integrations
   WHERE admin_id IN (
     SELECT id FROM user_profiles 
     WHERE admin_privileges = true AND is_active = true
   )
   AND is_active = true
   ```

3. Determines status:
   ```typescript
   classroom_enabled = integrations.some(i => i.service_type === 'classroom')
   calendar_enabled = integrations.some(i => i.service_type === 'calendar')
   ```

4. Returns:
   ```json
   {
     "classroom_enabled": true,
     "calendar_enabled": true,
     "integrations": [
       {
         "id": 25,
         "admin_id": "4acd852f-c769-48ee-8da6-23c1dbaf53c9",
         "service_type": "classroom",
         // ... rest of integration data
       },
       {
         "id": 26,
         "admin_id": "4acd852f-c769-48ee-8da6-23c1dbaf53c9",
         "service_type": "calendar",
         // ... rest of integration data
       }
     ]
   }
   ```

---

## Key Points

### ✅ Current Behavior (After Fix):
- **Connections are stored under the logged-in user's `admin_id`**
- **Each admin has their own integrations**
- **Falls back to shared integrations only if current user has none**

### 🔑 Important Fields:

**`google_integrations` table:**
- `admin_id`: **UUID** from `user_profiles.id` (links to admin user)
- `service_type`: `'classroom'` or `'calendar'`
- `access_token`: Short-lived (~1 hour), used for API calls
- `refresh_token`: Long-lived, used to get new access tokens
- `is_active`: Allows deactivating without deleting

**`classroom_data` table:**
- `admin_id`: Links to the admin who synced this data
- `raw_data`: Full course JSON from Google API (for reference)

**`calendar_data` table:**
- `admin_id`: Links to the admin who synced this data
- `raw_data`: Full event JSON from Google API (for reference)

### 🔄 Token Refresh (Future):
- When `access_token` expires, use `refresh_token` to get new token
- Currently not implemented, but tokens last ~1 hour
- Should refresh before expiry for continuous access

---

## Complete Flow Diagram

```
User clicks "Connect Google Services"
    ↓
AdminDashboard → /api/admin/auth-url?service=both&email=USER_EMAIL
    ↓
Next.js API → FastAPI Backend → Google OAuth URL
    ↓
User redirected to Google consent screen
    ↓
User grants permissions
    ↓
Google redirects: /admin/callback?code=AUTH_CODE&state=both
    ↓
Callback Page → POST /api/admin/callback { code, state, adminEmail }
    ↓
Exchange code for tokens (Google Token API)
    ↓
Store in google_integrations table (2 records: classroom + calendar)
    ↓
Redirect to /admin?connected=true
    ↓
Dashboard shows "Connected" status

---
Later: User clicks "Sync Classroom Data"
    ↓
POST /api/admin/sync/classroom { adminEmail }
    ↓
Get integration from google_integrations table
    ↓
Use access_token to fetch from Google Classroom API
    ↓
Store courses in classroom_data table
    ↓
Dashboard shows synced courses count
```

---

## Key Architecture Decision

### Admin is a Feature, Not a Separate User

**Important:** Admin privileges (`admin_privileges=true`) are a **feature flag** on a user's profile, not a separate user entity. Each user must connect their own Google account and has their own integrations.

**Implementation:**
1. **No Fallback Logic:** APIs require the current user's email - no fallback to "first admin"
2. **User-Owned Integrations:** Each integration is stored under the current logged-in user's ID
3. **Independent Connections:** Each admin user connects their own Google Classroom/Calendar account
4. **No Shared Integrations:** Integrations are personal to each user

**Benefits:**
- Clear ownership: each user's integrations are under their own account
- No confusion about which admin's Google account is connected
- Better security: users can only access their own data
- Simpler logic: no fallback mechanisms needed

**To Connect:**
1. User with `admin_privileges=true` logs in
2. Clicks "Connect Google Services"
3. Integrations are stored under **their own user ID**, not a shared admin ID
4. Each admin can have their own Google Classroom/Calendar connection



