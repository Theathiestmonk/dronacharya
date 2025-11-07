# 🤖 GPT-4 vs GPT-3.5-turbo Query Guide

## 📋 Model Selection Logic

The chatbot uses **intelligent hybrid model selection** to optimize costs:

### ✅ GPT-3.5-turbo (95% cheaper) - Used when structured data exists:
- **Classroom data** available (announcements, coursework, students, teachers)
- **Calendar data** available (events, holidays)
- **Web crawler data** available (cached website content > 50 chars)

### 🚀 GPT-4 (Higher quality) - Used when NO structured data:
- No classroom data found
- No calendar data found  
- No meaningful web crawler data found
- Query requires complex reasoning or generation

---

## 🎯 Examples: Which Model is Used?

### ✅ GPT-3.5-turbo Examples (Has Structured Data)

#### 1. **Announcement Queries** (Classroom data)
```
"what announce on 21 sep"
→ Has: Classroom announcements
→ Uses: GPT-3.5-turbo
→ Cost: ~$0.002
```

#### 2. **Coursework Queries** (Classroom data)
```
"show me my assignments"
→ Has: Classroom coursework data
→ Uses: GPT-3.5-turbo
→ Cost: ~$0.002
```

#### 3. **Student/Teacher Queries** (Classroom data)
```
"who are the students in my class"
→ Has: Classroom student roster
→ Uses: GPT-3.5-turbo
→ Cost: ~$0.002
```

#### 4. **Calendar Queries** (Calendar data)
```
"what events are on October 15"
→ Has: Calendar events
→ Uses: GPT-3.5-turbo
→ Cost: ~$0.002
```

#### 5. **Web Crawler Queries** (Web data)
```
"what are prakriti school admission fees"
→ Has: Web crawler cached data
→ Uses: GPT-3.5-turbo
→ Cost: ~$0.002
```

#### 6. **General Query with Classroom Context** (Classroom data)
```
"can you help me with algebra"
→ Has: Classroom data (user logged in)
→ Uses: GPT-3.5-turbo
→ Cost: ~$0.002
```

---

### 🚀 GPT-4 Examples (No Structured Data)

#### 1. **Philosophical Questions**
```
"explain Prakriti's philosophy in detail"
→ No structured data found
→ Uses: GPT-4
→ Cost: ~$0.064
```

#### 2. **General School Information** (No Web Data)
```
"what makes Prakriti School special"
→ No web crawler data found (or not triggered)
→ Uses: GPT-4
→ Cost: ~$0.064
```

#### 3. **Creative/Generative Queries**
```
"write a poem about learning"
→ No structured data
→ Uses: GPT-4
→ Cost: ~$0.064
```

#### 4. **Complex Reasoning Queries**
```
"compare progressive education vs traditional education"
→ No structured data
→ Uses: GPT-4
→ Cost: ~$0.064
```

#### 5. **Questions Not in Knowledge Base**
```
"explain quantum physics"
→ No classroom/calendar/web data relevant
→ Uses: GPT-4
→ Cost: ~$0.064
```

---

## 🔍 How to Identify Which Model Will Be Used

### Check the logs for these messages:

**GPT-3.5-turbo:**
```
[Chatbot] 🤖 MODEL SELECTION: GPT-3.5-turbo (Data-Enhanced Query)
[Chatbot] 📊 Data sources available: Classroom
[Chatbot] 💰 Cost: ~$0.002-0.003 per query
```

**GPT-4:**
```
[Chatbot] 🤖 MODEL SELECTION: GPT-4 (Complex Query - No Structured Data)
[Chatbot] 💰 Cost: ~$0.064 per query
```

---

## 💡 Tips to Ensure GPT-3.5 Usage (Lower Cost)

1. **For logged-in users**: Most queries will have classroom data → GPT-3.5
2. **Use specific date queries**: "announcements on 21 sep" → triggers data fetch → GPT-3.5
3. **Ask about classroom content**: "my assignments", "my teachers" → GPT-3.5
4. **Use web crawler keywords**: "admission fees", "curriculum" → triggers web data → GPT-3.5

---

## ⚠️ When GPT-4 Will Be Used (Higher Cost)

1. **Guest users** asking general questions (no classroom access)
2. **Questions outside knowledge base** without web crawler trigger
3. **Complex philosophical/reasoning** queries
4. **Creative writing** requests
5. **Queries where web crawler finds no relevant data**

---

## 📊 Expected Distribution

Based on typical usage:
- **70-80% of queries**: Will use GPT-3.5-turbo (have structured data)
- **20-30% of queries**: Will use GPT-4 (no structured data)

### Cost Impact:
- **All GPT-4**: $0.064 per query average
- **Hybrid (70% GPT-3.5, 30% GPT-4)**: $0.020 per query average
- **Savings**: ~69% cost reduction

---

## 🎯 Query Examples by Model

### ✅ GPT-3.5-turbo Queries (95% of typical usage)

| Query Type | Example | Data Source |
|------------|---------|-------------|
| Announcements | "what announce on 25 sep" | Classroom |
| Assignments | "show me my homework" | Classroom |
| Students | "who are my classmates" | Classroom |
| Teachers | "list teachers in my course" | Classroom |
| Calendar | "events on October" | Calendar |
| Fees | "admission fees" | Web Crawler |
| Curriculum | "what subjects are offered" | Web Crawler |

### 🚀 GPT-4 Queries (5-30% of usage)

| Query Type | Example | Reason |
|------------|---------|--------|
| Philosophy | "explain Prakriti's learning approach" | Complex reasoning |
| General Info | "what is Prakriti School" | No data (guest user) |
| Creative | "write about education" | Generative |
| Comparison | "progressive vs traditional" | Complex reasoning |
| Academic | "explain calculus" | No classroom data |

---

## 💰 Cost Comparison Examples

### Example 1: Announcement Query
```
Query: "what announce on 21 sep"
→ Model: GPT-3.5-turbo
→ Cost: $0.0015
→ vs GPT-4: $0.0365
→ Savings: 96%
```

### Example 2: General Question (Guest)
```
Query: "what is Prakriti School"
→ Model: GPT-4 (no web data triggered)
→ Cost: $0.064
→ Note: Could use GPT-3.5 if web crawler finds data
```

### Example 3: Algebra Help (Logged in)
```
Query: "help me with algebra"
→ Model: GPT-3.5-turbo (has classroom data)
→ Cost: $0.0015
→ vs GPT-4: $0.0365
→ Savings: 96%
```

---

## 🔧 Current Implementation

The system checks in this order:
1. **Classroom data** available? → GPT-3.5
2. **Calendar data** available? → GPT-3.5
3. **Web data** available (>50 chars)? → GPT-3.5
4. **None of above**? → GPT-4

This ensures maximum cost savings while maintaining quality for complex queries.

---

*Last updated: After implementing hybrid model selection*














