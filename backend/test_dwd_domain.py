#!/usr/bin/env python3
"""
Simple test to check DWD functionality
Run this on both localhost and production
"""

import os
import requests
import json
from datetime import datetime

def test_dwd_client_id():
    """Test the DWD client ID endpoint"""
    print("Testing DWD Client ID Endpoint...")
    print("-" * 40)

    backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')

    try:
        response = requests.get(f"{backend_url}/api/admin/dwd/client-id", timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Endpoint accessible")
            if 'client_id' in data:
                print(f"Client ID: {data.get('client_id')}")
                print(f"Service Account: {data.get('service_account_email', 'N/A')}")
                print(f"Workspace Domain: {data.get('workspace_domain', 'N/A')}")
                print("\n📋 Authorization Instructions:")
                if 'instructions' in data:
                    inst = data['instructions']
                    print(f"  1. {inst.get('step_1', '')}")
                    print(f"  2. {inst.get('step_2', '')}")
                    print(f"  3. {inst.get('step_3', '')}")
                    if 'scopes' in inst:
                        print(f"  4. {inst.get('step_4', '')}")
                        for scope in inst.get('scopes', []):
                            print(f"     • {scope}")
            else:
                print(f"Error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_dwd_status():
    """Test the DWD status endpoint"""
    print("\nTesting DWD Status Endpoint...")
    print("-" * 40)

    # Get backend URL
    backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')

    try:
        response = requests.get(f"{backend_url}/api/admin/dwd/status", timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Endpoint accessible")
            print(f"Available: {data.get('available', 'N/A')}")
            print(f"Workspace Domain: {data.get('workspace_domain', 'N/A')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_dwd_diagnose():
    """Test the comprehensive DWD diagnostic endpoint"""
    print("\nTesting DWD Diagnostic Endpoint...")
    print("-" * 40)

    backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')

    try:
        response = requests.get(f"{backend_url}/api/admin/dwd/diagnose", timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Diagnostic endpoint accessible")
            print(f"Environment: {data.get('environment', 'N/A')}")
            print(f"Timestamp: {data.get('timestamp', 'N/A')}")

            checks = data.get('checks', {})

            # Environment variables
            env_vars = checks.get('environment_variables', {})
            print(f"\nEnvironment Variables:")
            for var, value in env_vars.items():
                status = "✅" if value != "NOT SET" else "❌"
                print(f"  {status} {var}: {value}")

            # Service account
            sa_file = checks.get('service_account_file', {})
            print(f"\nService Account File:")
            print(f"  Path: {sa_file.get('path', 'N/A')}")
            print(f"  Exists: {'✅' if sa_file.get('exists') else '❌'}")
            if sa_file.get('project_id'):
                print(f"  Project ID: {sa_file.get('project_id')}")

            # Domain config
            domain = checks.get('domain_config', {})
            matches = "✅" if domain.get('matches') else "❌"
            print(f"\nDomain Config:")
            print(f"  Configured: {domain.get('configured_domain')}")
            print(f"  Expected: {domain.get('expected_domain')}")
            print(f"  Matches: {matches}")

            # DWD service
            dwd = checks.get('dwd_service', {})
            initialized = "✅" if dwd.get('initialized') else "❌"
            available = "✅" if dwd.get('available') else "❌"
            print(f"\nDWD Service:")
            print(f"  Initialized: {initialized}")
            print(f"  Available: {available}")
            if dwd.get('error'):
                print(f"  Error: {dwd.get('error')}")

            # Supabase
            sb = checks.get('supabase', {})
            client_created = "✅" if sb.get('client_created') else "❌"
            connection_ok = "✅" if sb.get('connection_successful') else "❌"
            print(f"\nSupabase:")
            print(f"  Client Created: {client_created}")
            print(f"  Connection OK: {connection_ok}")

        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}...")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def main():
    """Run all tests"""
    print("🚀 DWD Domain Test Script")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Environment: {'Production' if os.getenv('RENDER') else 'Local Development'}")
    print(f"🔗 Backend URL: {os.getenv('BACKEND_URL', 'http://localhost:8000')}")
    print()

    test_dwd_client_id()
    test_dwd_status()
    test_dwd_diagnose()

    print("\n" + "="*60)
    print("📋 QUICK TROUBLESHOOTING CHECKLIST:")
    print("="*60)
    print("□ Get Client ID from /api/admin/dwd/client-id endpoint")
    print("□ Environment variables set in Render dashboard?")
    print("□ GOOGLE_SERVICE_ACCOUNT_JSON contains valid JSON?")
    print("□ Service account authorized in Google Workspace Admin Console?")
    print("□ Client ID matches EXACTLY in Admin Console (no spaces, no typos)?")
    print("□ All 8 required OAuth scopes added (one per line)?")
    print("□ Domain set to 'learners.prakriti.org.in'?")
    print("□ Service restarted after environment variable changes?")
    print("□ Waited 15-30 minutes after Admin Console changes?")
    print("□ Check production logs for [DWD] messages?")
    print("="*60)
    print("📄 See: backend/DWD_PRODUCTION_SETUP.md for detailed instructions")
    print("="*60)

if __name__ == "__main__":
    main()

