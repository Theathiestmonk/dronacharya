# Deployment Configuration for prakritischool.ai

## 🌐 Domain Setup
**Your Domain:** https://prakritischool.ai/

---

## 📦 Render (Backend) Configuration

### Render Service URL
Your backend will be deployed at something like:
- `https://your-app-name.onrender.com` (free tier)
- Or your custom domain: `https://api.prakritischool.ai` (if configured)

**Note:** Replace `your-app-name.onrender.com` with your actual Render service URL.

### Environment Variables for Render

Go to **Render Dashboard → Your Service → Environment** and add:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://prakritischool.ai/admin/callback

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# Backend URL (if needed for internal calls)
BACKEND_URL=https://your-app-name.onrender.com
# OR if using custom domain:
# BACKEND_URL=https://api.prakritischool.ai
```

### Render Build Settings
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## 🚀 Vercel (Frontend) Configuration

### Vercel Project URL
Your frontend will be at: `https://prakritischool.ai`

### Environment Variables for Vercel

Go to **Vercel Dashboard → Your Project → Settings → Environment Variables** and add:

#### Production Environment:
```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://prakritischool.ai/admin/callback

# Backend API URL (Your Render backend URL)
BACKEND_URL=https://your-app-name.onrender.com
# OR if using custom domain:
# BACKEND_URL=https://api.prakritischool.ai
```

#### Preview/Development Environment:
```bash
# Same as above, or use localhost URLs for development
BACKEND_URL=http://localhost:8000
GOOGLE_REDIRECT_URI=http://localhost:3000/admin/callback
```

---

## 🔐 Google Cloud Console Configuration

### Step 1: Go to Google Cloud Console
Visit: https://console.cloud.google.com/

### Step 2: Select Your Project
Choose the project where your OAuth credentials are created.

### Step 3: Navigate to OAuth 2.0 Client IDs
1. Go to **APIs & Services** → **Credentials**
2. Find your OAuth 2.0 Client ID
3. Click **Edit** (pencil icon)

### Step 4: Add Authorized Redirect URIs

**CRITICAL:** Add these redirect URIs **EXACTLY** as shown (copy-paste to avoid typos):

```
https://prakritischool.ai/admin/callback
https://www.prakritischool.ai/admin/callback
http://localhost:3000/admin/callback
```

**Important Notes:**
- ✅ The redirect URI **MUST** point to your **frontend** domain, not backend
- ✅ **EXACT MATCH REQUIRED:** The URI in Google Console must match EXACTLY what you set in `GOOGLE_REDIRECT_URI` env variable (including http/https, no trailing slash)
- ✅ Include both `https://prakritischool.ai` and `https://www.prakritischool.ai` if you use both
- ✅ Keep `http://localhost:3000/admin/callback` for local development (with `http://` not `https://`)
- ❌ Do NOT add `https://your-app-name.onrender.com/api/admin/callback` (this is wrong!)
- ❌ Do NOT add trailing slashes: use `/admin/callback` not `/admin/callback/`

**Common Mistakes to Avoid:**
- ❌ Wrong: `https://prakritischool.ai/admin/callback/` (trailing slash)
- ❌ Wrong: `prakritischool.ai/admin/callback` (missing https://)
- ❌ Wrong: `https://prakritischool.ai/admin` (missing /callback)
- ✅ Correct: `https://prakritischool.ai/admin/callback` (exact match)

### Step 5: Save Changes
Click **Save** at the bottom of the page.

---

## 📝 Required Google APIs

Make sure these APIs are enabled in Google Cloud Console:
1. **Google Classroom API**
2. **Google Calendar API**

Enable them at: **APIs & Services** → **Library**

---

## 🔄 Code Updates Required

The frontend code has hardcoded `localhost:8000` URLs that need to be updated. I'll create environment variable support for this.

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Render backend is accessible at your backend URL
- [ ] Vercel frontend is accessible at https://prakritischool.ai
- [ ] Google OAuth redirect URI is added in Google Console
- [ ] All environment variables are set in both Render and Vercel
- [ ] Test Google Classroom connection from admin dashboard
- [ ] Test Google Calendar connection from admin dashboard

---

## 🐛 Troubleshooting

### Issue: "invalid_grant" or "Token exchange failed: Bad Request"
**This is the #1 OAuth error!** It means the redirect URI doesn't match.

**Solution Steps:**
1. **Check Google Console:** Go to OAuth 2.0 Client ID → Authorized redirect URIs
   - Verify `https://prakritischool.ai/admin/callback` is listed EXACTLY (no trailing slash, correct protocol)
   
2. **Check Environment Variables:**
   - In **Vercel**: `GOOGLE_REDIRECT_URI=https://prakritischool.ai/admin/callback`
   - In **Render**: `GOOGLE_REDIRECT_URI=https://prakritischool.ai/admin/callback`
   - They MUST be identical and match Google Console EXACTLY
   
3. **If code was already used (page refresh):**
   - The code will show: "The authorization code may have been used already"
   - **Fix:** Go back to admin dashboard and click "Connect" again (don't refresh the callback page)
   - The improved error handling will automatically check if integration already exists

4. **Verify in logs:**
   - Check browser console for: `🔍 [CALLBACK API] Using redirect_uri: ...`
   - This should show: `https://prakritischool.ai/admin/callback`
   - If it shows `localhost:3000` in production, your env variable isn't set correctly

### Issue: OAuth redirect mismatch
**Solution:** Ensure `GOOGLE_REDIRECT_URI` in both Render and Vercel matches EXACTLY what's in Google Console (character-by-character match, including http/https, no trailing slash)

### Issue: CORS errors
**Solution:** Make sure Render backend CORS allows `https://prakritischool.ai` origin

### Issue: Backend not accessible
**Solution:** Check Render service logs and ensure the service is running

### Issue: "Code already used" error
**Solution:** 
- Don't refresh the callback page after connecting
- If you see this error, check if integration already exists (improved error handling will do this automatically)
- If integration exists, just go back to admin dashboard - you're already connected!

---

## 📞 Quick Reference

**Frontend URL:** https://prakritischool.ai  
**Backend URL:** https://your-app-name.onrender.com (or custom domain)  
**OAuth Redirect:** https://prakritischool.ai/admin/callback

---

**Last Updated:** 2025-01-31

