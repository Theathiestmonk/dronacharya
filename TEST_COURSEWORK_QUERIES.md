# Test Questions for Coursework/Assignment Feature

Use these questions to test if the chatbot correctly provides Google Classroom links and instructions when coursework data is restricted.

---

## 🧪 **Basic Coursework Queries**

### Simple Assignment Questions:
1. "Show me my assignments"
2. "What homework do I have?"
3. "List all coursework"
4. "Show me tasks that are due"
5. "What assignments need to be submitted?"
6. "Show upcoming assignments"
7. "What assignments do I have?"

### Homework-Specific Queries:
8. "What's my homework?"
9. "Show me all homework"
10. "List homework assignments"
11. "What homework is due?"

### Task/Due Date Queries:
12. "What tasks are due?"
13. "Show me due assignments"
14. "What assignments are due this week?"
15. "List tasks that need to be submitted"
16. "What's due soon?"

---

## 📚 **Course-Specific Coursework Queries**

17. "Show assignments for Math class"
18. "What homework is there for Science?"
19. "List coursework in English course"
20. "Show tasks for History class"
21. "What assignments do I have in Math?"
22. "Show me homework for my Science course"

---

## 🔍 **Mixed Queries (Multiple Data Types)**

23. "Show me announcements and assignments"
24. "List students and assignments for Math class"
25. "What are today's announcements and my homework?"

---

## 📅 **Date-Specific Queries**

26. "What assignments are due today?"
27. "Show me tasks due tomorrow"
28. "List coursework due this week"
29. "What needs to be submitted soon?"

---

## 🎯 **Expected Behavior**

When you test these questions, the chatbot should:

### ✅ **If Coursework Data is Available:**
- Display the coursework/assignments in a formatted list
- Show assignment titles, due dates, and status
- Format nicely with Markdown

### ✅ **If Coursework Data is Restricted/Empty:**
- **Provide Google Classroom course links** (one per course)
- **Give clear instructions** like:
  ```
  "I can't directly access your assignment details due to Google Classroom restrictions, 
  but you can check them yourself:
  
  🔗 [Course Name] - [Click here](course_link)
  
  To view your assignments:
  1. Click on any course link above
  2. Go to the 'Classwork' tab
  3. View all assignments, due dates, and submission status"
  ```
- **Use Markdown formatting** for links
- **Be helpful and friendly** - not apologetic or negative

---

## 🚫 **What NOT to See**

The chatbot should **NOT**:
- Say "I don't have access" without providing links
- Say "I'm sorry but as an AI, I don't have access"
- Say "for privacy reasons, I can't show this"
- Just say "data not available" without guidance
- Show empty responses

---

## 📋 **Test Checklist**

For each test question, verify:

- [ ] Query is detected as coursework query
- [ ] Response includes course names
- [ ] Response includes clickable Google Classroom links
- [ ] Instructions are clear and helpful
- [ ] Formatting uses Markdown (headings, links)
- [ ] Tone is helpful (not apologetic)
- [ ] All relevant courses are mentioned
- [ ] Step-by-step instructions are provided

---

## 🔄 **Test Both Scenarios**

### Scenario 1: Coursework Data Available
If your system has some coursework data synced:
- Test questions should show actual assignment data

### Scenario 2: Coursework Data Restricted
If coursework data is empty/restricted:
- Test questions should show links and instructions

---

## 💡 **Recommended Test Flow**

1. **Start Simple**: Test "Show me my assignments"
2. **Test Course-Specific**: Test "What homework do I have in Math?"
3. **Test Mixed Queries**: Test "Show announcements and assignments"
4. **Verify Links**: Check that all links are clickable and go to Google Classroom
5. **Check Instructions**: Verify instructions are clear and helpful
6. **Verify Formatting**: Ensure Markdown formatting works correctly

---

## 🎯 **Quick Test (Start Here)**

Try these 3 questions first:

1. **"Show me my assignments"**
   - Should show links or data

2. **"What homework do I have for Math?"**
   - Should show Math course link or assignments

3. **"List all my coursework"**
   - Should show all courses with links or coursework data

---

Good luck testing! 🚀






