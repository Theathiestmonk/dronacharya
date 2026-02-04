#!/usr/bin/env python3
"""
Diagnostic script for DWD/GCDR domain issues
Run this on both localhost and production to compare
"""

import os
import json
import sys
from datetime import datetime

def check_environment():
    """Check all relevant environment variables"""
    print("🔍 ENVIRONMENT VARIABLES CHECK")
    print("="*50)

    env_vars = [
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GOOGLE_WORKSPACE_DOMAIN',
        'GOOGLE_SERVICE_ACCOUNT_JSON',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
        'NEXT_PUBLIC_SUPABASE_URL',
        'NEXT_PUBLIC_SUPABASE_ANON_KEY'
    ]

    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'SECRET' in var or 'JSON' in var:
                # Mask sensitive values
                masked = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else "***SET***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")

def check_service_account_file():
    """Check if service account file exists and is valid"""
    print("\n🔍 SERVICE ACCOUNT FILE CHECK")
    print("="*50)

    # Check file-based credentials
    file_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-key.json')
    print(f"Checking file: {file_path}")

    if os.path.exists(file_path):
        print("✅ File exists")
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                print(f"❌ Missing fields: {missing_fields}")
            else:
                print("✅ All required fields present")
                print(f"   Project ID: {data.get('project_id')}")
                print(f"   Client Email: {data.get('client_email')}")
                print(f"   Client ID: {data.get('client_id', 'Not found')[:20]}...")
        except Exception as e:
            print(f"❌ Error reading file: {e}")
    else:
        print("❌ File does not exist")

    # Check JSON environment variable
    json_content = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if json_content:
        print("✅ GOOGLE_SERVICE_ACCOUNT_JSON is set")
        try:
            data = json.loads(json_content)
            print(f"   Project ID from JSON: {data.get('project_id')}")
            print(f"   Client Email from JSON: {data.get('client_email')}")
        except Exception as e:
            print(f"❌ Error parsing JSON: {e}")
    else:
        print("❌ GOOGLE_SERVICE_ACCOUNT_JSON not set")

def check_domain_config():
    """Check domain configuration"""
    print("\n🔍 DOMAIN CONFIGURATION CHECK")
    print("="*50)

    domain = os.getenv('GOOGLE_WORKSPACE_DOMAIN', 'NOT SET')
    print(f"Workspace Domain: {domain}")

    if domain != 'NOT SET':
        if domain == 'learners.prakriti.org.in':
            print("✅ Domain matches expected value")
        else:
            print(f"⚠️  Domain is '{domain}', expected 'learners.prakriti.org.in'")
    else:
        print("❌ Domain not configured")

def check_dwd_service():
    """Test DWD service initialization"""
    print("\n🔍 DWD SERVICE INITIALIZATION CHECK")
    print("="*50)

    try:
        from app.services.google_dwd_service import get_dwd_service
        dwd_service = get_dwd_service()

        if dwd_service:
            print("✅ DWD service initialized successfully")
            print(f"   Available: {dwd_service.is_available()}")
            print(f"   Workspace Domain: {dwd_service.workspace_domain}")
            print(f"   Service Account Path: {dwd_service.service_account_path}")

            # Test credentials loading
            if hasattr(dwd_service, '_base_credentials') and dwd_service._base_credentials:
                print("✅ Base credentials loaded")
            else:
                print("❌ Base credentials not loaded")
        else:
            print("❌ DWD service initialization failed")

    except Exception as e:
        print(f"❌ DWD service error: {e}")
        import traceback
        traceback.print_exc()

def check_supabase_connection():
    """Test Supabase connection"""
    print("\n🔍 SUPABASE CONNECTION CHECK")
    print("="*50)

    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()

        if supabase:
            print("✅ Supabase client created")
            # Test a simple query
            try:
                result = supabase.table('user_profiles').select('count').limit(1).execute()
                print("✅ Database connection successful")
            except Exception as e:
                print(f"❌ Database query failed: {e}")
        else:
            print("❌ Supabase client creation failed")

    except Exception as e:
        print(f"❌ Supabase error: {e}")

def main():
    """Run all diagnostic checks"""
    print("🚀 DWD/GCDR DIAGNOSTIC SCRIPT")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Environment: {'Production' if os.getenv('RENDER') else 'Local Development'}")
    print()

    check_environment()
    check_service_account_file()
    check_domain_config()
    check_supabase_connection()
    check_dwd_service()

    print("\n" + "="*60)
    print("🔧 TROUBLESHOOTING STEPS:")
    print("="*60)
    print("1. Ensure GOOGLE_SERVICE_ACCOUNT_JSON is set in Render environment")
    print("2. Verify service account is authorized in Google Workspace Admin Console")
    print("3. Check that Client ID matches exactly in Admin Console")
    print("4. Confirm all required OAuth scopes are enabled")
    print("5. Wait 15-30 minutes after Admin Console changes")
    print("="*60)

if __name__ == "__main__":
    main()


