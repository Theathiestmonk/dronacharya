# Google API Scopes Configuration Guide

## Current Required Scopes

### For Google Classroom:
1. ✅ `https://www.googleapis.com/auth/classroom.courses.readonly`
   - **Purpose:** Read course information
   - **Used for:** Fetching course list, course details
   
2. ✅ `https://www.googleapis.com/auth/classroom.rosters.readonly`
   - **Purpose:** Read student and teacher rosters
   - **Used for:** Fetching students and teachers for each course

3. ✅ `https://www.googleapis.com/auth/classroom.coursework.readonly` ⭐ **NEW**
   - **Purpose:** Read assignments/coursework
   - **Used for:** Fetching assignments, homework, quizzes for each course
   - **Status:** Required for fetching nested coursework data

4. ✅ `https://www.googleapis.com/auth/classroom.student-submissions.readonly` ⭐ **NEW**
   - **Purpose:** Read student submissions
   - **Used for:** Fetching student work submissions
   - **Status:** Optional but recommended if you want to see submission data

### For Google Calendar:
1. ✅ `https://www.googleapis.com/auth/calendar.readonly`
   - **Purpose:** Read calendar information
   
2. ✅ `https://www.googleapis.com/auth/calendar.events.readonly`
   - **Purpose:** Read calendar events

---

## How to Update Scopes in Google Cloud Console

### Step 1: Enable Required APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** > **Library**
4. Search and enable:
   - ✅ Google Classroom API
   - ✅ Google Calendar API

### Step 2: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Make sure your app is configured correctly
3. Scopes should be automatically detected from your OAuth requests

### Step 3: Verify Scopes in OAuth Client

1. Go to **APIs & Services** > **Credentials**
2. Click on your **OAuth 2.0 Client ID**
3. The scopes will be requested automatically when users authorize your app

### Step 4: Re-authorize Users

**IMPORTANT:** When you add new scopes, existing users must re-authorize:

1. Delete existing integrations in Supabase:
   ```sql
   -- Optionally, deactivate old integrations
   UPDATE google_integrations 
   SET is_active = false 
   WHERE service_type = 'classroom';
   ```

2. Users need to reconnect by:
   - Going to Admin Dashboard
   - Clicking "Connect Google Classroom" again
   - Google will show a new consent screen with additional permissions
   - Users must approve the new scopes

---

## What Each Scope Allows

| Scope | What You Can Access |
|-------|-------------------|
| `classroom.courses.readonly` | ✅ Course list, course details |
| `classroom.rosters.readonly` | ✅ Students list, Teachers list |
| `classroom.coursework.readonly` | ✅ Assignments, homework, quizzes |
| `classroom.student-submissions.readonly` | ✅ Student submissions, grades |

---

## Troubleshooting

### Issue: Coursework is empty after sync

**Possible causes:**
1. ❌ Missing `classroom.coursework.readonly` scope
   - **Solution:** Re-connect Google Classroom (user must re-authorize)
   
2. ❌ Course has no assignments yet
   - **Check:** Verify in Google Classroom that the course actually has assignments

3. ❌ Token doesn't have new scopes
   - **Solution:** Delete old integration and reconnect

### Issue: 403 Forbidden when fetching coursework

**Error:** `Insufficient Permission` or `Forbidden`

**Solutions:**
1. Verify scope is in the OAuth request
2. Re-authorize the user with new scopes
3. Check Google Cloud Console that Classroom API is enabled

---

## Verification Checklist

- [ ] All 4 Classroom scopes are in the code
- [ ] Google Cloud Console has Classroom API enabled
- [ ] Users have re-authorized after scope changes
- [ ] OAuth consent screen shows all required permissions
- [ ] Test sync shows coursework data populated

---

## Code Location

Scopes are defined in:
- `backend/app/routes/admin.py` - Lines 68-76



## Current Required Scopes

### For Google Classroom:
1. ✅ `https://www.googleapis.com/auth/classroom.courses.readonly`
   - **Purpose:** Read course information
   - **Used for:** Fetching course list, course details
   
2. ✅ `https://www.googleapis.com/auth/classroom.rosters.readonly`
   - **Purpose:** Read student and teacher rosters
   - **Used for:** Fetching students and teachers for each course

3. ✅ `https://www.googleapis.com/auth/classroom.coursework.readonly` ⭐ **NEW**
   - **Purpose:** Read assignments/coursework
   - **Used for:** Fetching assignments, homework, quizzes for each course
   - **Status:** Required for fetching nested coursework data

4. ✅ `https://www.googleapis.com/auth/classroom.student-submissions.readonly` ⭐ **NEW**
   - **Purpose:** Read student submissions
   - **Used for:** Fetching student work submissions
   - **Status:** Optional but recommended if you want to see submission data

### For Google Calendar:
1. ✅ `https://www.googleapis.com/auth/calendar.readonly`
   - **Purpose:** Read calendar information
   
2. ✅ `https://www.googleapis.com/auth/calendar.events.readonly`
   - **Purpose:** Read calendar events

---

## How to Update Scopes in Google Cloud Console

### Step 1: Enable Required APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** > **Library**
4. Search and enable:
   - ✅ Google Classroom API
   - ✅ Google Calendar API

### Step 2: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Make sure your app is configured correctly
3. Scopes should be automatically detected from your OAuth requests

### Step 3: Verify Scopes in OAuth Client

1. Go to **APIs & Services** > **Credentials**
2. Click on your **OAuth 2.0 Client ID**
3. The scopes will be requested automatically when users authorize your app

### Step 4: Re-authorize Users

**IMPORTANT:** When you add new scopes, existing users must re-authorize:

1. Delete existing integrations in Supabase:
   ```sql
   -- Optionally, deactivate old integrations
   UPDATE google_integrations 
   SET is_active = false 
   WHERE service_type = 'classroom';
   ```

2. Users need to reconnect by:
   - Going to Admin Dashboard
   - Clicking "Connect Google Classroom" again
   - Google will show a new consent screen with additional permissions
   - Users must approve the new scopes

---

## What Each Scope Allows

| Scope | What You Can Access |
|-------|-------------------|
| `classroom.courses.readonly` | ✅ Course list, course details |
| `classroom.rosters.readonly` | ✅ Students list, Teachers list |
| `classroom.coursework.readonly` | ✅ Assignments, homework, quizzes |
| `classroom.student-submissions.readonly` | ✅ Student submissions, grades |

---

## Troubleshooting

### Issue: Coursework is empty after sync

**Possible causes:**
1. ❌ Missing `classroom.coursework.readonly` scope
   - **Solution:** Re-connect Google Classroom (user must re-authorize)
   
2. ❌ Course has no assignments yet
   - **Check:** Verify in Google Classroom that the course actually has assignments

3. ❌ Token doesn't have new scopes
   - **Solution:** Delete old integration and reconnect

### Issue: 403 Forbidden when fetching coursework

**Error:** `Insufficient Permission` or `Forbidden`

**Solutions:**
1. Verify scope is in the OAuth request
2. Re-authorize the user with new scopes
3. Check Google Cloud Console that Classroom API is enabled

---

## Verification Checklist

- [ ] All 4 Classroom scopes are in the code
- [ ] Google Cloud Console has Classroom API enabled
- [ ] Users have re-authorized after scope changes
- [ ] OAuth consent screen shows all required permissions
- [ ] Test sync shows coursework data populated

---

## Code Location

Scopes are defined in:
- `backend/app/routes/admin.py` - Lines 68-76





















