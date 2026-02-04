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

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, data: Dict = None, params: Dict = None) -> tuple:
        """Run a single API test"""
        url = f"{self.api_base}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
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
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

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
        """Run comprehensive API test suite"""
        print("🚀 Starting Cloud Watcher API Tests...")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)

        # 1. Health Check
        self.test_health_check()

        # 2. Dashboard Stats (initial state)
        self.test_dashboard_stats()

        # 3. Create cloud accounts for different providers
        aws_account_id = self.test_create_cloud_account("aws")
        azure_account_id = self.test_create_cloud_account("azure")
        gcp_account_id = self.test_create_cloud_account("gcp")

        # 4. List accounts
        self.test_list_cloud_accounts()

        # 5. Get specific account
        if aws_account_id:
            self.test_get_cloud_account(aws_account_id)

        # 6. Sync all accounts (generates mock data)
        self.test_sync_all_accounts()

        # 7. Sync single account
        if aws_account_id:
            self.test_sync_single_account(aws_account_id)

        # 8. Test instances endpoints
        self.test_list_instances()
        self.test_list_instances_with_filters()

        # 9. Test recommendations
        self.test_list_recommendations()
        self.test_run_recommendations()
        self.test_list_recommendations_by_category()

        # 10. Test recommendation status update (if we have recommendations)
        success, recs = self.run_test("Get Recommendations for Update Test", "GET", "recommendations", 200, params={"limit": 1})
        if success and recs and len(recs) > 0:
            rec_id = recs[0].get('id')
            if rec_id:
                self.test_update_recommendation_status(rec_id)

        # 11. Dashboard stats after data creation
        success, stats = self.test_dashboard_stats()
        if success:
            print(f"   📈 Final Stats: {stats.get('total_instances', 0)} instances, {stats.get('total_accounts', 0)} accounts")

        # 12. Cleanup - delete created accounts
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