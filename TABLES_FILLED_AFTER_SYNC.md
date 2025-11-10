# Tables Filled After Reconnect & Sync

## ✅ **After Reconnecting Google Services & Clicking Sync**

When you reconnect Google Classroom and/or Google Calendar and click the "Sync" button, the following tables will be automatically filled with data:

---

## 📚 **Google Classroom Tables (5 Tables)**

### 1. ✅ **`google_classroom_courses`**
**What Gets Stored:**
- Course ID (Google's course ID)
- Course name
- Description
- Section
- Room
- Description heading
- Update time
- Course state (ACTIVE, ARCHIVED, etc.)
- Enrollment code
- Alternate link
- Owner ID
- Teacher group email
- Course group email
- Guardians enabled status
- Calendar enabled status
- Max rosters
- Course material sets (JSONB)
- Gradebook settings (JSONB)
- Last synced timestamp

**When Filled:** Immediately when you click "Sync Classroom Data"

**Example Record:**
```json
{
  "course_id": "1234567890",
  "name": "Mathematics 101",
  "section": "Section A",
  "room": "Room 205",
  "description": "Introduction to Mathematics",
  "description_heading": "Course Overview",
  "course_state": "ACTIVE",
  "update_time": "2024-01-15T10:30:00Z"
}
```

---

### 2. ✅ **`google_classroom_teachers`**
**What Gets Stored:**
- Course ID (links to `google_classroom_courses.id`)
- User ID (Google's teacher user ID)
- Course user ID (unique ID for this course-teacher relationship)
- Profile (JSONB with full teacher profile including name, email, photo)
- Created/updated timestamps

**When Filled:** When syncing Classroom data (nested fetch per course)

**Example Record:**
```json
{
  "course_id": "uuid-of-course",
  "user_id": "teacher123@gmail.com",
  "course_user_id": "1234567890_teacher123@gmail.com",
  "profile": {
    "name": {
      "fullName": "John Smith",
      "givenName": "John",
      "familyName": "Smith"
    },
    "emailAddress": "john.smith@school.com",
    "photoUrl": "https://..."
  }
}
```

---

### 3. ✅ **`google_classroom_students`**
**What Gets Stored:**
- Course ID (links to `google_classroom_courses.id`)
- User ID (Google's student user ID)
- Course user ID (unique ID for this course-student relationship)
- Profile (JSONB with full student profile including name, email, photo)
- Student work folder (JSONB)
- Created/updated timestamps

**When Filled:** When syncing Classroom data (nested fetch per course)

**Example Record:**
```json
{
  "course_id": "uuid-of-course",
  "user_id": "student456@gmail.com",
  "course_user_id": "1234567890_student456@gmail.com",
  "profile": {
    "name": {
      "fullName": "Jane Doe",
      "givenName": "Jane",
      "familyName": "Doe"
    },
    "emailAddress": "jane.doe@school.com"
  },
  "student_work_folder": { ... }
}
```

---

### 4. ✅ **`google_classroom_announcements`**
**What Gets Stored:**
- Course ID (links to `google_classroom_courses.id`)
- Announcement ID (Google's announcement ID)
- Text (announcement content)
- Materials (JSONB array of files, links, etc.)
- State (PUBLISHED, DRAFT, DELETED)
- Alternate link
- Creation time
- Update time
- Scheduled time (if scheduled for future)
- Assignee mode
- Individual students options (JSONB)
- Creator user ID
- Course work type
- Last synced timestamp

**When Filled:** When syncing Classroom data (nested fetch per course)

**Example Record:**
```json
{
  "course_id": "uuid-of-course",
  "announcement_id": "ann_123456",
  "text": "Remember: Quiz on Friday!",
  "materials": [
    {
      "link": {
        "url": "https://example.com/quiz-info"
      }
    }
  ],
  "state": "PUBLISHED",
  "update_time": "2024-01-15T14:00:00Z"
}
```

---

### 5. ⚠️ **`google_classroom_coursework`** (Limited - Scope Deprecated)
**What SHOULD Get Stored (but may fail due to invalid scope):**
- Course ID (links to `google_classroom_courses.id`)
- Coursework ID (Google's coursework ID)
- Title
- Description
- Materials (JSONB)
- State (PUBLISHED, DRAFT)
- Alternate link
- Creation time
- Update time
- Due date
- Due time
- Max points
- Work type (ASSIGNMENT, QUIZ, etc.)
- Creator user ID
- Topic ID
- Grade category (JSONB)
- Assignment data (JSONB)
- Multiple choice question data (JSONB)
- Last synced timestamp

**When Filled:** ❌ **MAY FAIL** - Scope `classroom.coursework.readonly` is deprecated/invalid
**Status:** Table exists, but sync will likely get 403 error and this table will remain empty

---

### 6. ⚠️ **`google_classroom_submissions`** (Limited - Scope Deprecated)
**What SHOULD Get Stored (but may fail due to invalid scope):**
- Coursework ID (links to `google_classroom_coursework.id`)
- Submission ID (Google's submission ID)
- Course ID (Google's course ID string)
- Coursework ID (Google's coursework ID string)
- User ID (Google's student user ID)
- State (NEW, CREATED, TURNED_IN, RETURNED, etc.)
- Alternate link
- Assigned grade
- Draft grade
- Course work type
- Associated with developer flag
- Submission history (JSONB)
- **Late** (boolean - indicates if submission was late)
- Last synced timestamp

**When Filled:** ❌ **MAY FAIL** - Scope `classroom.student-submissions.readonly` is deprecated/invalid
**Status:** Table exists, but sync will likely get 403 error and this table will remain empty

---

## 📅 **Google Calendar Tables (2 Tables)**

### 7. ✅ **`google_calendar_calendars`**
**What Gets Stored:**
- User ID (links to `auth.users.id`)
- Calendar ID (Google's calendar ID)
- Summary (calendar name)
- Description
- Location
- Timezone
- Color ID
- Background color
- Foreground color
- Access role (OWNER, WRITER, READER, etc.)
- Selected (boolean - if calendar is selected)
- Primary calendar (boolean)
- Deleted (boolean)
- Conference properties (JSONB)
- Notification settings (JSONB)
- Last synced timestamp

**When Filled:** When you click "Sync Calendar Data"

**Example Record:**
```json
{
  "calendar_id": "primary",
  "summary": "My Calendar",
  "timezone": "Asia/Kolkata",
  "primary_calendar": true,
  "selected": true
}
```

---

### 8. ✅ **`google_calendar_events`**
**What Gets Stored:**
- User ID (links to `auth.users.id`)
- Event ID (Google's event ID)
- Calendar ID (Google's calendar ID)
- Summary (event title)
- Description
- Location
- Start time
- End time
- All day (boolean)
- Timezone
- Recurrence (JSONB - recurrence rules)
- Attendees (JSONB array)
- Creator (JSONB)
- Organizer (JSONB)
- HTML link
- **Hangout link** (Google Meet link)
- Conference data (JSONB)
- Visibility (PUBLIC, PRIVATE, etc.)
- Transparency (TRANSPARENT, OPAQUE)
- Status (CONFIRMED, TENTATIVE, CANCELLED)
- Event type
- Color ID
- Last synced timestamp

**When Filled:** When you click "Sync Calendar Data" (fetches events from last 90 days)

**Example Record:**
```json
{
  "event_id": "abc123def456",
  "calendar_id": "primary",
  "summary": "Team Meeting",
  "description": "Weekly team sync",
  "start_time": "2024-01-20T10:00:00Z",
  "end_time": "2024-01-20T11:00:00Z",
  "location": "Conference Room A",
  "hangout_link": "https://meet.google.com/abc-defg-hij"
}
```

---

## 🔗 **Support Tables**

### 9. ✅ **`google_integrations`**
**What Gets Stored:**
- Admin ID (links to `user_profiles.id`)
- Service type ('classroom' or 'calendar')
- Access token
- Refresh token
- Token expires at timestamp
- Scope (all granted scopes as text)
- Is active (boolean)
- Created/updated timestamps

**When Filled:** When you first connect Google Classroom/Calendar (during OAuth callback)

**Purpose:** Stores OAuth tokens for API access

---

## 📊 **Summary Table: What Gets Filled**

| Table Name | Status | When Filled | Notes |
|------------|--------|-------------|-------|
| `google_classroom_courses` | ✅ **FILLED** | Sync Classroom | All course data |
| `google_classroom_teachers` | ✅ **FILLED** | Sync Classroom | All teachers with profiles |
| `google_classroom_students` | ✅ **FILLED** | Sync Classroom | All students with profiles |
| `google_classroom_announcements` | ✅ **FILLED** | Sync Classroom | All announcements |
| `google_classroom_coursework` | ❌ **EMPTY** | Sync Classroom | Scope deprecated - 403 error |
| `google_classroom_submissions` | ❌ **EMPTY** | Sync Classroom | Scope deprecated - 403 error |
| `google_calendar_calendars` | ✅ **FILLED** | Sync Calendar | Calendar list |
| `google_calendar_events` | ✅ **FILLED** | Sync Calendar | Events (next 90 days) |
| `google_integrations` | ✅ **FILLED** | OAuth Connect | OAuth tokens |

---

## 🔄 **Sync Process Flow**

### **Step 1: Connect Google Classroom**
1. Click "Connect Google Classroom"
2. Authorize with Google
3. OAuth callback saves tokens → **`google_integrations`** table filled

### **Step 2: Sync Classroom Data**
1. Click "Sync Classroom Data"
2. Fetches courses → **`google_classroom_courses`** filled
3. For each course, fetches:
   - Teachers → **`google_classroom_teachers`** filled
   - Students → **`google_classroom_students`** filled
   - Announcements → **`google_classroom_announcements`** filled
   - Coursework → Attempts, but gets 403 error → **`google_classroom_coursework`** stays empty
   - Submissions → Attempts, but gets 403 error → **`google_classroom_submissions`** stays empty

### **Step 3: Connect Google Calendar**
1. Click "Connect Google Calendar"
2. Authorize with Google
3. OAuth callback saves tokens → **`google_integrations`** table updated

### **Step 4: Sync Calendar Data**
1. Click "Sync Calendar Data"
2. Fetches calendars → **`google_calendar_calendars`** filled
3. Fetches events from each calendar → **`google_calendar_events`** filled

---

## ✅ **Expected Results After Full Sync**

After completing all syncs, you should have:

**✅ 6 Tables Filled:**
1. ✅ `google_classroom_courses` - Your courses
2. ✅ `google_classroom_teachers` - All teachers
3. ✅ `google_classroom_students` - All students
4. ✅ `google_classroom_announcements` - Course announcements
5. ✅ `google_calendar_calendars` - Your calendars
6. ✅ `google_calendar_events` - Your events

**❌ 2 Tables Empty (Expected):**
7. ❌ `google_classroom_coursework` - Empty (scope issue)
8. ❌ `google_classroom_submissions` - Empty (scope issue)

**✅ 1 Support Table:**
9. ✅ `google_integrations` - OAuth tokens

---

## 🔍 **How to Verify Tables Are Filled**

Run these SQL queries in Supabase:

```sql
-- Check courses
SELECT COUNT(*) as course_count FROM google_classroom_courses;

-- Check teachers
SELECT COUNT(*) as teacher_count FROM google_classroom_teachers;

-- Check students
SELECT COUNT(*) as student_count FROM google_classroom_students;

-- Check announcements
SELECT COUNT(*) as announcement_count FROM google_classroom_announcements;

-- Check calendars
SELECT COUNT(*) as calendar_count FROM google_calendar_calendars;

-- Check events
SELECT COUNT(*) as event_count FROM google_calendar_events;

-- Check coursework (should be 0 due to scope issue)
SELECT COUNT(*) as coursework_count FROM google_classroom_coursework;

-- Check submissions (should be 0 due to scope issue)
SELECT COUNT(*) as submission_count FROM google_classroom_submissions;
```

---

## 📝 **Important Notes**

1. **Coursework & Submissions:** These tables will remain empty because Google deprecated the required scopes. This is expected behavior.

2. **Sync Frequency:** Data is synced when you click "Sync" button. You can sync again anytime to get latest updates.

3. **Upsert Logic:** The sync uses "upsert" (update or insert) - if a record exists, it updates it; if not, it creates a new one.

4. **Relationships:** All tables are properly linked:
   - Teachers/Students/Announcements link to Courses via `course_id`
   - Submissions link to Coursework via `coursework_id`
   - Events link to Calendars via `calendar_id`

5. **Last Synced:** Each table has `last_synced_at` timestamp showing when data was last updated.

---

## 🎯 **What Your Chatbot Can Access**

After sync, your chatbot can answer queries about:
- ✅ Courses (names, sections, rooms, descriptions)
- ✅ Teachers (names, emails)
- ✅ Students (names, emails)
- ✅ Announcements (content, materials, update times)
- ✅ Calendar events (titles, times, locations, Meet links)
- ❌ Coursework (not available - table empty)
- ❌ Submissions (not available - table empty)

---

**Total Tables That Will Be Filled: 6 out of 8 Classroom/Calendar tables**
**Support Table: 1 (`google_integrations`)**
**Grand Total: 7 tables with data after sync**

















