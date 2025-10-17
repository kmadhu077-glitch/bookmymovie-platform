#!/usr/bin/env python3
"""
Security Dashboard Validation Script
Generates security events to test dashboard functionality
"""

import requests
import json
import time
import threading
from datetime import datetime

class SecurityActivityGenerator:
    def __init__(self):
        self.services = {
            'auth': 'http://127.0.0.1:8013',
            'catalog': 'http://127.0.0.1:8012',
            'booking': 'http://127.0.0.1:8014',
            'payment': 'http://127.0.0.1:8015'
        }
        self.sessions = []
        
    def create_authenticated_session(self, user_suffix):
        """Create a new authenticated session"""
        session = requests.Session()
        
        # Register user
        user_data = {
            "username": f"testuser_{user_suffix}",
            "email": f"test_{user_suffix}@example.com", 
            "password": "SecurePassword123!",
            "phone_number": f"123456{user_suffix:04d}",
            "full_name": f"Test User {user_suffix}"
        }
        
        try:
            response = session.post(f"{self.services['auth']}/auth/register", json=user_data, timeout=10)
            
            if response.status_code in [200, 201]:
                result = response.json()
                token = result.get('access_token')
                
                if token:
                    session.headers.update({'Authorization': f'Bearer {token}'})
                    print(f"✅ Created authenticated session for user_{user_suffix}")
                    return session
                    
        except Exception as e:
            pass
            
        return None
    
    def generate_legitimate_activity(self, session, user_id):
        """Generate legitimate user activity"""
        try:
            # Browse catalog
            session.get(f"{self.services['catalog']}/catalog/movies", timeout=5)
            time.sleep(0.5)
            
            # Check user bookings  
            session.get(f"{self.services['booking']}/booking/user-bookings", timeout=5)
            time.sleep(0.5)
            
            # Update profile
            session.get(f"{self.services['auth']}/auth/profile", timeout=5)
            
        except Exception as e:
            pass
    
    def generate_suspicious_activity(self):
        """Generate suspicious activity patterns"""
        session = requests.Session()
        
        # Attempt SQL injection
        malicious_data = {
            "username": "admin'; DROP TABLE users; --",
            "email": "hacker@evil.com",
            "password": "password123",
            "phone_number": "1234567890", 
            "full_name": "Evil Hacker"
        }
        
        try:
            session.post(f"{self.services['auth']}/auth/register", json=malicious_data, timeout=5)
        except:
            pass
            
        # Attempt XSS
        xss_data = {
            "username": "<script>alert('xss')</script>",
            "email": "xss@test.com",
            "password": "password123",
            "phone_number": "1234567890",
            "full_name": "<script>document.cookie</script>"
        }
        
        try:
            session.post(f"{self.services['auth']}/auth/register", json=xss_data, timeout=5)
        except:
            pass
    
    def generate_rate_limit_events(self):
        """Generate rate limiting events"""
        session = requests.Session()
        
        # Make rapid requests to trigger rate limiting
        for i in range(20):
            try:
                session.get(f"{self.services['auth']}/auth/profile", timeout=2)
                time.sleep(0.05)
            except:
                pass
    
    def run_security_validation(self):
        """Run comprehensive security dashboard validation"""
        print("🔒 SECURITY DASHBOARD VALIDATION")
        print("=" * 50)
        print(f"Started at: {datetime.now()}")
        print()
        
        # Create multiple authenticated sessions
        print("📱 Creating authenticated user sessions...")
        for i in range(3):
            session = self.create_authenticated_session(int(time.time()) + i)
            if session:
                self.sessions.append(session)
        
        print(f"   Created {len(self.sessions)} authenticated sessions")
        print()
        
        # Generate legitimate activity
        print("👤 Generating legitimate user activity...")
        for i, session in enumerate(self.sessions):
            threading.Thread(target=self.generate_legitimate_activity, args=(session, i)).start()
        
        time.sleep(2)
        
        # Generate security events
        print("🚨 Generating security events...")
        
        # Suspicious activity
        threading.Thread(target=self.generate_suspicious_activity).start()
        time.sleep(1)
        
        # Rate limiting events
        threading.Thread(target=self.generate_rate_limit_events).start()
        time.sleep(2)
        
        # More legitimate activity 
        print("📊 Continuing normal activity...")
        for session in self.sessions:
            threading.Thread(target=self.generate_legitimate_activity, args=(session, 1)).start()
        
        time.sleep(3)
        
        print("\n" + "=" * 50)
        print("✅ SECURITY DASHBOARD VALIDATION COMPLETED!")
        print()
        print("📊 Dashboard should now show:")
        print("   • User registration events")
        print("   • Authentication activities") 
        print("   • Input validation blocks")
        print("   • Rate limiting triggers")
        print("   • Cross-service API calls")
        print()
        print("🌐 View dashboard at: http://127.0.0.1:8080/security-dashboard.html")
        print("📈 Check real-time security metrics and activity logs")

if __name__ == "__main__":
    generator = SecurityActivityGenerator()
    generator.run_security_validation()