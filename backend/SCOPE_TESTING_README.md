# Google Workspace DWD Scope Testing Scripts

This collection of scripts helps you test and verify that your Domain-Wide Delegation (DWD) scopes are properly authorized in your Google Workspace Admin Console.

## 📋 Available Test Scripts

### 🎯 Quick Tests (Recommended for beginners)

#### `run_all_scope_tests.py` - **MASTER TEST SCRIPT**
- **Purpose**: Runs all scope tests in one command
- **What it tests**: Drive, Directory, Classroom, Calendar scopes
- **Output**: Comprehensive report with action items
- **Usage**: `python run_all_scope_tests.py`

#### `quick_drive_scope_test.py` - Drive Scope Only
- **Purpose**: Test only the drive.readonly scope
- **What it tests**: Google Drive file access
- **Usage**: `python quick_drive_scope_test.py`

### 🔧 Individual Scope Tests

#### `test_directory_scope.py` - Directory Access
- **Tests**: `admin.directory.user.readonly`
- **Purpose**: User directory and organization data access
- **Usage**: `python test_directory_scope.py`

#### `test_classroom_scope.py` - Classroom Access
- **Tests**: `classroom.courses.readonly` and `classroom.coursework.readonly`
- **Purpose**: Classroom courses and assignments access
- **Usage**: `python test_classroom_scope.py`

#### `test_calendar_scope.py` - Calendar Access
- **Tests**: `calendar.readonly`
- **Purpose**: Calendar events and schedules access
- **Usage**: `python test_calendar_scope.py`

### 🧪 Advanced Test

#### `test_all_dwd_scopes.py` - Comprehensive Scope Test
- **Purpose**: Detailed testing of all scopes with full error reporting
- **Output**: Technical details for debugging
- **Usage**: `python test_all_dwd_scopes.py`

## 🚀 Quick Start

1. **Make sure your `.env` is configured**:
   ```bash
   # Check backend/.env contains:
   GOOGLE_SERVICE_ACCOUNT_JSON=your_service_account_json_here
   ```

2. **Run the master test**:
   ```bash
   python run_all_scope_tests.py
   ```

3. **Check results and add missing scopes** in Google Workspace Admin Console:
   - Go to: `https://admin.google.com/ac/owl/domainwidedelegation`
   - Find your service account
   - Add the required scopes

## 📊 Understanding Test Results

### ✅ AUTHORIZED (Green/Success)
```
✅ Drive scope AUTHORIZED
   Found 5 accessible files
   User: dummy@learners.prakriti.org.in
```

### ❌ NOT AUTHORIZED (Red/Failure)
```
❌ Drive scope NOT AUTHORIZED
   Solution: Add 'https://www.googleapis.com/auth/drive.readonly'
   to Google Workspace Admin Console → Security → API controls → Domain-wide delegation
```

### ⚠️ UNKNOWN/ERROR (Yellow/Warning)
```
⚠️ Unexpected error: connection timeout
```

## 🔧 Required Scopes for Your Use Case

### For Exam File Access (Drive)
```
https://www.googleapis.com/auth/drive.readonly
```

### For User Directory Access
```
https://www.googleapis.com/auth/admin.directory.user.readonly
```

### For Classroom Data (Courses & Assignments)
```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.coursework.readonly
```

### For Calendar Events
```
https://www.googleapis.com/auth/calendar.readonly
```

## 🐛 Troubleshooting

### "No GOOGLE_SERVICE_ACCOUNT_JSON in .env"
- Check your `backend/.env` file
- Make sure the service account JSON is properly formatted
- Ensure the environment variable is loaded

### "Failed to create delegated credentials"
- Verify your service account is set up for DWD
- Check that the service account email is correct
- Ensure DWD is enabled in Google Workspace

### "access_denied" errors
- The scope is not authorized in Admin Console
- Add the missing scope to your service account's DWD configuration
- Wait 5-10 minutes for changes to propagate

### "Invalid JSON" errors
- Check your service account JSON format
- Ensure it's properly escaped in the .env file
- Try re-downloading the service account key

## 📞 Support

If you encounter issues:

1. **Run the comprehensive test**: `python test_all_dwd_scopes.py`
2. **Check the detailed error messages**
3. **Verify your Admin Console configuration**
4. **Ensure your service account has DWD enabled**

## 🎯 Use Case Examples

### Exam Chatbot Integration
- ✅ **Drive scope**: Access exam files and schedules
- ✅ **Directory scope**: Get student information
- ✅ **Classroom scope**: Access course assignments
- ✅ **Calendar scope**: Get exam schedules and events

### File Access Pattern
1. Teacher shares exam files with `dummy@learners.prakriti.org.in`
2. Chatbot searches for files using Drive API
3. Content is extracted and made available for queries
4. Real-time updates when new files are shared

## 🔄 Next Steps After Authorization

Once all scopes are authorized:

1. **Test with actual exam files**:
   ```bash
   python test_drive_access.py
   ```

2. **Integrate with your chatbot**:
   - Update chatbot agent to use Drive service
   - Test exam queries
   - Monitor for authorization issues

3. **Set up file sharing workflow**:
   - Teachers share files with dummy account
   - Files are automatically accessible
   - No manual synchronization needed

---

**Happy testing!** 🎉 If you have questions, run the tests and share the output.
