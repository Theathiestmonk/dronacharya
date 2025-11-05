# OAuth "invalid_grant" Error - Quick Fix Checklist

## 🔴 The Error You're Seeing:
```
Token exchange failed: Bad Request
error: invalid_grant
"The authorization code may have been used already or has expired"
```

## ✅ Step-by-Step Fix (5 minutes)

### Step 1: Verify Google Cloud Console Redirect URIs

1. Go to: https://console.cloud.google.com/
2. Navigate to: **APIs & Services** → **Credentials**
3. Click your **OAuth 2.0 Client ID**
4. Under **Authorized redirect URIs**, verify you have:

```
https://prakritischool.ai/admin/callback
http://localhost:3000/admin/callback
```

**Check:**
- [ ] No trailing slash (`/admin/callback` not `/admin/callback/`)
- [ ] Correct protocol (`https://` for production, `http://` for localhost)
- [ ] Exact spelling: `admin/callback` (not `admin/call-back` or `adminCallback`)

### Step 2: Verify Vercel Environment Variables

1. Go to: https://vercel.com/dashboard
2. Select your project
3. Go to: **Settings** → **Environment Variables**
4. Verify these variables exist in **Production**:

```
GOOGLE_REDIRECT_URI=https://prakritischool.ai/admin/callback
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Check:**
- [ ] `GOOGLE_REDIRECT_URI` matches Google Console EXACTLY
- [ ] No trailing slash
- [ ] Using `https://` (not `http://`)

### Step 3: Verify Render Environment Variables

1. Go to: https://dashboard.render.com/
2. Select your backend service
3. Go to: **Environment**
4. Verify:

```
GOOGLE_REDIRECT_URI=https://prakritischool.ai/admin/callback
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Check:**
- [ ] `GOOGLE_REDIRECT_URI` matches Google Console EXACTLY
- [ ] Same value as in Vercel

### Step 4: Restart Services

**After changing environment variables:**

1. **Render:** Click "Manual Deploy" → "Deploy latest commit" (or wait for auto-restart)
2. **Vercel:** If variables changed, trigger a new deployment

### Step 5: Test Again

1. Clear browser cache for `prakritischool.ai`
2. Go to: https://prakritischool.ai/admin
3. Click **"Connect Google Classroom & Calendar"**
4. Complete OAuth flow
5. **Don't refresh** the callback page - let it redirect automatically

## 🎯 Quick Verification

Run this in your browser console on `prakritischool.ai/admin`:

```javascript
// Check what redirect URI is being used
fetch('/api/admin/auth-url?service=both&email=your-email@example.com')
  .then(r => r.json())
  .then(data => {
    const url = new URL(data.auth_url);
    console.log('Redirect URI in auth URL:', url.searchParams.get('redirect_uri'));
  });
```

This should show: `https://prakritischool.ai/admin/callback`

## ⚠️ Common Mistakes

| Wrong ❌ | Correct ✅ |
|----------|-----------|
| `https://prakritischool.ai/admin/callback/` | `https://prakritischool.ai/admin/callback` |
| `http://prakritischool.ai/admin/callback` | `https://prakritischool.ai/admin/callback` |
| `https://prakritischool.ai/admin` | `https://prakritischool.ai/admin/callback` |
| `https://api.prakritischool.ai/admin/callback` | `https://prakritischool.ai/admin/callback` |

## 🔍 Still Not Working?

1. **Check browser console logs** - Look for `🔍 [CALLBACK API] Using redirect_uri:`
2. **Check Render logs** - Look for `🔍 GOOGLE_REDIRECT_URI:`
3. **Verify exact match** - The three places must match EXACTLY:
   - Google Console redirect URI
   - Vercel `GOOGLE_REDIRECT_URI` env var
   - Render `GOOGLE_REDIRECT_URI` env var

## 💡 Pro Tip

If you get "code already used" error but the integration actually succeeded:
- The improved error handling will automatically check if you're already connected
- Just go back to the admin dashboard - you should see "Connected" status

---

**Most Important:** All three redirect URIs must match EXACTLY (character-by-character):
1. Google Cloud Console
2. Vercel Environment Variable
3. Render Environment Variable










