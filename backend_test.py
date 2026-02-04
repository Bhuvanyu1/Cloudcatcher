#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class CloudWatcherAPITester:
    def __init__(self, base_url="https://instance-scout.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_accounts = []
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
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
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

    def test_health_check(self):
        """Test health endpoint - should return version 2.0.0"""
        success, response = self.run_test("Health Check", "GET", "health", 200)
        if success:
            version = response.get("version")
            if version == "2.0.0":
                print(f"   ✅ Version check passed: {version}")
            else:
                print(f"   ⚠️  Version mismatch: got {version}, expected 2.0.0")
                success = False
                self.log_test("Health Check Version", False, f"Expected version 2.0.0, got {version}")
        return success, response

    def test_login_demo_credentials(self):
        """Test login with demo credentials: admin@cloudwatcher.com / Admin123!"""
        login_data = {
            "email": "admin@cloudwatcher.com",
            "password": "Admin123!"
        }
        
        success, response = self.run_test("Login Demo Credentials", "POST", "auth/login", 200, login_data)
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            user = response.get('user', {})
            print(f"   👤 Logged in as: {user.get('name', 'Unknown')} ({user.get('role', 'Unknown')})")
        return success, response

    def test_scheduler_jobs(self):
        """Test GET /api/scheduler/jobs returns scheduled sync job (requires auth)"""
        success, response = self.run_test("Get Scheduled Jobs", "GET", "scheduler/jobs", 200, auth_required=True)
        if success:
            jobs = response if isinstance(response, list) else []
            sync_job = next((job for job in jobs if 'sync' in job.get('name', '').lower()), None)
            if sync_job:
                print(f"   📅 Found sync job: {sync_job.get('name')} (next run: {sync_job.get('next_run', 'N/A')})")
            else:
                print(f"   ⚠️  No sync job found in {len(jobs)} jobs")
        return success, response

    def test_sync_real_cloud_apis(self):
        """Test sync endpoint attempts real cloud API calls"""
        success, response = self.run_test("Sync All Accounts (Real APIs)", "POST", "sync", 200)
        if success:
            accounts_synced = response.get('accounts_synced', 0)
            instances_found = response.get('instances_found', 0)
            errors = response.get('errors', [])
            
            print(f"   📊 Synced {accounts_synced} accounts, found {instances_found} instances")
            if errors:
                print(f"   ⚠️  Sync errors (expected with invalid credentials): {len(errors)} errors")
                for error in errors[:3]:  # Show first 3 errors
                    print(f"      - {error}")
            
            # Check if we have any accounts to test credential errors
            self.test_cloud_accounts_credential_errors()
        return success, response

    def test_cloud_accounts_credential_errors(self):
        """Test that cloud accounts with invalid credentials show error status after sync"""
        success, accounts = self.run_test("List Cloud Accounts for Error Check", "GET", "cloud-accounts", 200)
        if success:
            error_accounts = [acc for acc in accounts if acc.get('status') == 'error']
            connected_accounts = [acc for acc in accounts if acc.get('status') == 'connected']
            
            print(f"   🔍 Account status check: {len(error_accounts)} error, {len(connected_accounts)} connected")
            
            if error_accounts:
                for acc in error_accounts[:2]:  # Show first 2 error accounts
                    error_msg = acc.get('last_error', 'No error message')
                    print(f"      - {acc.get('account_name', 'Unknown')}: {error_msg[:100]}")
                    
                    # Check if error is credential-related
                    if any(keyword in error_msg.lower() for keyword in ['credential', 'auth', 'access', 'key', 'token']):
                        self.log_test("Credential Error Detection", True, f"Found credential error: {error_msg[:50]}")
                    else:
                        self.log_test("Credential Error Detection", False, f"Error not credential-related: {error_msg[:50]}")
        
        return success, accounts

    def test_email_service(self):
        """Test email service endpoint POST /api/email/test (requires auth)"""
        if not self.auth_token:
            self.log_test("Email Service Test", False, "No auth token available")
            return False, {}
        
        email_data = {
            "email": "test@example.com"
        }
        
        success, response = self.run_test("Email Service Test", "POST", "email/test", 200, email_data, auth_required=True)
        if success:
            if response.get('mock'):
                print(f"   📧 Email service test (mocked): {response.get('message', 'No message')}")
            else:
                print(f"   📧 Email service test: {response.get('message', 'No message')}")
        return success, response

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        return self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)

    def test_create_cloud_account(self, provider: str = "aws") -> str:
        """Test creating a cloud account"""
        account_data = {
            "provider": provider,
            "account_name": f"Test {provider.upper()} Account",
            "credentials": {
                "access_key_id": "test_key_123",
                "secret_access_key": "test_secret_456",
                "region": "us-east-1"
            }
        }
        
        success, response = self.run_test(
            f"Create {provider.upper()} Account", 
            "POST", 
            "cloud-accounts", 
            200, 
            account_data
        )
        
        if success and 'id' in response:
            self.created_accounts.append(response['id'])
            return response['id']
        return None

    def test_list_cloud_accounts(self):
        """Test listing cloud accounts"""
        return self.run_test("List Cloud Accounts", "GET", "cloud-accounts", 200)

    def test_get_cloud_account(self, account_id: str):
        """Test getting specific cloud account"""
        return self.run_test(
            "Get Cloud Account", 
            "GET", 
            f"cloud-accounts/{account_id}", 
            200
        )

    def test_sync_all_accounts(self):
        """Test syncing all accounts"""
        success, response = self.run_test("Sync All Accounts", "POST", "sync", 200)
        if success:
            print(f"   📊 Synced {response.get('accounts_synced', 0)} accounts, found {response.get('instances_found', 0)} instances")
        return success, response

    def test_sync_single_account(self, account_id: str):
        """Test syncing single account"""
        return self.run_test(
            "Sync Single Account", 
            "POST", 
            f"sync/{account_id}", 
            200
        )

    def test_list_instances(self):
        """Test listing instances"""
        return self.run_test("List Instances", "GET", "instances", 200)

    def test_list_instances_with_filters(self):
        """Test listing instances with filters"""
        params = {"provider": "aws", "state": "running", "limit": 10}
        return self.run_test(
            "List Instances (Filtered)", 
            "GET", 
            "instances", 
            200, 
            params=params
        )

    def test_list_recommendations(self):
        """Test listing recommendations"""
        return self.run_test("List Recommendations", "GET", "recommendations", 200)

    def test_list_recommendations_by_category(self):
        """Test listing recommendations by category"""
        # Test FinOps recommendations
        params = {"category": "finops", "status": "open"}
        success1, _ = self.run_test(
            "List FinOps Recommendations", 
            "GET", 
            "recommendations", 
            200, 
            params=params
        )
        
        # Test SecOps recommendations
        params = {"category": "secops", "status": "open"}
        success2, _ = self.run_test(
            "List SecOps Recommendations", 
            "GET", 
            "recommendations", 
            200, 
            params=params
        )
        
        return success1 and success2

    def test_run_recommendations(self):
        """Test running recommendation analysis"""
        success, response = self.run_test("Run Recommendations", "POST", "recommendations/run", 200)
        if success:
            print(f"   🔍 Generated {response.get('recommendations_generated', 0)} recommendations")
        return success, response

    def test_update_recommendation_status(self, rec_id: str):
        """Test updating recommendation status"""
        return self.run_test(
            "Update Recommendation Status", 
            "PATCH", 
            f"recommendations/{rec_id}?status=dismissed", 
            200
        )

    def test_delete_cloud_account(self, account_id: str):
        """Test deleting cloud account"""
        return self.run_test(
            "Delete Cloud Account", 
            "DELETE", 
            f"cloud-accounts/{account_id}", 
            200
        )

    def run_comprehensive_test(self):
        """Run comprehensive API test suite for Cloud Watcher v2.1"""
        print("🚀 Starting Cloud Watcher v2.1 API Tests...")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)

        # 1. Health Check - should return version 2.0.0
        self.test_health_check()

        # 2. Login with demo credentials
        self.test_login_demo_credentials()

        # 3. Test scheduler jobs (requires auth)
        self.test_scheduler_jobs()

        # 4. Dashboard Stats (backend API for dashboard)
        self.test_dashboard_stats()

        # 5. Sync endpoint - attempts real cloud API calls
        self.test_sync_real_cloud_apis()

        # 6. Email service test (requires auth)
        self.test_email_service()

        # 7. Additional comprehensive tests
        print("\n📋 Running additional comprehensive tests...")
        
        # Create test accounts for different providers
        aws_account_id = self.test_create_cloud_account("aws")
        azure_account_id = self.test_create_cloud_account("azure")
        gcp_account_id = self.test_create_cloud_account("gcp")

        # List accounts
        self.test_list_cloud_accounts()

        # Get specific account
        if aws_account_id:
            self.test_get_cloud_account(aws_account_id)

        # Sync single account
        if aws_account_id:
            self.test_sync_single_account(aws_account_id)

        # Test instances endpoints
        self.test_list_instances()
        self.test_list_instances_with_filters()

        # Test recommendations
        self.test_list_recommendations()
        self.test_run_recommendations()
        self.test_list_recommendations_by_category()

        # Test recommendation status update (if we have recommendations)
        success, recs = self.run_test("Get Recommendations for Update Test", "GET", "recommendations", 200, params={"limit": 1})
        if success and recs and len(recs) > 0:
            rec_id = recs[0].get('id')
            if rec_id:
                self.test_update_recommendation_status(rec_id)

        # Final dashboard stats
        success, stats = self.test_dashboard_stats()
        if success:
            print(f"   📈 Final Stats: {stats.get('total_instances', 0)} instances, {stats.get('total_accounts', 0)} accounts")

        # Cleanup - delete created accounts
        for account_id in self.created_accounts:
            self.test_delete_cloud_account(account_id)

        # Print summary
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed ({(self.tests_passed/self.tests_run*100):.1f}%)")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed!")
            failed_tests = [t for t in self.test_results if not t['success']]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
            return 1

def main():
    tester = CloudWatcherAPITester()
    return tester.run_comprehensive_test()

if __name__ == "__main__":
    sys.exit(main())