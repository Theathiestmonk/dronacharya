# Token Usage Optimization Suggestions for Chatbot Agent

## Current Issues Identified

1. **Very Long System Prompts** (~150-200 lines of instructions)
2. **Redundant Formatting Instructions** (~50-100 lines repeated in user_content)
3. **Large Admin Data Payloads** (even with filtering, could be more aggressive)
4. **Conversation History** (limited to 5, but could be smarter)
5. **Web Info Truncation** (800 chars, could be more selective)
6. **Token Estimation Threshold** (6000 tokens threshold may be too high)

---

## Priority Recommendations (High Impact)

### 1. **Simplify and Shorten System Prompts** ⭐⭐⭐ (HIGHEST PRIORITY)
**Current:** System prompts are 200+ lines with repetitive instructions
**Impact:** Could save 500-1000 tokens per request

**Actions:**
- Create concise base system prompt (~30-40 lines max)
- Move role-specific guidelines to separate short variables (only include if needed)
- Remove redundant instructions that are already in the base prompt
- Use shorter, more direct language
- Combine similar instruction points

**Example Reduction:**
```
Instead of 50 lines of formatting instructions, use:
"Format responses with Markdown: **bold**, *italic*, ### headings. 
Process time ranges (add 'to' between times), fix grammar, use tables for lists."
```

### 2. **Move Formatting Instructions Out of User Content** ⭐⭐⭐
**Current:** 50-100 lines of formatting instructions added to every request
**Impact:** Could save 200-400 tokens per request

**Actions:**
- Add formatting rules ONCE to system prompt (not repeated in user_content)
- Only add specific query-type instructions when absolutely necessary
- Use shorter, coded instructions (e.g., "FORMAT_AS_TABLE" instead of 10 lines explaining how)

### 3. **Implement Smarter Conversation History** ⭐⭐
**Current:** Always includes last 5 messages
**Impact:** Could save 100-300 tokens per request

**Actions:**
- Only include conversation history when necessary (not for simple queries)
- Use message summarization for older messages (summarize messages 3-5 into 1 summary)
- Skip history entirely for stateless queries (announcements, calendar, coursework queries)
- Implement intelligent truncation: keep recent messages full, older ones summarized

### 4. **Aggressive Data Filtering & Summarization** ⭐⭐⭐
**Current:** Sends filtered but still large JSON payloads
**Impact:** Could save 500-2000 tokens per request

**Actions:**
- **Reduce default limits further:**
  - Announcements: 20 → 10 (or 5 for date-specific queries)
  - Students: 50 → 20-30 max
  - Teachers: 50 → 10-15 max (rarely need more)
  - Coursework: 20 → 10 max
  
- **Implement text summarization for announcements:**
  - For long announcements (>200 chars), send summary + full text only if explicitly requested
  - Truncate announcement text to first 150-200 chars by default
  
- **Use field-specific loading:**
  - Only load email addresses when explicitly requested (already done, but can be more aggressive)
  - Only load full profile data when needed
  
- **Send structured summaries instead of full JSON:**
  ```
  Instead of full JSON, send:
  "Course: Math 101
   - Announcements (3): [Date1: Summary1], [Date2: Summary2]
   - Students: 25 total (names only)"
  ```

### 5. **Optimize Query Intent Detection** ⭐⭐
**Current:** Loads all data types even when not needed
**Impact:** Could save 200-800 tokens per request

**Actions:**
- Make intent detection more aggressive (higher confidence threshold)
- Only load ONE data type per query unless query explicitly mentions multiple
- For ambiguous queries, default to minimal data (just course names, no details)

### 6. **Reduce Web Info Size** ⭐
**Current:** 800 chars truncation
**Impact:** Could save 50-200 tokens per request

**Actions:**
- Reduce to 400-500 chars for non-critical queries
- Only include web info when query explicitly needs current/recent information
- Extract only relevant snippets instead of sending full text

### 7. **Optimize Token Estimation & Threshold** ⭐
**Current:** 6000 token threshold
**Impact:** Better proactive reduction

**Actions:**
- Lower threshold to 4000-4500 tokens (safer margin)
- Implement progressive compression:
  - First pass: Remove formatting instructions from user_content
  - Second pass: Summarize data
  - Third pass: Use ultra-compact format

### 8. **Cache and Reuse System Prompts** ⭐
**Current:** Rebuilds system prompt every request
**Impact:** Minimal token saving, but faster processing

**Actions:**
- Cache system prompts by user role (student/teacher/parent/guest)
- Only rebuild when user profile changes
- Use shorter identifiers for repeated phrases

---

## Implementation Strategy

### Phase 1: Quick Wins (1-2 hours)
1. Shorten system prompts (remove redundancy)
2. Move formatting instructions to system prompt
3. Reduce default data limits
4. Lower conversation history from 5 to 3 messages

**Expected Savings:** ~1000-1500 tokens per request

### Phase 2: Medium Changes (2-4 hours)
1. Implement smarter conversation history
2. Add text summarization for long announcements
3. More aggressive intent detection
4. Progressive compression for large payloads

**Expected Savings:** ~500-1000 additional tokens per request

### Phase 3: Advanced Optimizations (4-8 hours)
1. Implement data summarization before sending to LLM
2. Intelligent caching system
3. Dynamic token budget allocation (more tokens for complex queries)
4. Query classification to determine minimal data needed

**Expected Savings:** ~300-800 additional tokens per request

---

## Code-Level Changes

### 1. Create Compact System Prompt Generator
```python
def get_system_prompt(user_profile=None):
    """Generate concise system prompt (30-40 lines max)"""
    base = """You are Prakriti School's AI assistant. 
    Philosophy: "Learning for happiness" - progressive K-12 school in Greater Noida.
    Format: Use Markdown (**bold**, ### headings, tables). Process time ranges (add 'to'), fix grammar."""
    
    if user_profile:
        role = user_profile.get('role', '')
        name = user_profile.get('first_name', '')
        # Add only essential personalization (5-10 lines)
        return base + f"\nUser: {name} ({role})"
    return base
```

### 2. Implement Smart History Management
```python
def get_conversation_history_messages(history, user_query):
    """Only include history when needed"""
    query_needs_context = any(kw in user_query.lower() for kw in [
        'previous', 'earlier', 'before', 'continue', 'follow up'
    ])
    
    if not query_needs_context or len(history) < 2:
        return []  # Skip history for simple queries
    
    # Include only last 2-3 messages
    recent = history[-2:] if len(history) > 2 else history
    return [{"role": msg["role"], "content": msg["content"]} for msg in recent]
```

### 3. Aggressive Data Limits
```python
# In get_admin_data call:
limit_teachers = 10 if should_load_teachers else None  # Reduced from 50
limit_students = 20 if should_load_students else None   # Reduced from 50
limit_announcements = 5 if should_load_announcements else None  # Reduced from 20
limit_coursework = 10 if should_load_coursework else None  # Reduced from 20
```

### 4. Summarize Long Announcements
```python
def summarize_announcement(text, max_length=150):
    """Truncate announcements intelligently"""
    if len(text) <= max_length:
        return text
    # Truncate at sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    if last_period > max_length * 0.7:  # If period is reasonably close
        return truncated[:last_period+1] + "..."
    return truncated + "..."
```

---

## Monitoring & Metrics

Track these metrics to measure improvements:
1. **Average tokens per request** (before optimization vs after)
2. **Token distribution:** System prompt / User content / Data payload / History
3. **Query types:** Which queries use most tokens
4. **Response quality:** Ensure optimization doesn't hurt quality

---

## Expected Results

**Before Optimization:**
- Average request: 4000-8000 tokens
- Large requests: 10000+ tokens

**After Phase 1:**
- Average request: 2500-4500 tokens (40-50% reduction)
- Large requests: 6000-8000 tokens

**After Phase 2:**
- Average request: 2000-3500 tokens (50-60% reduction)
- Large requests: 4000-6000 tokens

**After Phase 3:**
- Average request: 1500-3000 tokens (60-70% reduction)
- Large requests: 3000-5000 tokens

---

## Notes

- Always test response quality after optimization
- Some queries may need more context (complex questions) - use dynamic budgets
- Monitor user satisfaction - don't sacrifice quality for token savings
- Consider using cheaper models (gpt-3.5-turbo) for simple queries

