# Admin Directory Scope Testing for DWD

This directory contains test scripts for checking admin user directory access permissions in the Google Workspace Domain-Wide Delegation (DWD) system.

## Overview

The DWD system allows service accounts to impersonate Google Workspace users to access their data. For admin users to access directory information, specific Google API scopes must be authorized in the Google Workspace Admin Console.

## Test Scripts

### 1. `check_admin_scopes.py` - Quick Scope Checker
**Purpose:** Simple, fast check for basic directory access permissions.

**Usage:**
```bash
# Test specific admin
python check_admin_scopes.py admin@domain.com

# Or set environment variable
export TEST_ADMIN_EMAIL=admin@domain.com
python check_admin_scopes.py
```

**What it tests:**
- Service account configuration
- Admin user existence in database
- Basic directory API access
- Basic Google Drive API access

**Output:** Simple ✅/❌ results with actionable error messages.

---

### 2. `test_admin_directory_scopes.py` - Comprehensive Scope Tester
**Purpose:** Detailed testing of all directory-related scopes with full reporting.

**Usage:**
```bash
# Test specific admin
python test_admin_directory_scopes.py admin@domain.com

# Or set environment variable
export TEST_ADMIN_EMAIL=admin@domain.com
python test_admin_directory_scopes.py
```

**What it tests:**
- Service account credentials
- Admin user database existence
- Directory service creation
- Drive service creation
- Directory user access
- Drive file access
- Directory group access
- Organizational unit access

**Output:** Detailed JSON report saved to `admin_directory_scopes_test_results.json`

---

### 3. `test_dwd_scope_authorization.py` - Specific Scope Authorization Tester
**Purpose:** Tests individual Google API scopes to verify exact authorization levels.

**Usage:**
```bash
# Test specific admin
python test_dwd_scope_authorization.py admin@domain.com

# Or set environment variable
export TEST_ADMIN_EMAIL=admin@domain.com
python test_dwd_scope_authorization.py
```

**Scopes tested:**
- `admin.directory.user.readonly` - Read user directory information
- `admin.directory.group.readonly` - Read group directory information
- `admin.directory.orgunit.readonly` - Read organizational unit information
- `drive.readonly` - Read Google Drive files
- `drive.file` - Create/modify Google Drive files
- `cloud-platform.readonly` - Read Google Cloud resources

**Output:** Scope-by-scope authorization results with error details.

---

### 4. `batch_admin_scope_test.py` - Batch Testing for All Admins
**Purpose:** Test directory scope authorization for all admin users in the system.

**Usage:**
```bash
# Test all admins in database
python batch_admin_scope_test.py

# Test specific admins only
python batch_admin_scope_test.py admin1@domain.com admin2@domain.com
```

**What it provides:**
- Tests all admin users found in the database
- Categorizes admins by access level (full/partial/none)
- Identifies which admins lack directory permissions
- Batch reporting and statistics

**Output:** Comprehensive batch results saved to `batch_admin_scope_test_results.json`

## Required Google API Scopes

For full directory access, these scopes must be authorized in Google Workspace Admin Console:

### Required Directory Scopes:
```
https://www.googleapis.com/auth/admin.directory.user.readonly
https://www.googleapis.com/auth/admin.directory.group.readonly
https://www.googleapis.com/auth/admin.directory.orgunit.readonly
```

### Required Drive Scopes:
```
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/drive.file
```

## How to Authorize Scopes

1. **Go to Google Workspace Admin Console**
   - Navigate to: `https://admin.google.com`
   - Sign in with super admin account

2. **Navigate to API Controls**
   - Go to: Security → API controls → Domain-wide delegation

3. **Find Your Service Account**
   - Look for your service account by Client ID
   - The Client ID can be found in your service account JSON file

4. **Add Required Scopes**
   - Click on the service account
   - Add each required scope URL
   - Save changes

5. **Wait for Propagation**
   - Scope changes may take 5-10 minutes to propagate
   - You may need to re-authenticate affected users

## Prerequisites

1. **Service Account Setup:**
   - Valid service account JSON file
   - `GOOGLE_APPLICATION_CREDENTIALS` environment variable set
   - Service account authorized in Google Workspace Admin Console

2. **Database Access:**
   - Valid Supabase connection
   - Admin users exist in `user_profiles` table

3. **Environment Variables:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   export SUPABASE_URL=your_supabase_url
   export SUPABASE_ANON_KEY=your_supabase_key
   export TEST_ADMIN_EMAIL=admin@domain.com  # Optional, for single-user testing
   ```

## Troubleshooting

### Common Issues:

1. **"DWD service not available"**
   - Check `GOOGLE_APPLICATION_CREDENTIALS` path
   - Verify service account JSON file exists and is valid

2. **"Directory API access denied"**
   - Required scopes not authorized in Admin Console
   - Check Domain-wide delegation settings

3. **"Admin user not found in database"**
   - User doesn't exist in `user_profiles` table
   - Check Supabase connection

4. **"Empty response from directory API"**
   - User may not have directory permissions
   - Check user's role in Google Workspace

### Debug Mode:
Run scripts with verbose output to see detailed error messages and API responses.

## Output Files

All test scripts generate JSON output files with detailed results:

- `admin_directory_scopes_test_results.json` - Comprehensive single-user test results
- `dwd_scope_test_results.json` - Scope-specific authorization results
- `batch_admin_scope_test_results.json` - Multi-user batch test results

## Security Notes

- These scripts only test read permissions; they don't modify any data
- Service account credentials should be kept secure
- Test results may contain sensitive information; handle output files appropriately
- Directory access should be limited to authorized administrators only

## Support

If you encounter issues:

1. Check the error messages in test output
2. Verify Google Workspace Admin Console settings
3. Confirm service account configuration
4. Check database connectivity
5. Review environment variables

For additional help, check the main application logs and Google API documentation.


















