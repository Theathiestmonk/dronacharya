# Supported Queries - Complete List of Example Questions

This document lists all the types of queries your chatbot can handle, organized by data source.

---

## 📚 **Google Classroom Data Queries**

### ⚠️ **Important Limitations:**
- ✅ **Available**: Announcements, Students, Teachers, Courses
- ⚠️ **Coursework/Assignments**: Cannot display data directly, but chatbot provides **links and instructions** to access coursework in Google Classroom

### **Announcements**

#### Simple Announcement Queries:
- "Show me today's announcements"
- "What are the announcements for today?"
- "Show me yesterday's announcements"
- "What were the announcements yesterday?"
- "Show me all announcements"
- "List recent announcements"
- "What are the latest announcements?"
- "Show me the announcements"

#### Date-Specific Announcement Queries:
- "Show me announcements for 21 October"
- "What are the announcements on 22, 24, 30 October?"
- "Show announcements for October 21, 24, 29"
- "Announcements for 21/10"
- "What was announced on 22/09?"
- "Show announcements for September 21, 29"
- "Announcements on 15/09, 20/09"
- "What are the announcements for October 21st and 24th?"

#### Course-Specific Announcements:
- "Show me announcements for Math class"
- "What are the announcements in Science course?"
- "Announcements for my English course"
- "Latest updates in History class"

### **Students**

#### General Student Queries:
- "Show me all students"
- "List students in my class"
- "Who are the students?"
- "Show student roster"
- "What students are enrolled?"
- "List all classmates"

#### Course-Specific Student Queries:
- "Show me students in Math class"
- "Who are the students in Science course?"
- "List students enrolled in English"
- "Show students for History course"

#### Student with Email Queries:
- "Show me student emails"
- "What are the email addresses of students?"
- "List students with their emails"
- "Show me student roster with emails"
- "Get student email addresses"

### **Teachers**

#### General Teacher Queries:
- "Show me all teachers"
- "List faculty members"
- "Who are the teachers?"
- "Show instructor list"
- "What teachers do we have?"
- "List staff members"

#### Course-Specific Teacher Queries:
- "Show me teachers for Math class"
- "Who teaches Science course?"
- "List instructors for English"
- "Show teachers in History course"
- "Which faculty teaches my course?"

#### Teacher with Email Queries:
- "Show me teacher emails"
- "What are the email addresses of teachers?"
- "List teachers with their emails"
- "Show me faculty with email addresses"
- "Get teacher contact emails"

### **Coursework/Assignments**

⚠️ **LIMITATION**: Coursework and assignment data cannot be directly displayed due to Google Classroom API restrictions. However, the chatbot can provide **links and instructions** to access coursework.

**How it works**: When users ask about assignments/homework, the chatbot will:
1. Detect the coursework query
2. Provide a helpful response with instructions
3. Share links to Google Classroom where users can check their assignments directly
4. Guide users on how to access their coursework

#### Coursework Query Examples:
- "Show me my assignments" → Bot provides Google Classroom link + instructions
- "What homework do I have?" → Bot provides link + access instructions
- "List all coursework" → Bot directs to Google Classroom
- "Show me tasks that are due" → Bot provides course links
- "What assignments need to be submitted?" → Bot gives instructions to check Google Classroom

#### Example Response Pattern:
The chatbot will respond with something like:
```
"I can't directly access your assignment details due to Google Classroom restrictions, but you can check them yourself:

🔗 [Course Name] - [Link to Google Classroom Course]
🔗 [Another Course] - [Link to Google Classroom Course]

To view your assignments:
1. Click on any course link above
2. Go to the 'Classwork' tab
3. View all assignments, due dates, and submission status

Need help accessing a specific course? Let me know!"
```

**Why**: Google Classroom API restricts coursework data to maintain privacy and security. Links are provided to help users access their coursework directly in Google Classroom.

### **Courses/Classes**

#### General Course Queries:
- "Show me all courses"
- "List my classes"
- "What classes am I enrolled in?"
- "Show me all subjects"
- "List available courses"
- "What courses are available?"

---

## 📅 **Google Calendar Data Queries**

### **General Calendar Queries:**
- "Show me calendar events"
- "What events are scheduled?"
- "List upcoming events"
- "Show me the calendar"
- "What's on the schedule?"
- "Show me meetings"
- "List holidays"
- "Show school holidays"

### **Holiday Calendar:**
- "Show holiday calendar"
- "What are the school holidays?"
- "Show me vacation calendar"
- "List school holidays"
- "Show calendar of holidays"
- "Holiday list"

### **Event Queries:**
- "What events are happening?"
- "Show upcoming events"
- "List scheduled meetings"
- "What's on the calendar today?"
- "Show events this week"

---

## 🌐 **Web Crawler Data Queries**

### **Team/Staff Information:**
- "Tell me about [Person Name]"
- "Who is [Person Name]?"
- "Show me details about [Person Name]"
- "Information about [Person Name]"
- "What is [Person Name]'s profile?"
- "Tell me about the staff"
- "Who works at Prakriti?"
- "Show team members"

**Example Names (if they exist on team page):**
- "Tell me about John Doe"
- "Who is Jane Smith?"
- "Information about Deepankar"
- "Details about Dr. Sharma"

### **Latest News & Updates:**
- "Show me latest news"
- "What's new at Prakriti?"
- "Recent updates"
- "Latest school news"
- "What's happening at Prakriti School?"
- "Show recent news"
- "Current updates"

### **School Information:**
- "Tell me about Prakriti School"
- "What kind of school is Prakriti?"
- "Describe Prakriti School"
- "Prakriti School overview"
- "What is Prakriti School?"

### **Teaching Philosophy:**
- "What's the teaching philosophy at Prakriti?"
- "How does Prakriti teach?"
- "What is Prakriti's teaching approach?"
- "Prakriti education philosophy"
- "What is the learning model at Prakriti?"
- "How are students taught at Prakriti?"
- "What is Prakriti's approach to education?"

### **Subjects & Curriculum:**
- "Which subjects are available for IGCSE and AS/A Level?"
- "What IGCSE subjects are offered?"
- "Show AS Level subjects"
- "What can I study at Prakriti?"
- "What are the subject options for Grade 9?"
- "What subjects are available for Grade 12?"
- "Prakriti subject list"
- "What are the options for IGCSE?"

### **Special Needs Support:**
- "How are learners with special needs supported?"
- "Tell me about special needs support"
- "What is the Bridge Programme?"
- "How does Prakriti help special needs students?"
- "Inclusive education at Prakriti"
- "Special educators at Prakriti"
- "Therapy support at Prakriti"
- "Support for disabilities"

### **Activities & Programs:**
- "What sports, arts, and enrichment activities are available?"
- "What sports are offered?"
- "Show me arts programs"
- "What enrichment activities are there?"
- "Prakriti extracurricular activities"
- "What clubs are available?"
- "Tell me about music programs"
- "What theater activities are there?"
- "Show STEM labs"
- "Tell me about mindfulness programs"
- "What maker projects are there?"
- "Farm outings at Prakriti"

### **Fees:**
- "What are the fees for different grades?"
- "Show me Prakriti fee structure"
- "What is the school fees?"
- "Fee for Grade 9"
- "Fee for nursery"
- "What are admission charges?"
- "Prakriti monthly fee"
- "Show fee breakdown"
- "Fee for 2024"
- "Fee for 2025"

### **Location:**
- "Where is Prakriti School located?"
- "What is Prakriti School's address?"
- "Show me Prakriti location"
- "How to reach Prakriti?"
- "Prakriti School directions"
- "Show me Prakriti on Google Map"
- "Where is Prakriti School in Greater Noida?"

### **Articles & Philosophy:**
- "Tell me about Prakriti's philosophy"
- "What is the Prakriti way of learning?"
- "Show me articles about Prakriti"
- "Tell me about progressive education"
- "What is experiential learning?"
- "Explain alternative schooling"

### **Admissions:**
- "How do I apply to Prakriti?"
- "Tell me about admissions"
- "What is the admission process?"
- "Show admission requirements"
- "How to enroll at Prakriti?"

### **Contact Information:**
- "How can I contact Prakriti School?"
- "Show contact information"
- "What is Prakriti's phone number?"
- "Prakriti School contact details"

---

## 🎥 **YouTube Video Queries**

### **Video-Related Queries:**
- "Show me a video about gardening"
- "Watch art demonstration"
- "Show me sports video"
- "Video about science"
- "Show mindfulness video"
- "Watch campus tour"
- "Show me facilities video"
- "Video of performance"
- "Watch exhibition video"
- "Show workshop video"
- "Video about activity"
- "Watch program video"
- "Show class video"
- "Video lesson"

**Note:** Video queries work for topics like gardening, art, sports, science, mindfulness, campus tours, facilities, performances, exhibitions, workshops, activities, programs, classes, and lessons.

---

## 💬 **General Conversational Queries**

### **Greetings:**
- "Hi"
- "Hello"
- "Hey"
- "Good morning"
- "Good afternoon"
- "Good evening"
- "Greetings"

### **How are you:**
- "How are you?"
- "How are you doing?"
- "How do you do?"
- "How's it going?"
- "How's everything?"

### **General Questions (Knowledge Base):**
The chatbot uses a local knowledge base JSON file for fuzzy matching. Examples of questions that might be in the KB:
- Various school-related FAQ questions
- Program details
- Policy questions
- General information queries

**Note:** The knowledge base uses fuzzy matching (threshold: 50), so similar questions to those in the KB will be matched.

---

## 🔍 **Query Features & Capabilities**

### **Date Detection Support:**
- ✅ **Today**: "today", "today's"
- ✅ **Yesterday**: "yesterday", "yesterday's"
- ✅ **Specific dates**: "21 October", "22, 24, 30 October"
- ✅ **Multiple dates**: "21 and 29 September"
- ✅ **Date formats**: 
  - "22/10", "21/09" (DD/MM or MM/DD)
  - "22 October", "October 22"
  - "21, 24, 29 October"
  - "October 21, 24, 29"
- ✅ **Typo tolerance**: Handles common typos like "octomber" → "october"

### **Smart Intent Detection:**
The chatbot automatically detects query intent to:
- Load only relevant data (saves tokens)
- Filter by date when specified
- Include/exclude email addresses based on query
- Prioritize web crawler for person queries
- Use YouTube for video-related queries

### **Multi-Source Queries:**
You can combine multiple data sources:
- "Show me today's announcements and calendar events"
- "List students and teachers for Math class"
- "Show announcements and students for today"
- "List teachers, students, and announcements for Math course"

---

## 📝 **Query Examples by User Role**

### **Student Queries:**
- "What are today's announcements?"
- "Who are my classmates?"
- "List teachers for my courses"
- "What events are coming up?"
- "Tell me about Prakriti's teaching approach"
- "Show me all my courses"
- "List students in my class"

### **Teacher Queries:**
- "Show me all students in my class"
- "List announcements I posted"
- "Show student emails"
- "List my courses"
- "Show calendar events"
- "List teachers for my courses"
- "Show me students with their emails"

### **Parent Queries:**
- "What are the school announcements?"
- "List teachers for my child's courses"
- "Show school calendar"
- "What are the fees for Grade 9?"
- "Tell me about special needs support"
- "What activities are available?"
- "Show students in my child's class"
- "What courses is my child enrolled in?"
- "How can I check my child's assignments?" (Gets Google Classroom links)
- "Where are the homework assignments?" (Gets course links + instructions)

---

## ⚠️ **Important Notes**

1. **Case Sensitivity**: Queries are case-insensitive, so "ANNOUNCEMENT" works the same as "announcement"

2. **Keyword Matching**: The chatbot uses keyword matching, so queries containing these words will trigger specific data loading:
   - **Announcements**: announcement, announce, notice, update, news
   - **Students**: student, students, classmate, classmates, roster, enrollment
   - **Teachers**: teacher, teachers, faculty, instructor, instructors, staff member, staff
   - **Coursework**: assignment, homework, coursework, task, due, submit ⚠️ (Detected - chatbot provides links/instructions instead of data)
   - **Courses**: course, courses, class, classes, subject, subjects
   - **Calendar**: event, events, calendar, schedule, meeting, holiday

3. **Date Filtering**: When dates are specified, the chatbot automatically filters data at the SQL level to reduce token usage

4. **Email Inclusion**: Email addresses are only included when the query explicitly mentions "email" or "emails"

5. **Web Crawler**: Triggers automatically for:
   - Person detail queries (with names)
   - Queries with keywords: latest, recent, news, update, current, new, recently
   - School-related information queries

6. **YouTube Videos**: Triggers for video-related keywords when not asking for articles/text

---

## 🚀 **Advanced Query Patterns**

### **Combined Queries:**
- "Show me announcements and calendar events for today"
- "List students and their emails for Math class"
- "Show today's announcements and events"
- "List teachers and students for Math course"

### **Specific Filtering:**
- "Show announcements for 21 October only"
- "List students in Science course with emails"
- "Show announcements for all my courses"

### **Multi-Course Queries:**
- "Show announcements for all my courses"
- "List students across all classes"
- "Show all courses with their teachers"

---

This comprehensive list covers all supported query types. The chatbot intelligently routes queries to the appropriate data sources and filters results based on detected intent!

