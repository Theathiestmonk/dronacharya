# Required Google OAuth Scopes

## ✅ **REQUIRED SCOPES** (Currently in Code)

### For Google Classroom Sync:
1. ✅ `https://www.googleapis.com/auth/classroom.courses.readonly`
   - **Why:** Fetches course list and basic course information
   - **Used in:** Course sync API

2. ✅ `https://www.googleapis.com/auth/classroom.rosters.readonly`
   - **Why:** Fetches students and teachers for each course
   - **Used in:** Nested data fetch (students/teachers arrays)

3. ✅ `https://www.googleapis.com/auth/classroom.coursework.readonly`
   - **Why:** Fetches assignments/homework/quizzes for each course
   - **Used in:** Nested data fetch (coursework array)

### For Google Calendar Sync:
1. ✅ `https://www.googleapis.com/auth/calendar.readonly`
   - **Why:** Basic calendar read access
   - **Used in:** Calendar sync API

2. ✅ `https://www.googleapis.com/auth/calendar.events.readonly`
   - **Why:** Fetches calendar events
   - **Used in:** Event sync API

## ❌ **OPTIONAL SCOPES** (Can Remove if Not Needed)

1. ⚠️ `classroom.student-submissions.readonly`
   - **Status:** Optional - Only needed if you want to see student submission data
   - **Current:** Included in code but not strictly required
   - **Can remove?** Yes, if you don't need submission details

## 🗑️ **NOT NEEDED** (Can Delete from Google Console)

### You can REMOVE these if they appear in your Google Console:

**Classroom Scopes:**
- ❌ `classroom.courses` (write permission - you only need `readonly`)
- ❌ `classroom.announcements` (if you don't need announcements)
- ❌ `classroom.profile.emails` (if you don't need email profiles)
- ❌ `classroom.profile.photos` (if you don't need photos)
- ❌ `classroom.topics` (if you don't need topics)

**Calendar Scopes:**
- ❌ `calendar.calendars.readonly` (you already have `calendar.readonly`)
- ❌ `calendar.events.owned.readonly` (you already have `calendar.events.readonly`)
- ❌ `calendar.freebusy` (if you don't need availability checking)

**User Info Scopes (May be auto-added by Google):**
- ❌ `userinfo.email` (only if you're not using Supabase auth)
- ❌ `userinfo.profile` (only if you're not using Supabase auth)

## 📋 **Summary: MINIMUM Required Scopes**

**Total Required: 5 scopes**

```
✅ classroom.courses.readonly
✅ classroom.rosters.readonly
✅ classroom.coursework.readonly
✅ calendar.readonly
✅ calendar.events.readonly
```

Optional (can remove):
- ⚠️ classroom.student-submissions.readonly

## 🧹 **How to Clean Up Unused Scopes**

1. Go to Google Cloud Console
2. **APIs & Services** > **OAuth consent screen**
3. Click on each unused scope
4. Click the **trash can icon** to remove it
5. **Important:** Users will need to re-authorize after removing scopes

## ⚠️ **Important Notes**

1. **Don't remove scopes that are currently in use** - Your app will break
2. **After cleaning up, users must re-authorize** to get the updated permission set
3. **Some scopes might be required by Google** - If you try to delete and Google prevents it, keep it
4. **Test after cleanup** - Make sure sync still works with fewer scopes

## 🔍 **How to Verify What's Actually Used**

Check your code:
- `backend/app/routes/admin.py` - Lines 68-77 show what's requested
- Google Console shows what's been granted, which may include unused ones



## ✅ **REQUIRED SCOPES** (Currently in Code)

### For Google Classroom Sync:
1. ✅ `https://www.googleapis.com/auth/classroom.courses.readonly`
   - **Why:** Fetches course list and basic course information
   - **Used in:** Course sync API

2. ✅ `https://www.googleapis.com/auth/classroom.rosters.readonly`
   - **Why:** Fetches students and teachers for each course
   - **Used in:** Nested data fetch (students/teachers arrays)

3. ✅ `https://www.googleapis.com/auth/classroom.coursework.readonly`
   - **Why:** Fetches assignments/homework/quizzes for each course
   - **Used in:** Nested data fetch (coursework array)

### For Google Calendar Sync:
1. ✅ `https://www.googleapis.com/auth/calendar.readonly`
   - **Why:** Basic calendar read access
   - **Used in:** Calendar sync API

2. ✅ `https://www.googleapis.com/auth/calendar.events.readonly`
   - **Why:** Fetches calendar events
   - **Used in:** Event sync API

## ❌ **OPTIONAL SCOPES** (Can Remove if Not Needed)

1. ⚠️ `classroom.student-submissions.readonly`
   - **Status:** Optional - Only needed if you want to see student submission data
   - **Current:** Included in code but not strictly required
   - **Can remove?** Yes, if you don't need submission details

## 🗑️ **NOT NEEDED** (Can Delete from Google Console)

### You can REMOVE these if they appear in your Google Console:

**Classroom Scopes:**
- ❌ `classroom.courses` (write permission - you only need `readonly`)
- ❌ `classroom.announcements` (if you don't need announcements)
- ❌ `classroom.profile.emails` (if you don't need email profiles)
- ❌ `classroom.profile.photos` (if you don't need photos)
- ❌ `classroom.topics` (if you don't need topics)

**Calendar Scopes:**
- ❌ `calendar.calendars.readonly` (you already have `calendar.readonly`)
- ❌ `calendar.events.owned.readonly` (you already have `calendar.events.readonly`)
- ❌ `calendar.freebusy` (if you don't need availability checking)

**User Info Scopes (May be auto-added by Google):**
- ❌ `userinfo.email` (only if you're not using Supabase auth)
- ❌ `userinfo.profile` (only if you're not using Supabase auth)

## 📋 **Summary: MINIMUM Required Scopes**

**Total Required: 5 scopes**

```
✅ classroom.courses.readonly
✅ classroom.rosters.readonly
✅ classroom.coursework.readonly
✅ calendar.readonly
✅ calendar.events.readonly
```

Optional (can remove):
- ⚠️ classroom.student-submissions.readonly

## 🧹 **How to Clean Up Unused Scopes**

1. Go to Google Cloud Console
2. **APIs & Services** > **OAuth consent screen**
3. Click on each unused scope
4. Click the **trash can icon** to remove it
5. **Important:** Users will need to re-authorize after removing scopes

## ⚠️ **Important Notes**

1. **Don't remove scopes that are currently in use** - Your app will break
2. **After cleaning up, users must re-authorize** to get the updated permission set
3. **Some scopes might be required by Google** - If you try to delete and Google prevents it, keep it
4. **Test after cleanup** - Make sure sync still works with fewer scopes

## 🔍 **How to Verify What's Actually Used**

Check your code:
- `backend/app/routes/admin.py` - Lines 68-77 show what's requested
- Google Console shows what's been granted, which may include unused ones









































