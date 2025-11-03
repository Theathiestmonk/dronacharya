# Chatbot Data Access - What's Available After Setup

## ✅ **Setup Complete!**

You've successfully added all valid scopes to your Google Cloud Console. Your chatbot now has access to the following data for enhanced responses.

---

## 📚 **Google Classroom Data Access**

### 1. **Course Information** ✅
**Scope:** `classroom.courses.readonly`

**What Chatbot Can Access:**
- ✅ Course ID
- ✅ Course name
- ✅ Course section
- ✅ Room information
- ✅ Course description
- ✅ Description heading
- ✅ Update time
- ✅ Course state (ACTIVE, ARCHIVED, etc.)
- ✅ Enrollment codes
- ✅ Alternate links

**Example Chatbot Queries:**
- "What courses are available?"
- "Tell me about the Math 101 course"
- "What section is Chemistry in?"
- "Which room is History class in?"

---

### 2. **Teacher Information** ✅
**Scope:** `classroom.rosters.readonly`

**What Chatbot Can Access:**
- ✅ Teacher ID
- ✅ Teacher name (extracted from profile)
- ✅ Teacher email address
- ✅ Teacher profile information
- ✅ Course-user relationships

**Example Chatbot Queries:**
- "Who teaches Mathematics?"
- "What's the teacher's email for Science class?"
- "List all teachers in my courses"

---

### 3. **Student Information** ✅
**Scope:** `classroom.rosters.readonly`

**What Chatbot Can Access:**
- ✅ Student ID
- ✅ Student name (extracted from profile)
- ✅ Student email address
- ✅ Student profile information
- ✅ Student work folder info
- ✅ Course enrollment data

**Example Chatbot Queries:**
- "How many students are in Math class?"
- "List all students in my course"
- "Who is enrolled in Chemistry?"

---

### 4. **Course Announcements** ✅
**Scope:** `classroom.announcements.readonly`

**What Chatbot Can Access:**
- ✅ Announcement ID
- ✅ Announcement text/content
- ✅ Materials (files, links attached)
- ✅ Update time
- ✅ Creation time
- ✅ Announcement state
- ✅ Alternate links

**Example Chatbot Queries:**
- "What are the latest announcements?"
- "Show me announcements from Math class"
- "Any new updates in my courses?"

---

## 📅 **Google Calendar Data Access**

### 5. **Calendar Events** ✅
**Scopes:** `calendar.readonly` + `calendar.events.readonly`

**What Chatbot Can Access:**
- ✅ Event ID
- ✅ Event summary (title)
- ✅ Event description
- ✅ Start time
- ✅ End time
- ✅ Location
- ✅ Hangout link (Google Meet links)
- ✅ Event status
- ✅ Attendees information
- ✅ Recurrence rules
- ✅ Event visibility

**Example Chatbot Queries:**
- "What events do I have today?"
- "Show me upcoming calendar events"
- "When is my next meeting?"
- "What's the Google Meet link for the meeting?"
- "Where is the conference located?"

---

### 6. **Calendar Information** ✅
**Scope:** `calendar.readonly`

**What Chatbot Can Access:**
- ✅ Calendar summary (name)
- ✅ Calendar description
- ✅ Calendar location
- ✅ Timezone settings
- ✅ Primary calendar status
- ✅ Calendar access role

**Example Chatbot Queries:**
- "List all my calendars"
- "Which is my primary calendar?"

---

## 👤 **User Profile Data** ✅

### 7. **Email Address** ✅
**Scope:** `userinfo.email`

**What Chatbot Can Access:**
- ✅ Primary Google Account email

**Used For:**
- Identifying user context
- Personalizing responses

---

### 8. **Profile Information** ✅
**Scope:** `userinfo.profile`

**What Chatbot Can Access:**
- ✅ Personal info (name, photo, etc.)
- ✅ Publicly available profile data

**Used For:**
- Personalizing chatbot responses
- User identification

---

## ❌ **Data NOT Available (Due to Invalid Scopes)**

### **Coursework/Assignments** ⚠️
**Missing Scope:** `classroom.coursework.readonly` (DEPRECATED by Google)

**What Chatbot CANNOT Access:**
- ❌ Assignment titles
- ❌ Assignment descriptions
- ❌ Due dates for assignments
- ❌ Assignment states (PUBLISHED, DRAFT)
- ❌ Assignment links

**Impact:**
- Chatbot cannot answer: "What assignments are due this week?"
- Chatbot cannot answer: "Show me my homework"
- Chatbot cannot answer: "What's due in Math class?"

---

### **Student Submissions** ⚠️
**Missing Scope:** `classroom.student-submissions.readonly` (DEPRECATED by Google)

**What Chatbot CANNOT Access:**
- ❌ Submission status (TURNED_IN, RETURNED, etc.)
- ❌ Late status
- ❌ Assigned grades
- ❌ Draft grades
- ❌ Submission history

**Impact:**
- Chatbot cannot answer: "Did I turn in my assignment?"
- Chatbot cannot answer: "What grade did I get?"
- Chatbot cannot answer: "Is my submission late?"

---

## 🎯 **Enhanced Chatbot Experience - What Works**

### **Course-Related Queries:**
✅ "What courses am I enrolled in?"
✅ "Tell me about my courses"
✅ "Who are the teachers?"
✅ "How many students are in each course?"
✅ "What section am I in?"

### **Announcement Queries:**
✅ "Show me recent announcements"
✅ "What's new in my classes?"
✅ "Any updates from teachers?"

### **Calendar/Event Queries:**
✅ "What's on my calendar today?"
✅ "When is my next meeting?"
✅ "Show me upcoming events"
✅ "What's the Google Meet link?"
✅ "Where is the event located?"

### **Roster Queries:**
✅ "Who are my classmates?"
✅ "List students in Math class"
✅ "Who teaches Science?"

---

## 🚀 **Best Practices for Chatbot Responses**

### **1. Use Available Data:**
Focus on:
- ✅ Course information
- ✅ Teacher/student rosters
- ✅ Announcements
- ✅ Calendar events

### **2. Gracefully Handle Missing Data:**
For coursework/submissions queries, chatbot should:
- Explain that assignment data isn't available via API
- Suggest alternative ways to get this info
- Direct users to Google Classroom directly

### **3. Combine Data Sources:**
- Use course data + calendar events for context
- Link announcements to specific courses
- Show teacher info with course details

---

## 📊 **Data Summary Table**

| Data Type | Available | Scope | Example Use |
|-----------|-----------|-------|-------------|
| Courses | ✅ Yes | `courses.readonly` | List courses, show details |
| Teachers | ✅ Yes | `rosters.readonly` | Show teacher names, emails |
| Students | ✅ Yes | `rosters.readonly` | List students, show rosters |
| Announcements | ✅ Yes | `announcements.readonly` | Show course updates |
| Calendar Events | ✅ Yes | `calendar.events.readonly` | Show schedule, meetings |
| Calendar Info | ✅ Yes | `calendar.readonly` | List calendars |
| **Coursework** | ❌ **No** | **DEPRECATED** | **Cannot access assignments** |
| **Submissions** | ❌ **No** | **DEPRECATED** | **Cannot access submission data** |

---

## ✅ **Next Steps**

1. **Re-authorize Your App:**
   - Disconnect existing Google integrations
   - Reconnect to grant all new scopes
   - Users will see permission screen with all 7 scopes

2. **Test Chatbot:**
   - Ask about courses: "What courses do I have?"
   - Ask about calendar: "What's on my calendar?"
   - Ask about announcements: "Show me updates"
   - Ask about teachers: "Who teaches Math?"

3. **Monitor Performance:**
   - Check if chatbot responds with course data
   - Verify calendar events are accessible
   - Confirm announcements appear in responses

---

## 🎉 **You're All Set!**

Your chatbot can now provide rich, contextual responses using:
- ✅ Course information
- ✅ Teacher and student data
- ✅ Course announcements
- ✅ Calendar events and meetings
- ✅ User profile context

The chatbot will gracefully handle coursework/submission queries by explaining limitations and suggesting alternatives.

---

**Total Available Scopes:** 7 (5 Classroom/Calendar + 2 User Info)
**Data Tables Populated:** 6 (courses, teachers, students, announcements, calendar_events, calendar_calendars)
**Chatbot Enhancement:** ✅ SIGNIFICANTLY IMPROVED



