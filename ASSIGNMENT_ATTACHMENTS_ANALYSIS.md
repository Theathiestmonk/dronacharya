# Assignment Attachments & Download Feature Analysis

## Current State Analysis

### ✅ **What EXISTS:**

1. **Database Schema Supports Materials:**
   - The `google_classroom_coursework` table has a `materials` JSONB field (line 95 in `google_integrations_schema.sql`)
   - This field stores an array of materials from Google Classroom assignments, including:
     - Drive files (`driveFile`)
     - YouTube videos (`youtubeVideo`)
     - Links (`link`)
     - Forms (`form`)

2. **Materials Are Being Synced:**
   - ✅ Student sync: Materials are stored during sync (line 180 in `frontend/src/pages/api/student/google-classroom/sync.ts`)
   - ✅ Admin sync: Materials are stored during admin sync (line 327 in `frontend/src/pages/api/admin/sync/[service].ts`)

### ❌ **What's MISSING:**

1. **Materials Are NOT Being Fetched:**
   - In `backend/app/agents/chatbot_agent.py`, the `get_student_coursework_data()` function (line 129-130) does NOT include `materials` in the SELECT query:
   ```python
   coursework_result = supabase.table('google_classroom_coursework').select(
       'id, course_id, coursework_id, title, description, due_date, due_time, state, alternate_link, max_points, work_type'
   ).in_('id', list(coursework_ids_from_submissions))...
   ```
   - **Missing:** `materials` field is not selected, so attachments are never retrieved

2. **No Frontend Support for File Attachments:**
   - The `Message` type in `Chatbot.tsx` (lines 9-13) only supports:
     - Text messages
     - Calendar links
     - Map links
     - Video lists
   - **Missing:** No type for file attachments or downloadable materials

3. **No Download Functionality:**
   - There's no UI component or handler for downloading files
   - No file preview or download buttons in assignment responses

4. **Materials Not Included in Response:**
   - When assignments are formatted for the LLM prompt, materials are not included
   - The coursework data structure (line 233-247 in `chatbot_agent.py`) doesn't include materials

---

## Implementation Requirements

### **To Enable Attachments with Assignments:**

#### **Backend Changes:**

1. **Update `get_student_coursework_data()` function:**
   - Add `materials` to the SELECT query (line 130)
   - Include `materials` in the coursework data structure (line 233-247)

2. **Parse and Format Materials:**
   - Extract different material types:
     - `driveFile` → Google Drive file (needs download URL generation)
     - `youtubeVideo` → YouTube video link
     - `link` → Direct URL
     - `form` → Google Form link
   - Format materials for inclusion in assignment data

3. **Update LLM Prompt:**
   - Include materials in the assignment data sent to the LLM
   - Add instructions for the LLM to display attachments with download options

#### **Frontend Changes:**

1. **Extend Message Type:**
   ```typescript
   type Message =
     | { sender: 'user' | 'bot'; text: string }
     | { sender: 'bot'; type: 'calendar'; url: string }
     | { sender: 'bot'; type: 'map'; url: string }
     | { sender: 'bot'; type: 'videos'; videos: Array<...> }
     | { sender: 'bot'; type: 'assignment'; assignment: AssignmentData } // NEW
   
   type AssignmentData = {
     title: string;
     description?: string;
     dueDate?: string;
     link: string;
     materials?: Material[]; // NEW
   }
   
   type Material = {
     type: 'driveFile' | 'youtubeVideo' | 'link' | 'form';
     title?: string;
     url: string;
     downloadUrl?: string; // For Drive files
   }
   ```

2. **Create Attachment Component:**
   - Display file attachments with download buttons
   - Show file type icons
   - Handle different material types (Drive files, links, videos, forms)

3. **Update Chatbot Response Handler:**
   - Detect assignment responses with materials
   - Render attachments below assignment information
   - Add download functionality for Drive files

4. **Download Functionality:**
   - For Google Drive files: Generate download URLs (may require OAuth token)
   - For direct links: Open in new tab or download
   - For YouTube videos: Embed or link to video
   - For forms: Link to Google Form

---

## Material Data Structure (from Google Classroom API)

Based on the sync code, materials have this structure:

```typescript
materials: [
  {
    driveFile: {
      driveFile: {
        id: "file_id",
        title: "Assignment.pdf",
        alternateLink: "https://drive.google.com/...",
        thumbnailUrl: "..."
      }
    }
  },
  {
    youtubeVideo: {
      id: "video_id",
      title: "Video Title",
      alternateLink: "https://youtube.com/..."
    }
  },
  {
    link: {
      url: "https://example.com",
      title: "Link Title",
      thumbnailUrl: "..."
    }
  },
  {
    form: {
      formUrl: "https://docs.google.com/forms/...",
      responseUrl: "...",
      thumbnailUrl: "...",
      title: "Form Title"
    }
  }
]
```

---

## Recommended Implementation Steps

### Phase 1: Backend - Fetch Materials
1. ✅ Update `get_student_coursework_data()` to include `materials` in SELECT
2. ✅ Add `materials` to coursework data structure
3. ✅ Parse materials array and format for LLM
4. ✅ Update LLM prompt to include materials in assignment responses

### Phase 2: Backend - Format Materials for Frontend
1. ✅ Create helper function to parse materials JSONB
2. ✅ Generate download URLs for Drive files (may need OAuth)
3. ✅ Format materials as structured data for frontend

### Phase 3: Frontend - Display Attachments
1. ✅ Extend Message type to support assignments with materials
2. ✅ Create `AssignmentAttachments` component
3. ✅ Add download buttons and file type icons
4. ✅ Handle different material types (Drive, Link, YouTube, Form)

### Phase 4: Frontend - Download Functionality
1. ✅ Implement download handler for Drive files
2. ✅ Add download progress indicator
3. ✅ Handle errors (permissions, file not found, etc.)
4. ✅ Test with various file types

---

## Challenges & Considerations

1. **Google Drive File Access:**
   - Drive files may require OAuth token for download
   - Need to check file permissions
   - May need to generate temporary download URLs

2. **File Size:**
   - Large files may need streaming or chunked download
   - Consider file size limits

3. **Security:**
   - Validate file URLs before allowing downloads
   - Ensure user has permission to access the file
   - Sanitize file names for download

4. **User Experience:**
   - Show file type icons
   - Display file sizes if available
   - Show download progress
   - Handle download errors gracefully

---

## Conclusion

**Current Answer:** ❌ **NO** - Attachments cannot currently be sent with assignments, and there's no download option.

**Feasibility:** ✅ **YES** - The infrastructure exists (materials are stored in DB), but implementation is needed:
- Backend: Fetch and format materials
- Frontend: Display and download attachments

**Estimated Complexity:** Medium
- Backend changes: ~2-3 hours
- Frontend changes: ~4-6 hours
- Testing: ~2-3 hours
- **Total: ~8-12 hours**

