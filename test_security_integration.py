#!/usr/bin/env python3
"""
Comprehensive Security Integration Test Suite
Tests the complete secure BookMyMovie platform
"""

import requests
import json
import time
from datetime import datetime

# Service endpoints
SERVICES = {
    'auth': 'http://127.0.0.1:8013',
    'catalog': 'http://127.0.0.1:8012',
    'booking': 'http://127.0.0.1:8014',
    'payment': 'http://127.0.0.1:8015',
    'realtime': 'http://127.0.0.1:8016'
}

class SecurityTester:
    def __init__(self):
        self.session = requests.Session()
        self.jwt_token = None
        self.user_id = None
        
    def log_test(self, test_name, result, details=""):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        print()
    
    def test_service_health(self):
        """Test if all services are running"""
        print("=== SERVICE HEALTH CHECK ===")
        
        for service, url in SERVICES.items():
            try:
                response = self.session.get(f"{url}/health", timeout=5)
                self.log_test(f"{service.capitalize()} Service Health", 
                             response.status_code == 200,
                             f"Status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                self.log_test(f"{service.capitalize()} Service Health", 
                             False, f"Error: {str(e)}")
    
    def test_user_registration(self):
        """Test user registration with security validation"""
        print("=== USER REGISTRATION TEST ===")
        
        # Test valid registration
        user_data = {
            "username": "securitytest",
            "email": "security@test.com",
            "password": "SecurePassword123!",
            "phone_number": "1234567890",
            "full_name": "Security Test User"
        }
        
        try:
            response = self.session.post(
                f"{SERVICES['auth']}/auth/register",
                json=user_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                self.user_id = result.get('user_id')
                self.jwt_token = result.get('access_token')  # Get token from registration
                if self.jwt_token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.jwt_token}'
                    })
                self.log_test("User Registration", True, 
                             f"User ID: {self.user_id}, JWT Token obtained")
                return True
            else:
                self.log_test("User Registration", False,
                             f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("User Registration", False, f"Error: {str(e)}")
            return False
    
    def test_user_login(self):
        """Test user login and JWT token generation"""
        print("=== USER LOGIN TEST ===")
        
        login_data = {
            "username": "securitytest",
            "password": "SecurePassword123!"
        }
        
        try:
            response = self.session.post(
                f"{SERVICES['auth']}/auth/login",
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.jwt_token = result.get('access_token')
                self.session.headers.update({
                    'Authorization': f'Bearer {self.jwt_token}'
                })
                self.log_test("User Login", True,
                             f"JWT Token obtained (length: {len(self.jwt_token)})")
                return True
            else:
                self.log_test("User Login", False,
                             f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("User Login", False, f"Error: {str(e)}")
            return False
    
    def test_authenticated_access(self):
        """Test JWT authentication across services"""
        print("=== JWT AUTHENTICATION TEST ===")
        
        # Test authenticated access to catalog service
        try:
            response = self.session.get(
                f"{SERVICES['catalog']}/catalog/movies",
                timeout=10
            )
            
            self.log_test("Authenticated Catalog Access",
                         response.status_code in [200, 404],
                         f"Status: {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            self.log_test("Authenticated Catalog Access", False, f"Error: {str(e)}")
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        print("=== RATE LIMITING TEST ===")
        
        # Make multiple rapid requests to test rate limiting
        rate_limit_hit = False
        
        for i in range(15):  # Attempt more than typical rate limit
            try:
                response = self.session.get(f"{SERVICES['auth']}/auth/profile", timeout=5)
                if response.status_code == 429:
                    rate_limit_hit = True
                    break
                time.sleep(0.1)  # Brief delay between requests
            except:
                pass
        
        self.log_test("Rate Limiting Active", rate_limit_hit,
                     "Rate limiting triggered as expected" if rate_limit_hit 
                     else "Rate limiting not triggered (may use higher limits)")
    
    def test_input_validation(self):
        """Test input validation and sanitization"""
        print("=== INPUT VALIDATION TEST ===")
        
        # Test invalid registration data
        invalid_data = {
            "username": "<script>alert('xss')</script>",
            "email": "not-an-email",
            "password": "weak",
            "phone_number": "invalid",
            "full_name": "<script>alert('xss')</script>"
        }
        
        try:
            response = self.session.post(
                f"{SERVICES['auth']}/auth/register",
                json=invalid_data,
                timeout=10
            )
            
            # Should reject invalid data
            rejected = response.status_code in [400, 422]
            self.log_test("Input Validation", rejected,
                         f"Invalid data properly rejected with status {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            self.log_test("Input Validation", False, f"Error: {str(e)}")
    
    def test_security_headers(self):
        """Test security headers in responses"""
        print("=== SECURITY HEADERS TEST ===")
        
        try:
            response = self.session.get(f"{SERVICES['auth']}/health", timeout=10)
            headers = response.headers
            
            # Check for common security headers
            security_headers = [
                'X-Content-Type-Options',
                'X-Frame-Options', 
                'X-XSS-Protection'
            ]
            
            headers_present = sum(1 for header in security_headers if header in headers)
            self.log_test("Security Headers Present",
                         headers_present > 0,
                         f"{headers_present}/{len(security_headers)} security headers found")
            
        except requests.exceptions.RequestException as e:
            self.log_test("Security Headers", False, f"Error: {str(e)}")
    
    def run_comprehensive_test(self):
        """Run all security tests"""
        print("🔒 BOOKMYMOVIE SECURITY INTEGRATION TEST")
        print("=" * 50)
        print(f"Test started at: {datetime.now()}")
        print()
        
        # Run test suite
        self.test_service_health()
        
        if self.test_user_registration():
            if self.test_user_login():
                self.test_authenticated_access()
                self.test_rate_limiting()
        
        self.test_input_validation()
        self.test_security_headers()
        
        print("=" * 50)
        print("🔒 Security integration test completed!")
        print(f"JWT Token: {'✅ Active' if self.jwt_token else '❌ Not obtained'}")
        print(f"User ID: {self.user_id if self.user_id else 'Not created'}")

if __name__ == "__main__":
    tester = SecurityTester()
    tester.run_comprehensive_test()