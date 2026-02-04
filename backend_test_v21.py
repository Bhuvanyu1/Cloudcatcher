#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class CloudWatcherV21Tester:
    def __init__(self, base_url="https://instance-scout.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.auth_token = None

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, data: Dict = None, params: Dict = None, auth_required: bool = False) -> tuple:
        """Run a single API test"""
        url = f"{self.api_base}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Add auth header if required and token available
        if auth_required and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=60)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=60)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            details = f"Status: {response.status_code}"
            if not success:
                details += f", Expected: {expected_status}, Response: {response.text[:200]}"

            self.log_test(name, success, details)
            return success, response_data

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_v21_features(self):
        """Test all Cloud Watcher v2.1 specific features"""
        print("🚀 Testing Cloud Watcher v2.1 Features...")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)

        # 1. Backend health check returns version 2.0.0
        print("\n1️⃣ Testing health check version...")
        success, response = self.run_test("Health Check", "GET", "health", 200)
        if success:
            version = response.get("version")
            if version == "2.0.0":
                print(f"   ✅ Version check passed: {version}")
            else:
                print(f"   ❌ Version mismatch: got {version}, expected 2.0.0")
                self.log_test("Version Check", False, f"Expected 2.0.0, got {version}")

        # 2. Login with admin@cloudwatcher.com / Admin123! works
        print("\n2️⃣ Testing demo login credentials...")
        login_data = {
            "email": "admin@cloudwatcher.com",
            "password": "Admin123!"
        }
        
        success, response = self.run_test("Demo Login", "POST", "auth/login", 200, login_data)
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            user = response.get('user', {})
            print(f"   👤 Logged in as: {user.get('name', 'Unknown')} ({user.get('role', 'Unknown')})")
        else:
            print("   ❌ Login failed - cannot test authenticated endpoints")
            return

        # 3. GET /api/scheduler/jobs returns scheduled sync job
        print("\n3️⃣ Testing scheduler jobs endpoint...")
        success, response = self.run_test("Scheduler Jobs", "GET", "scheduler/jobs", 200, auth_required=True)
        if success:
            jobs = response if isinstance(response, list) else []
            sync_job = next((job for job in jobs if 'sync' in job.get('name', '').lower()), None)
            if sync_job:
                print(f"   📅 Found sync job: {sync_job.get('name')}")
                print(f"   📅 Next run: {sync_job.get('next_run', 'N/A')}")
                print(f"   📅 Trigger: {sync_job.get('trigger', 'N/A')}")
            else:
                print(f"   ⚠️  No sync job found in {len(jobs)} jobs")
                if jobs:
                    print(f"   Available jobs: {[job.get('name') for job in jobs]}")

        # 4. Sync endpoint POST /api/sync attempts real cloud API calls
        print("\n4️⃣ Testing sync endpoint with real cloud APIs...")
        success, response = self.run_test("Sync Real APIs", "POST", "sync", 200)
        if success:
            accounts_synced = response.get('accounts_synced', 0)
            instances_found = response.get('instances_found', 0)
            errors = response.get('errors', [])
            
            print(f"   📊 Synced {accounts_synced} accounts")
            print(f"   📊 Found {instances_found} instances")
            if errors:
                print(f"   ⚠️  Sync errors (expected with invalid credentials): {len(errors)}")
                for i, error in enumerate(errors[:3]):  # Show first 3 errors
                    print(f"      {i+1}. {error}")

        # 5. Cloud accounts with invalid credentials show error status after sync
        print("\n5️⃣ Testing cloud account error status...")
        success, accounts = self.run_test("Cloud Accounts Status", "GET", "cloud-accounts", 200)
        if success:
            error_accounts = [acc for acc in accounts if acc.get('status') == 'error']
            connected_accounts = [acc for acc in accounts if acc.get('status') == 'connected']
            
            print(f"   🔍 Total accounts: {len(accounts)}")
            print(f"   🔍 Error status: {len(error_accounts)}")
            print(f"   🔍 Connected status: {len(connected_accounts)}")
            
            if error_accounts:
                for i, acc in enumerate(error_accounts[:2]):  # Show first 2 error accounts
                    error_msg = acc.get('last_error', 'No error message')
                    print(f"      {i+1}. {acc.get('account_name', 'Unknown')}: {error_msg[:100]}")
                    
                    # Check if error is credential-related
                    if any(keyword in error_msg.lower() for keyword in ['credential', 'auth', 'access', 'key', 'token', 'permission']):
                        print(f"         ✅ Credential-related error detected")
                    else:
                        print(f"         ⚠️  Error may not be credential-related")

        # 6. Email service endpoint POST /api/email/test (requires auth)
        print("\n6️⃣ Testing email service endpoint...")
        if self.auth_token:
            email_data = {
                "email": "test@example.com"
            }
            
            success, response = self.run_test("Email Service", "POST", "email/test", 200, email_data, auth_required=True)
            if success:
                if response.get('mock'):
                    print(f"   📧 Email service (mocked): {response.get('message', 'No message')}")
                    print(f"   📧 RESEND_API_KEY not configured (expected for demo)")
                else:
                    print(f"   📧 Email service active: {response.get('message', 'No message')}")
        else:
            print("   ❌ Cannot test email service - no auth token")

        # 7. Dashboard loads after login (test backend API)
        print("\n7️⃣ Testing dashboard backend API...")
        success, response = self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)
        if success:
            stats = response
            print(f"   📈 Total instances: {stats.get('total_instances', 0)}")
            print(f"   📈 Total accounts: {stats.get('total_accounts', 0)}")
            print(f"   📈 Open recommendations: {stats.get('open_recommendations', 0)}")
            print(f"   📈 FinOps recommendations: {stats.get('finops_recommendations', 0)}")
            print(f"   📈 SecOps recommendations: {stats.get('secops_recommendations', 0)}")
            print(f"   📈 Last sync: {stats.get('last_sync', 'Never')}")

        # 8. Settings page shows scheduler status (test backend API)
        print("\n8️⃣ Testing settings/scheduler status...")
        # Re-test scheduler jobs to verify settings page data
        success, response = self.run_test("Settings Scheduler Status", "GET", "scheduler/jobs", 200, auth_required=True)
        if success:
            jobs = response if isinstance(response, list) else []
            print(f"   ⚙️  Scheduler status: {len(jobs)} jobs configured")
            for job in jobs:
                print(f"      - {job.get('name', 'Unknown')}: {job.get('trigger', 'Unknown trigger')}")

        # Print final summary
        print("\n" + "=" * 60)
        print(f"📊 v2.1 Feature Test Results: {self.tests_passed}/{self.tests_run} passed ({(self.tests_passed/self.tests_run*100):.1f}%)")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All v2.1 features working correctly!")
            return 0
        else:
            print("❌ Some v2.1 features have issues!")
            failed_tests = [t for t in self.test_results if not t['success']]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
            return 1

def main():
    tester = CloudWatcherV21Tester()
    return tester.test_v21_features()

if __name__ == "__main__":
    sys.exit(main())