# Domain-Wide Google Classroom Data Sync

This implementation adds comprehensive domain-wide Google Classroom data synchronization capabilities to the Prakriti School chatbot system.

## 🚀 What It Does

- **Fetches ALL classroom data** from the entire Google Workspace domain (not just individual users)
- **Stores comprehensive data** including courses, teachers, students, coursework, submissions, and announcements
- **Provides admin dashboard** with domain-wide sync controls
- **Creates analytics views** for domain-wide classroom insights

## 🏗️ Architecture

### Database Tables Enhanced
All existing Google Classroom tables now support domain-wide data with an `is_domain_wide` flag:

- `google_classroom_courses` - All courses in the domain
- `google_classroom_teachers` - All teachers across courses
- `google_classroom_students` - All students across courses
- `google_classroom_coursework` - All assignments and materials
- `google_classroom_submissions` - All student submissions
- `google_classroom_announcements` - All course announcements

### API Endpoints Added
- `POST /api/admin/sync-domain-classroom` - Sync all classroom data from domain
- `GET /api/admin/data/domain-classroom` - Get domain-wide classroom analytics

### Frontend Features
- **Domain Sync Button** - Purple button to sync entire domain data
- **Analytics Dashboard** - View comprehensive classroom statistics
- **Progress Tracking** - Real-time sync progress with detailed stats

## 🧪 Testing

### Backend Tests
```bash
cd backend
python test_domain_classroom.py
```

This tests:
- ✅ Supabase database connection
- ✅ DWD service initialization
- ✅ Database schema integrity
- ✅ Google Classroom API access
- ✅ Domain sync API functionality

### Frontend Tests
```bash
cd frontend
node test_domain_sync.js
```

This tests:
- ✅ Backend API connectivity
- ✅ DWD service status
- ✅ Domain data endpoints
- ✅ Sync functionality (optional with `--run-sync`)

### Running Actual Sync Test
```bash
# Test without actually syncing data
node test_domain_sync.js

# Test with actual domain sync (will sync real data!)
node test_domain_sync.js --run-sync
```

## 🔧 Setup Requirements

### Environment Variables
```bash
# Required for DWD
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_WORKSPACE_DOMAIN=learners.prakriti.org.in

# Backend API
BACKEND_URL=http://localhost:8000

# Test configuration
TEST_ADMIN_EMAIL=admin@learners.prakriti.org.in
```

### Database Migration
Run the schema updates:
```sql
-- Execute the contents of backend/create_domain_wide_schema.sql
-- This adds is_domain_wide columns and creates analytics views
```

### Google Workspace Setup
1. **Service Account**: Create service account with Domain-Wide Delegation
2. **Admin Console**: Authorize service account with required scopes:
   - `https://www.googleapis.com/auth/classroom.courses.readonly`
   - `https://www.googleapis.com/auth/classroom.rosters.readonly`
   - `https://www.googleapis.com/auth/classroom.announcements.readonly`
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/calendar.events.readonly`
3. **Domain**: Set `GOOGLE_WORKSPACE_DOMAIN=learners.prakriti.org.in`

## 🎯 Usage

### Admin Dashboard
1. Go to Admin Dashboard → Classroom tab
2. Click **"Domain Sync"** button (purple button)
3. Confirm the domain-wide sync operation
4. Wait for sync to complete (may take several minutes)
5. View comprehensive analytics and data

### API Usage
```bash
# Sync all domain data
curl -X POST http://localhost:8000/api/admin/sync-domain-classroom

# Get domain analytics
curl "http://localhost:8000/api/admin/data/domain-classroom?email=admin@domain.com"
```

## 📊 Data Structure

### Sync Statistics
The domain sync returns detailed statistics:
```json
{
  "success": true,
  "message": "Synced Google Classroom data from entire domain",
  "stats": {
    "courses": {"created": 25, "updated": 5},
    "teachers": {"created": 15, "updated": 3},
    "students": {"created": 150, "updated": 20},
    "coursework": {"created": 45, "updated": 10},
    "submissions": {"created": 200, "updated": 50},
    "announcements": {"created": 30, "updated": 8}
  },
  "summary": {
    "courses": 30,
    "teachers": 18,
    "students": 170,
    "coursework": 55,
    "submissions": 250,
    "announcements": 38
  }
}
```

### Analytics View
The `domain_classroom_analytics` view provides:
- Course information with enrollment counts
- Teacher and student statistics
- Content and submission metrics
- Last sync timestamps

## 🔒 Security & Permissions

- **Admin Only**: Domain sync requires admin privileges
- **Domain Scoped**: Only syncs data from configured workspace domain
- **Read-Only**: All operations are read-only from Google Classroom
- **Audit Trail**: All sync operations are logged with timestamps

## 🚨 Important Notes

1. **Domain Sync Impact**: This syncs ALL classroom data from your entire Google Workspace domain
2. **Data Volume**: Large domains may have thousands of courses - sync may take time
3. **Rate Limits**: Google API has rate limits - large syncs may need to be batched
4. **Storage**: Ensure adequate database storage for comprehensive domain data
5. **Performance**: Domain analytics queries may be slower with large datasets

## 🐛 Troubleshooting

### Common Issues
1. **DWD Not Configured**: Check `GOOGLE_APPLICATION_CREDENTIALS` path
2. **Domain Mismatch**: Verify `GOOGLE_WORKSPACE_DOMAIN` setting
3. **Permissions**: Ensure service account has all required scopes
4. **API Quotas**: Check Google Cloud Console for Classroom API quotas

### Test Failures
- Run individual test components to isolate issues
- Check backend logs for detailed error messages
- Verify service account JSON file format and permissions

## 🎉 Success Criteria

✅ **All Tests Pass**: Backend and frontend tests complete successfully
✅ **Domain Data Available**: Can retrieve comprehensive classroom data
✅ **Admin UI Works**: Domain sync button functions correctly
✅ **Performance Acceptable**: Sync and queries complete in reasonable time
✅ **Data Integrity**: No duplicate or missing records in database

---

**Ready to sync your entire Google Workspace domain classroom data! 🎓**




