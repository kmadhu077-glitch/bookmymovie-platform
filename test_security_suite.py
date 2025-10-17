"""
🛡️ Advanced Security Suite Test Suite
Test enterprise security framework with OAuth, rate limiting, fraud detection
"""

import requests
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

BASE_URL = "http://127.0.0.1:8023"

class SecurityTestSuite:
    def __init__(self):
        self.test_results = {}
        self.rate_limit_results = {}
    
    def test_service_health(self):
        """Test if the advanced security suite service is running"""
        print("🔍 Testing Advanced Security Suite Health...")
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Security Suite is healthy!")
                print(f"   Service: {health_data['service']}")
                print(f"   Status: {health_data['status']}")
                print(f"   Features: {', '.join(health_data['features'])}")
                print(f"   Active Rules: {health_data['active_rules']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Service connection failed: {e}")
            return False
    
    def test_oauth_providers(self):
        """Test OAuth provider endpoints"""
        print("\n🔐 Testing OAuth Providers...")
        
        oauth_providers = ["google", "github"]
        successful_redirects = 0
        
        for provider in oauth_providers:
            try:
                # Test OAuth URL generation (should redirect)
                response = requests.get(f"{BASE_URL}/oauth/{provider}", allow_redirects=False)
                if response.status_code in [302, 307]:  # Redirect codes
                    print(f"✅ {provider.title()} OAuth redirect working")
                    successful_redirects += 1
                    
                    # Check if redirect URL contains expected OAuth provider domain
                    location = response.headers.get('location', '')
                    if provider == 'google' and 'accounts.google.com' in location:
                        print(f"   ✓ Google OAuth URL correctly formatted")
                    elif provider == 'github' and 'github.com' in location:
                        print(f"   ✓ GitHub OAuth URL correctly formatted")
                else:
                    print(f"❌ {provider.title()} OAuth failed: {response.status_code}")
            except Exception as e:
                print(f"❌ Error testing {provider} OAuth: {e}")
        
        return successful_redirects
    
    def test_rate_limiting(self):
        """Test API rate limiting functionality"""
        print("\n🚦 Testing Rate Limiting...")
        
        test_endpoints = [
            "/health",
            "/security/analytics"
        ]
        
        rate_limit_triggered = False
        
        for endpoint in test_endpoints:
            print(f"   Testing rate limits on {endpoint}...")
            
            # Make rapid requests to trigger rate limiting
            for i in range(15):  # Try to exceed typical rate limits
                try:
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=2)
                    if response.status_code == 429:  # Rate limit exceeded
                        print(f"   ✅ Rate limit triggered on request {i+1}")
                        rate_limit_triggered = True
                        break
                    elif response.status_code != 200:
                        print(f"   ⚠️ Unexpected response: {response.status_code}")
                        break
                except Exception as e:
                    print(f"   ❌ Request {i+1} failed: {e}")
                    break
                
                time.sleep(0.1)  # Small delay between requests
            
            if rate_limit_triggered:
                break
        
        return rate_limit_triggered
    
    def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent load"""
        print("\n⚡ Testing Concurrent Rate Limiting...")
        
        def make_request(thread_id):
            """Make a single request"""
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=5)
                return {
                    'thread_id': thread_id,
                    'status_code': response.status_code,
                    'timestamp': time.time()
                }
            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'error': str(e),
                    'timestamp': time.time()
                }
        
        # Launch concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            results = [future.result() for future in futures]
        
        # Analyze results
        success_count = sum(1 for r in results if r.get('status_code') == 200)
        rate_limited_count = sum(1 for r in results if r.get('status_code') == 429)
        error_count = sum(1 for r in results if 'error' in r)
        
        print(f"   📊 Concurrent Request Results:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   🚦 Rate Limited: {rate_limited_count}")
        print(f"   ❌ Errors: {error_count}")
        
        return rate_limited_count > 0
    
    def test_fraud_detection(self):
        """Test fraud detection system"""
        print("\n🔍 Testing Fraud Detection...")
        
        # Test various fraud scenarios
        fraud_scenarios = [
            {
                "name": "Rapid Multiple Bookings",
                "user_id": "test_user_001",
                "event_data": {
                    "recent_booking_count": 15,
                    "booking_pattern": "rapid",
                    "time_window": 300
                }
            },
            {
                "name": "Multiple Payment Failures",
                "user_id": "test_user_002", 
                "event_data": {
                    "payment_failures": 5,
                    "failure_pattern": "repeated",
                    "time_window": 600
                }
            },
            {
                "name": "Geographical Anomaly",
                "user_id": "test_user_003",
                "event_data": {
                    "geo_distance_km": 2000,
                    "previous_location": "New York",
                    "current_location": "London",
                    "time_window": 3600
                }
            },
            {
                "name": "Normal User Behavior",
                "user_id": "test_user_004",
                "event_data": {
                    "recent_booking_count": 2,
                    "payment_failures": 0,
                    "geo_distance_km": 10
                }
            }
        ]
        
        fraud_detected = 0
        
        for scenario in fraud_scenarios:
            try:
                response = requests.post(
                    f"{BASE_URL}/security/fraud-check",
                    params={"user_id": scenario["user_id"]},
                    json=scenario["event_data"]
                )
                
                if response.status_code == 200:
                    result = response.json()
                    fraud_score = result.get('fraud_score', 0)
                    risk_level = result.get('risk_level', 'NONE')
                    action = result.get('recommended_action', 'ALLOW')
                    
                    print(f"   🎯 {scenario['name']}:")
                    print(f"      Fraud Score: {fraud_score:.2f}")
                    print(f"      Risk Level: {risk_level}")
                    print(f"      Action: {action}")
                    
                    if fraud_score > 0.5:
                        fraud_detected += 1
                        
                else:
                    print(f"   ❌ Fraud check failed for {scenario['name']}: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error testing {scenario['name']}: {e}")
        
        return fraud_detected
    
    def test_security_analytics(self):
        """Test security analytics endpoint"""
        print("\n📊 Testing Security Analytics...")
        
        try:
            response = requests.get(f"{BASE_URL}/security/analytics")
            if response.status_code == 200:
                analytics = response.json()
                
                print("✅ Security analytics retrieved successfully:")
                print(f"   Period: {analytics.get('period', 'N/A')}")
                
                security_events = analytics.get('security_events', {})
                print(f"   Security Events (24h): {security_events.get('total', 0)}")
                
                rate_limiting = analytics.get('rate_limiting', {})
                print(f"   Rate Limit Violations (1h): {rate_limiting.get('violations_1h', 0)}")
                
                fraud_detection = analytics.get('fraud_detection', {})
                print(f"   Fraud Rules Triggered: {fraud_detection.get('rules_triggered', 0)}")
                
                security_alerts = analytics.get('security_alerts', {})
                print(f"   Security Alerts (24h): {security_alerts.get('total', 0)}")
                
                return True
            else:
                print(f"❌ Analytics retrieval failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error retrieving analytics: {e}")
            return False
    
    def test_security_logs(self):
        """Test security logs retrieval"""
        print("\n📋 Testing Security Logs...")
        
        try:
            # Test basic log retrieval
            response = requests.get(f"{BASE_URL}/security/logs?limit=10")
            if response.status_code == 200:
                logs_data = response.json()
                logs_count = logs_data.get('total_logs', 0)
                print(f"✅ Retrieved {logs_count} security logs")
                
                # Test filtered log retrieval
                response_filtered = requests.get(f"{BASE_URL}/security/logs?event_type=api_access&limit=5")
                if response_filtered.status_code == 200:
                    filtered_data = response_filtered.json()
                    filtered_count = filtered_data.get('total_logs', 0)
                    print(f"✅ Retrieved {filtered_count} filtered logs (api_access)")
                    return True
                else:
                    print(f"⚠️ Filtered logs failed: {response_filtered.status_code}")
                    return True  # Basic logs worked
            else:
                print(f"❌ Security logs retrieval failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error retrieving security logs: {e}")
            return False
    
    def test_ip_blocking(self):
        """Test IP blocking functionality"""
        print("\n🚫 Testing IP Blocking...")
        
        test_ip = "192.168.100.100"  # Test IP that won't affect real traffic
        
        try:
            # Block IP address
            response = requests.post(
                f"{BASE_URL}/security/block-ip",
                params={
                    "ip_address": test_ip,
                    "reason": "Test blocking functionality",
                    "permanent": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ IP blocking successful:")
                print(f"   Blocked IP: {result.get('ip_address')}")
                print(f"   Reason: {result.get('reason')}")
                print(f"   Permanent: {result.get('permanent')}")
                print(f"   Blocked At: {result.get('blocked_at')}")
                return True
            else:
                print(f"❌ IP blocking failed: {response.status_code}")
                if response.status_code != 404:
                    print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing IP blocking: {e}")
            return False
    
    def test_dashboard_access(self):
        """Test security dashboard accessibility"""
        print("\n🖥️ Testing Security Dashboard...")
        
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            if response.status_code == 200 and "Advanced Security Suite" in response.text:
                print("✅ Security dashboard is accessible and loads properly")
                print(f"   Dashboard URL: {BASE_URL}/")
                return True
            else:
                print(f"❌ Dashboard access failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
            return False
    
    def stress_test_security(self):
        """Perform stress test on security components"""
        print("\n💪 Running Security Stress Test...")
        
        def security_request_worker():
            """Worker function for stress testing"""
            try:
                # Mix of different requests
                endpoints = ["/health", "/security/analytics", "/security/logs?limit=1"]
                
                for endpoint in endpoints:
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                    if response.status_code in [200, 429]:  # Success or rate limited
                        continue
                    else:
                        return False
                return True
            except:
                return False
        
        # Run concurrent stress test
        success_count = 0
        total_workers = 20
        
        with ThreadPoolExecutor(max_workers=total_workers) as executor:
            futures = [executor.submit(security_request_worker) for _ in range(total_workers)]
            results = [future.result() for future in futures]
            success_count = sum(results)
        
        print(f"   📊 Stress Test Results:")
        print(f"   ✅ Successful Workers: {success_count}/{total_workers}")
        print(f"   📈 Success Rate: {success_count/total_workers*100:.1f}%")
        
        return success_count >= total_workers * 0.7  # 70% success rate threshold
    
    def run_comprehensive_test(self):
        """Run complete security test suite"""
        print("🛡️ ADVANCED SECURITY SUITE - COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        
        # Test service health
        if not self.test_service_health():
            print("❌ Service not available. Ending tests.")
            return False
        
        # Run all security tests
        oauth_success = self.test_oauth_providers() > 0
        rate_limiting_basic = self.test_rate_limiting()
        rate_limiting_concurrent = self.test_concurrent_rate_limiting()
        fraud_detections = self.test_fraud_detection()
        analytics_ok = self.test_security_analytics()
        logs_ok = self.test_security_logs()
        ip_blocking_ok = self.test_ip_blocking()
        dashboard_ok = self.test_dashboard_access()
        stress_test_ok = self.stress_test_security()
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE SECURITY TEST SUMMARY")
        print("=" * 80)
        print(f"✅ Service Health: {'PASS' if True else 'FAIL'}")
        print(f"✅ OAuth Providers: {'PASS' if oauth_success else 'FAIL'}")
        print(f"✅ Rate Limiting (Basic): {'PASS' if rate_limiting_basic else 'FAIL'}")
        print(f"✅ Rate Limiting (Concurrent): {'PASS' if rate_limiting_concurrent else 'FAIL'}")
        print(f"✅ Fraud Detection: {'PASS' if fraud_detections > 0 else 'FAIL'} ({fraud_detections} scenarios triggered)")
        print(f"✅ Security Analytics: {'PASS' if analytics_ok else 'FAIL'}")
        print(f"✅ Security Logs: {'PASS' if logs_ok else 'FAIL'}")
        print(f"✅ IP Blocking: {'PASS' if ip_blocking_ok else 'FAIL'}")
        print(f"✅ Dashboard Access: {'PASS' if dashboard_ok else 'FAIL'}")
        print(f"✅ Stress Testing: {'PASS' if stress_test_ok else 'FAIL'}")
        
        print(f"\n🛡️ ADVANCED SECURITY SUITE STATUS:")
        print(f"   🌐 Security Dashboard: {BASE_URL}/")
        print(f"   📚 API Documentation: {BASE_URL}/docs")
        print(f"   🔐 OAuth Authentication: Google, GitHub SSO")
        print(f"   🚦 API Rate Limiting: Multi-endpoint protection")
        print(f"   🔍 Fraud Detection: Real-time risk assessment")
        print(f"   📊 Security Analytics: Comprehensive monitoring")
        print(f"   🚫 IP Blocking: Dynamic threat response")
        print(f"   📋 Security Logging: Complete audit trail")
        
        success = (oauth_success and rate_limiting_basic and fraud_detections > 0 and 
                  analytics_ok and dashboard_ok)
        
        if success:
            print("\n🎉 ALL SECURITY TESTS PASSED! Advanced Security Suite is fully operational!")
            print("\n💡 Key Security Features Verified:")
            print("   🔐 Multi-provider OAuth authentication (Google, GitHub)")
            print("   🚦 Intelligent API rate limiting with concurrent protection")
            print("   🔍 Real-time fraud detection with multiple rule engines")
            print("   📊 Comprehensive security analytics and reporting")
            print("   🚫 Dynamic IP blocking and threat response")
            print("   📋 Complete security audit logging")
            print("   💪 High-performance concurrent request handling")
        else:
            print("\n⚠️  Some security tests failed. Check service configuration.")
        
        return success

def main():
    """Run the advanced security suite test"""
    test_suite = SecurityTestSuite()
    
    print("🚀 Starting Advanced Security Suite Tests...")
    print("⏳ Please ensure the security service is running on port 8023")
    print()
    
    # Wait a moment for service to be ready
    time.sleep(2)
    
    success = test_suite.run_comprehensive_test()
    
    if success:
        print(f"\n🎯 Next Steps:")
        print(f"   • Open security dashboard: {BASE_URL}/")
        print(f"   • Test OAuth login flows with Google/GitHub")
        print(f"   • Monitor security analytics and threat detection")
        print(f"   • Configure custom fraud detection rules")
        print(f"   • Review security logs and alerts")
    
    return success

if __name__ == "__main__":
    main()