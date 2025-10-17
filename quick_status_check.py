#!/usr/bin/env python3
"""
Simple Service Status Test
"""

import requests
import json

def test_service(name, port, endpoint="/docs"):
    try:
        response = requests.get(f"http://127.0.0.1:{port}{endpoint}", timeout=5)
        print(f"✅ {name} Service (port {port}): Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ {name} Service (port {port}): Error - {str(e)}")
        return False

def test_auth_registration():
    """Test the auth service registration endpoint"""
    try:
        user_data = {
            "username": "testuser123", 
            "email": "test123@example.com",
            "password": "SecurePassword123!",
            "phone_number": "1234567890"
        }
        
        response = requests.post(
            "http://127.0.0.1:8013/auth/register",
            json=user_data,
            timeout=10
        )
        
        print(f"🔐 Registration Test: Status {response.status_code}")
        if response.status_code in [200, 201]:
            print(f"   ✅ Registration successful")
            return True
        elif response.status_code == 400:
            print(f"   ⚠️  User might already exist: {response.text}")
            return True  # This is also a valid response
        else:
            print(f"   ❌ Registration failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Registration Test Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 QUICK SERVICE STATUS CHECK")
    print("=" * 40)
    
    services = [
        ("Auth", 8013),
        ("Catalog", 8012), 
        ("Booking", 8014),
        ("Payment", 8015),
        ("Realtime", 8016)
    ]
    
    running_services = 0
    for name, port in services:
        if test_service(name, port):
            running_services += 1
    
    print(f"\n📊 Services Running: {running_services}/{len(services)}")
    
    if running_services > 0:
        print("\n🧪 Testing Auth Service...")
        test_auth_registration()
    
    print("\n✅ Quick status check completed!")