# Domain-Wide Delegation Admin Console Setup

## Service Account Details

**Service Account Email:**
```
prakriti-school-ai-service@prakriti-ai-assistant.iam.gserviceaccount.com
```

**Client ID (MUST match exactly):**
```
105179368085912065226
```

**Project ID:**
```
prakriti-ai-assistant
```

---

## Admin Console Setup Steps

### Step 1: Go to Domain-Wide Delegation

1. Go to: **https://admin.google.com**
2. Sign in with a **Super Admin** account
3. Navigate to: **Security** → **Access and data control** → **API controls**
4. Click: **"Domain-wide Delegation"** (or "Manage Domain-Wide Delegation")

### Step 2: Remove Existing Authorization (if any)

1. Find Client ID: `105179368085912065226`
2. If it exists, **DELETE it completely**
3. Wait 5 minutes

### Step 3: Add New Authorization

1. Click **"Add new"** or **"Authorize"**
2. Enter Client ID: `105179368085912065226`
   - **IMPORTANT:** Type it manually or copy-paste exactly (no spaces)
   - Verify it's exactly 21 digits: `105179368085912065226`

### Step 4: Add ONLY These 5 Scopes

**Copy and paste these EXACTLY (one per line, no extra spaces):**

```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.rosters.readonly
https://www.googleapis.com/auth/classroom.announcements.readonly
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events.readonly
```

**CRITICAL:**
- ✅ Each scope on its own line
- ✅ No leading/trailing spaces
- ✅ Must start with `https://`
- ✅ Must end with `.readonly`
- ✅ Exactly 5 scopes (no more, no less)
- ❌ DO NOT add any other scopes
- ❌ DO NOT use `classroom.coursework.readonly` (invalid)
- ❌ DO NOT use `classroom.student-submissions.readonly` (invalid)

### Step 5: Authorize

1. Click **"Authorize"**
2. Verify it appears in the list
3. Wait **15-30 minutes** for propagation

---

## API Access Control

1. Go to: **Security** → **API Controls** → **API Access Control**
2. Ensure it's set to **"Unrestricted"** (not "Restricted")
3. If restricted, add your app to the allowed list

---

## Verification Checklist

After setup, verify:

- [ ] Client ID matches exactly: `105179368085912065226`
- [ ] Exactly 5 scopes are listed (no more, no less)
- [ ] All 5 scopes match exactly (no typos)
- [ ] Each scope is on its own line
- [ ] Authorization is saved and visible in the list
- [ ] API Access Control is set to "Unrestricted"
- [ ] Waited 15-30 minutes after authorization

---

## Test After Setup

Run the test script to verify:

```bash
python scripts/test_dwd_fetch.py services@atsnai.com
```

You should see:
- ✅ JWT has no scope parameter (correct for DWD)
- ✅ Successful API calls (no errors)

---

## Current Status

**Code Logic:** ✅ CORRECT
- JWT has no scope field (correct for DWD)
- Request body has no scope parameter
- All patches are working

**Admin Console:** ⚠️ NEEDS VERIFICATION
- Client ID: `105179368085912065226`
- Must have exactly 5 scopes (remove any others)
- Must match exactly (no typos, no extra spaces)









