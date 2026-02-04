# DWD Classroom API Error Diagnosis

## Error Message
```
invalid_scope: https://www.googleapis.com/auth/classroom.courses.readonly is not a valid audience string.
```

## Current Status
- ✅ **Calendar API**: Works perfectly with 2 scopes
- ❌ **Classroom API**: Fails with 5 scopes
- ✅ **All scopes authorized** in Google Workspace Admin Console
- ✅ **JWT structure**: Identical for both APIs
- ✅ **Scope strings**: Verified clean (no hidden characters)

## What We've Tried

### 1. Scope Configuration
- ✅ Using API-specific scopes (5 Classroom scopes)
- ✅ Using all authorized scopes (8 scopes)
- ✅ Using single scope (to isolate issue)
- ✅ Verified scope strings are clean (hex encoding shows normal ASCII)

### 2. JWT Construction
- ✅ Using Google's official `google.auth.jwt.encode()` library
- ✅ Manual JWT encoding with proper formatting
- ✅ Preserving original JWT field order
- ✅ Using original JWT's timestamps and expiration

### 3. Credentials Configuration
- ✅ Setting scopes on credentials before JWT creation
- ✅ Not setting scopes (letting Google create JWT naturally)
- ✅ Re-signing JWT with correct scopes
- ✅ Not re-signing JWT (using original)

### 4. Request Body
- ✅ Removing scope from request body (only in JWT)
- ✅ Verified request body has no scope parameter

## JWT Structure (Verified Correct)
```json
{
  "iss": "prakriti-school-ai-service@prakriti-ai-assistant.iam.gserviceaccount.com",
  "sub": "dummy@learners.prakriti.org.in",
  "aud": "https://oauth2.googleapis.com/token",
  "iat": 1770108726,
  "exp": 1770112326,
  "scope": "https://www.googleapis.com/auth/classroom.courses.readonly https://www.googleapis.com/auth/classroom.rosters.readonly https://www.googleapis.com/auth/classroom.coursework.readonly https://www.googleapis.com/auth/classroom.student-submissions.students.readonly https://www.googleapis.com/auth/classroom.announcements.readonly"
}
```

## Authorized Scopes in Admin Console
All 8 scopes are authorized for Client ID: `105179368085912065226`

1. `https://www.googleapis.com/auth/classroom.courses.readonly`
2. `https://www.googleapis.com/auth/classroom.rosters.readonly`
3. `https://www.googleapis.com/auth/classroom.coursework.readonly`
4. `https://www.googleapis.com/auth/classroom.student-submissions.students.readonly`
5. `https://www.googleapis.com/auth/classroom.announcements.readonly`
6. `https://www.googleapis.com/auth/admin.directory.user.readonly`
7. `https://www.googleapis.com/auth/calendar.readonly`
8. `https://www.googleapis.com/auth/calendar.events.readonly`

## Key Observations

1. **Calendar works, Classroom doesn't** - Same approach, same JWT structure
2. **Error is very specific** - "is not a valid audience string" when mentioning a scope
3. **Scope strings are clean** - Hex encoding shows normal ASCII, no hidden characters
4. **JWT structure is correct** - Matches Calendar's working JWT exactly

## Possible Causes

1. **Google API Bug** - Classroom API might have a bug in DWD validation
2. **Classroom-Specific Requirement** - Classroom API might require something different
3. **Scope Validation Issue** - Google might be validating Classroom scopes differently
4. **Timing/Propagation Issue** - Admin Console changes might not have propagated for Classroom scopes

## Recommended Next Steps

1. **Contact Google Support** - This appears to be a Google API issue
2. **Check Google Issue Tracker** - Search for similar reports
3. **Verify Admin Console** - Double-check scope URLs match exactly (character-by-character)
4. **Try Different Service Account** - Test if issue is service-account specific
5. **Check API Enablement** - Ensure Classroom API is enabled in Google Cloud Console

## Test Results

- Calendar API: ✅ Works (2 scopes)
- Classroom API: ❌ Fails (5 scopes)
- JWT Structure: ✅ Identical for both
- Scope Authorization: ✅ All scopes authorized
- Scope Strings: ✅ Clean (no encoding issues)

## Conclusion

This appears to be a Google API issue specific to Classroom API Domain-Wide Delegation. The error message is unusual and doesn't match typical DWD errors. Since Calendar works with the exact same approach, and all scopes are authorized, this likely requires Google Support intervention.


