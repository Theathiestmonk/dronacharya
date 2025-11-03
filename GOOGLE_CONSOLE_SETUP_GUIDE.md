# Google Cloud Console Setup Guide - Fetch All Data

This guide shows you exactly what to configure in Google Cloud Console to fetch **ALL** data (courses, teachers, students, coursework, submissions, announcements, calendar events).

---

## 🎯 **Quick Checklist**

- [ ] Enable Google Classroom API
- [ ] Enable Google Calendar API
- [ ] Add all required OAuth scopes
- [ ] Configure OAuth Consent Screen
- [ ] Test OAuth connection

---

## 📋 **Step 1: Enable Required APIs**

### **1.1 Go to Google Cloud Console**
1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)

### **1.2 Enable Google Classroom API**
1. Navigate to **APIs & Services** > **Library**
2. Search for: **"Google Classroom API"**
3. Click on it and click **"ENABLE"** button
4. ✅ Wait for confirmation that it's enabled

### **1.3 Enable Google Calendar API**
1. Still in **APIs & Services** > **Library**
2. Search for: **"Google Calendar API"**
3. Click on it and click **"ENABLE"** button
4. ✅ Wait for confirmation that it's enabled

**✅ Both APIs must be enabled before proceeding!**

---

## 🔐 **Step 2: Configure OAuth Scopes**

### **2.1 Go to OAuth Consent Screen**
1. Navigate to **APIs & Services** > **OAuth consent screen**
2. Make sure your app is set up (if not, complete the basic setup first)

### **2.2 Add Required Scopes**

Click **"ADD OR REMOVE SCOPES"** button, then add these **EXACT** scopes:

#### **For Google Classroom (3 scopes - VALID):**
```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.rosters.readonly
https://www.googleapis.com/auth/classroom.announcements.readonly
```

⚠️ **IMPORTANT:** These scopes are **INVALID** and Google will reject them:
- ❌ `classroom.coursework.readonly` - **DEPRECATED/INVALID**
- ❌ `classroom.student-submissions.readonly` - **DEPRECATED/INVALID**

#### **For Google Calendar (2 scopes):**
```
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events.readonly
```

**Total: 5 valid scopes** (down from 7)

### **2.3 Save Scopes**
- Click **"UPDATE"** or **"SAVE"** button
- ✅ Scopes are now added to your OAuth consent screen

---

## 📝 **Step 3: Verify OAuth Client Configuration**

### **3.1 Check OAuth Client**
1. Go to **APIs & Services** > **Credentials**
2. Find your **OAuth 2.0 Client ID**
3. Click on it to view details

### **3.2 Verify Authorized Redirect URIs**
Make sure these redirect URIs are added:

**For Development:**
```
http://localhost:3000/admin/callback
```

**For Production:**
```
https://yourdomain.com/admin/callback
```

**✅ Add both if you test locally and deploy**

---

## ✅ **Step 4: Test Configuration**

### **4.1 Re-authorize Your App**
⚠️ **IMPORTANT:** If you already connected Google before, you need to **disconnect and reconnect** to get the new scopes!

1. Go to your admin dashboard
2. Click **"Disconnect"** on existing Google integrations (if any)
3. Click **"Connect Google Classroom"** again
4. You'll see a new permission screen with all the scopes listed
5. Review and click **"Allow"**

### **4.2 Verify Scopes Are Granted**
After re-authorizing, check your database:

```sql
SELECT scope FROM google_integrations 
WHERE service_type = 'classroom' 
ORDER BY created_at DESC 
LIMIT 1;
```

You should see all 5 Classroom scopes listed.

---

## 📊 **Scope Details - What Each Scope Does**

### **Classroom Scopes:**

1. **`classroom.courses.readonly`**
   - ✅ Fetches: Course list, course details (name, section, room, description, etc.)
   - 📦 Used for: `google_classroom_courses` table

2. **`classroom.rosters.readonly`**
   - ✅ Fetches: Students and teachers for each course
   - 📦 Used for: `google_classroom_teachers` and `google_classroom_students` tables

3. **`classroom.announcements.readonly`** ⭐ **REQUIRED**
   - ✅ Fetches: Course announcements
   - 📦 Used for: `google_classroom_announcements` table
   - ⚠️ **Without this:** Announcements won't sync!

### **Calendar Scopes:**

1. **`calendar.readonly`**
   - ✅ Fetches: Calendar metadata and basic info
   - 📦 Used for: `google_calendar_calendars` table

2. **`calendar.events.readonly`**
   - ✅ Fetches: Calendar events (summary, description, startTime, endTime, location, hangoutLink)
   - 📦 Used for: `google_calendar_events` table

---

## ⚠️ **Common Issues & Solutions**

### **Issue 1: "Insufficient permissions" or 403 error**

**Solution:**
- ✅ Make sure all APIs are **ENABLED** (Step 1)
- ✅ Make sure all scopes are **ADDED** to OAuth consent screen (Step 2)
- ✅ **Re-authorize** your app after adding scopes (Step 4)

### **Issue 2: Invalid scope error**

**Solution:**
- ❌ **DO NOT add** `classroom.coursework.readonly` - Google rejects this as invalid
- ❌ **DO NOT add** `classroom.student-submissions.readonly` - Google rejects this as invalid
- ⚠️ These scopes have been deprecated by Google
- 📝 **Note:** Coursework and submissions data may require alternative approaches or may not be accessible via OAuth scopes

### **Issue 3: Announcements not syncing**

**Solution:**
- ✅ Verify `classroom.announcements.readonly` scope is added
- ✅ This is a **NEW** scope - make sure it's in your OAuth consent screen
- ✅ Re-authorize after adding this scope

### **Issue 4: "Invalid scope" error**

**Solution:**
- ✅ Double-check scope URLs are **EXACTLY** as listed above
- ✅ Make sure you copied the full URL (not abbreviated)
- ✅ Scopes are case-sensitive

---

## 🔄 **Step 5: Update Your Code**

Your code is already updated in `backend/app/routes/admin.py` to request all these scopes. Just make sure your environment variables are set:

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:3000/admin/callback
```

---

## ✅ **Verification Checklist**

After setup, verify everything works:

- [ ] All 7 scopes appear in OAuth consent screen
- [ ] Can connect Google Classroom successfully
- [ ] Can connect Google Calendar successfully
- [ ] Click "Sync Classroom Data" → Courses sync
- [ ] Teachers and students appear in database
- [ ] ⚠️ **Coursework/assignments** - Limited (scope deprecated by Google)
- [ ] ⚠️ **Submissions** - Limited (scope deprecated by Google)
- [ ] **Announcements sync** ✅
- [ ] Calendar events sync

---

## 📞 **Testing Your Setup**

1. **Connect Google Classroom:**
   ```
   Click "Connect Google Classroom" → Authorize → Should see 5 scopes requested
   ```

2. **Click "Sync Classroom Data":**
   ```
   Should fetch: courses, teachers, students, coursework, submissions, announcements
   ```

3. **Check Database:**
   ```sql
   -- Should see courses
   SELECT COUNT(*) FROM google_classroom_courses;
   
   -- Should see teachers
   SELECT COUNT(*) FROM google_classroom_teachers;
   
   -- Should see students
   SELECT COUNT(*) FROM google_classroom_students;
   
   -- Should see coursework
   SELECT COUNT(*) FROM google_classroom_coursework;
   
   -- Should see submissions (if students have submitted work)
   SELECT COUNT(*) FROM google_classroom_submissions;
   
   -- Should see announcements
   SELECT COUNT(*) FROM google_classroom_announcements;
   ```

---

## 🎉 **You're Done!**

Once all scopes are added and you've re-authorized, clicking "Sync" will fetch **ALL** data:
- ✅ Courses (with all fields)
- ✅ Teachers (with names)
- ✅ Students (with names)
- ✅ Coursework/Assignments
- ✅ Student Submissions (with late status)
- ✅ Announcements
- ✅ Calendar Events (with hangout links)

---

## 📚 **Reference: Full Scope List**

Copy-paste this list when adding scopes in Google Console:

```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.rosters.readonly
https://www.googleapis.com/auth/classroom.announcements.readonly
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events.readonly
```

⚠️ **Note:** `classroom.coursework.readonly` and `classroom.student-submissions.readonly` are **INVALID** and will be rejected by Google Console.

---

## 🔗 **Quick Links**

- [Google Cloud Console](https://console.cloud.google.com/)
- [APIs & Services Library](https://console.cloud.google.com/apis/library)
- [OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)
- [Credentials](https://console.cloud.google.com/apis/credentials)

---

**Need Help?** Check the error messages in your browser console or backend logs for specific scope-related issues.

