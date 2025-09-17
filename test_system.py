#!/usr/bin/env python3
"""
System functionality test script
"""

import requests
import json
import sys
import time
from datetime import datetime

class SystemTester:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
    
    def log_test(self, test_name, success, message=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_server_running(self):
        """Test if server is running"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                self.log_test("Server Running", True, "Server is accessible")
                return True
            else:
                self.log_test("Server Running", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Server Running", False, f"Connection error: {str(e)}")
            return False
    
    def test_login_page(self):
        """Test login page loads"""
        try:
            response = self.session.get(f"{self.base_url}/login")
            if response.status_code == 200 and "Đăng nhập" in response.text:
                self.log_test("Login Page", True, "Login page loads correctly")
                return True
            else:
                self.log_test("Login Page", False, "Login page not accessible")
                return False
        except Exception as e:
            self.log_test("Login Page", False, f"Error: {str(e)}")
            return False
    
    def test_login_functionality(self):
        """Test login with test credentials"""
        try:
            # Get login page first to get CSRF token
            login_page = self.session.get(f"{self.base_url}/login")
            
            # Try login with test credentials
            login_data = {
                'employee_id': 'ADMIN001',
                'password': 'admin123'
            }
            
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            if response.status_code == 200 and "dashboard" in response.url:
                self.log_test("Login Functionality", True, "Login successful")
                return True
            else:
                self.log_test("Login Functionality", False, "Login failed or redirected incorrectly")
                return False
        except Exception as e:
            self.log_test("Login Functionality", False, f"Error: {str(e)}")
            return False
    
    def test_dashboard_access(self):
        """Test dashboard access after login"""
        try:
            response = self.session.get(f"{self.base_url}/dashboard")
            if response.status_code == 200 and "Dashboard" in response.text:
                self.log_test("Dashboard Access", True, "Dashboard accessible")
                return True
            else:
                self.log_test("Dashboard Access", False, "Dashboard not accessible")
                return False
        except Exception as e:
            self.log_test("Dashboard Access", False, f"Error: {str(e)}")
            return False
    
    def test_settings_page(self):
        """Test settings page"""
        try:
            response = self.session.get(f"{self.base_url}/settings")
            if response.status_code == 200 and "Cài đặt" in response.text:
                self.log_test("Settings Page", True, "Settings page accessible")
                return True
            else:
                self.log_test("Settings Page", False, "Settings page not accessible")
                return False
        except Exception as e:
            self.log_test("Settings Page", False, f"Error: {str(e)}")
            return False
    
    def test_leave_request_page(self):
        """Test leave request page"""
        try:
            response = self.session.get(f"{self.base_url}/leave-request")
            if response.status_code == 200 and "nghỉ phép" in response.text:
                self.log_test("Leave Request Page", True, "Leave request page accessible")
                return True
            else:
                self.log_test("Leave Request Page", False, "Leave request page not accessible")
                return False
        except Exception as e:
            self.log_test("Leave Request Page", False, f"Error: {str(e)}")
            return False
    
    def test_css_loading(self):
        """Test CSS files loading"""
        try:
            response = self.session.get(f"{self.base_url}/static/css/style.css")
            if response.status_code == 200 and ":root" in response.text:
                self.log_test("CSS Loading", True, "CSS files load correctly")
                return True
            else:
                self.log_test("CSS Loading", False, "CSS files not loading")
                return False
        except Exception as e:
            self.log_test("CSS Loading", False, f"Error: {str(e)}")
            return False
    
    def test_database_connection(self):
        """Test database connection by checking API endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/attendance/pending")
            if response.status_code in [200, 401]:  # 401 is expected if not logged in
                self.log_test("Database Connection", True, "Database connection working")
                return True
            else:
                self.log_test("Database Connection", False, f"Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Database Connection", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting System Tests...")
        print("=" * 50)
        
        # Basic connectivity tests
        if not self.test_server_running():
            print("❌ Server not running. Stopping tests.")
            return False
        
        # UI tests
        self.test_login_page()
        self.test_css_loading()
        
        # Functionality tests
        login_success = self.test_login_functionality()
        if login_success:
            self.test_dashboard_access()
            self.test_settings_page()
            self.test_leave_request_page()
        
        # Database tests
        self.test_database_connection()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check the details above.")
            return False
    
    def save_results(self, filename="test_results.json"):
        """Save test results to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(self.test_results),
                'passed': sum(1 for r in self.test_results if r['success']),
                'failed': sum(1 for r in self.test_results if not r['success']),
                'results': self.test_results
            }, f, indent=2, ensure_ascii=False)
        print(f"📄 Test results saved to {filename}")

if __name__ == "__main__":
    tester = SystemTester()
    
    # Check if custom URL provided
    if len(sys.argv) > 1:
        tester.base_url = sys.argv[1]
    
    print(f"🔗 Testing URL: {tester.base_url}")
    
    success = tester.run_all_tests()
    tester.save_results()
    
    sys.exit(0 if success else 1)
