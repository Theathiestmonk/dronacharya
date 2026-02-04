# DWD Production Setup Guide

## Problem: DWD works on localhost but fails on production domain

If you see errors like:
- `access_denied: Requested client not authorized`
- `unauthorized_client`
- No DWD logs in production

**IMPORTANT FIX (2025):** For Domain-Wide Delegation, Google determines scopes from Admin Console authorization, NOT from the JWT. The JWT should NOT contain a scope field - including it can cause "not a valid audience string" errors. The code has been updated to remove the scope field from JWT for DWD requests.

## Quick Fix Steps

### 1. Get Your Client ID

Call this endpoint on your production backend:
```bash
curl https://your-backend-domain.com/api/admin/dwd/client-id
```

Or check the startup logs - the Client ID is now logged when the server starts.

### 2. Authorize Client ID in Google Workspace Admin Console

1. Go to: https://admin.google.com
2. Navigate to: **Security** → **API Controls** → **Domain-wide Delegation**
3. Click **"Add new"**
4. Enter the **Client ID** from step 1 (copy EXACTLY, no spaces)
5. In **OAuth scopes**, add these EXACT URLs (one per line):

```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.rosters.readonly
https://www.googleapis.com/auth/classroom.announcements.readonly
https://www.googleapis.com/auth/classroom.coursework.students.readonly
https://www.googleapis.com/auth/classroom.student-submissions.students.readonly
https://www.googleapis.com/auth/admin.directory.user.readonly
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events.readonly
```

**Note:** We use `classroom.student-submissions.students.readonly` for both students and faculty. For students, we filter results in code to show only their own submissions. This simplifies scope management - you don't need `classroom.student-submissions.me.readonly`.

6. Click **"Authorize"**
7. **Wait 15-30 minutes** for changes to propagate

### 3. Verify Environment Variables in Render

Go to Render Dashboard → Your Service → Environment and ensure:

```
GOOGLE_WORKSPACE_DOMAIN=learners.prakriti.org.in
GOOGLE_SERVICE_ACCOUNT_JSON=<paste entire JSON content>
```

**OR** if using file path:
```
GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/backend/service-account-key.json
GOOGLE_WORKSPACE_DOMAIN=learners.prakriti.org.in
```

### 4. Test DWD Status

```bash
# Check status
curl https://your-backend-domain.com/api/admin/dwd/status

# Run comprehensive diagnostic
curl https://your-backend-domain.com/api/admin/dwd/diagnose
```

### 5. Check Production Logs

After deploying, check Render logs for:
```
[DWD] ✅ Service available
[DWD] Client ID: <your-client-id>
[DWD] Workspace Domain: learners.prakriti.org.in
```

If you see `[DWD] ❌ Service not available`, check environment variables.

## Common Issues

### Issue: "access_denied: Requested client not authorized"

**Solution:**
- Client ID is not authorized in Admin Console
- Follow step 2 above
- Ensure Client ID matches EXACTLY (no spaces, no typos)
- Wait 15-30 minutes after authorization

### Issue: No DWD logs in production

**Solution:**
- Check environment variables are set in Render
- Verify `GOOGLE_SERVICE_ACCOUNT_JSON` contains valid JSON
- Check startup logs for `[DWD]` messages
- Restart the service after setting environment variables

### Issue: Domain mismatch

**Solution:**
- Set `GOOGLE_WORKSPACE_DOMAIN=learners.prakriti.org.in` in Render
- Ensure user emails are in the `learners.prakriti.org.in` domain

## Diagnostic Endpoints

### Get Client ID:
```
GET /api/admin/dwd/client-id
```

### Check Status:
```
GET /api/admin/dwd/status
```

### Comprehensive Diagnostic:
```
GET /api/admin/dwd/diagnose
```

## Verification Checklist

- [ ] Client ID retrieved from `/api/admin/dwd/client-id`
- [ ] Client ID authorized in Google Admin Console
- [ ] All 8 OAuth scopes added (one per line)
- [ ] Environment variables set in Render
- [ ] `GOOGLE_WORKSPACE_DOMAIN=learners.prakriti.org.in`
- [ ] Service restarted after environment variable changes
- [ ] Waited 15-30 minutes after Admin Console authorization
- [ ] `/api/admin/dwd/status` shows `"available": true`
- [ ] Production logs show `[DWD] ✅ Service available`

## Still Not Working?

1. Run the diagnostic endpoint and check all checks pass
2. Compare localhost vs production diagnostic outputs
3. Verify the service account JSON is identical in both environments
4. Check Google Cloud Console API quotas
5. Ensure Admin SDK API is enabled in Google Cloud Console

## Support

If issues persist:
1. Run: `curl https://your-backend-domain.com/api/admin/dwd/diagnose`
2. Check Render logs for `[DWD]` messages
3. Compare with localhost diagnostic output
4. Verify Google Workspace Admin Console authorization
