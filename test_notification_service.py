"""
Test script for Enhanced Notification Service
"""

import requests
import json
import time

def test_notification_service():
    base_url = "http://127.0.0.1:8018"
    
    print("🧪 Testing BookMyMovie Enhanced Notification Service...")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Health Check: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health Check Failed: {str(e)}")
        return False
    
    # Test 2: Service info
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Service Info: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Features: {len(data.get('features', []))} features")
    except Exception as e:
        print(f"❌ Service Info Failed: {str(e)}")
    
    # Test 3: Register device
    try:
        device_data = {
            "user_id": 1,
            "device_token": "test_device_token_123",
            "platform": "web",
            "app_version": "2.1.0"
        }
        
        response = requests.post(
            f"{base_url}/devices/register",
            params=device_data,
            timeout=5
        )
        print(f"✅ Device Registration: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Device Registration Failed: {str(e)}")
    
    # Test 4: Send test notification
    try:
        response = requests.post(
            f"{base_url}/notifications/test",
            params={"user_id": 1, "message": "Test notification from test script! 🚀"},
            timeout=5
        )
        print(f"✅ Test Notification: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Test Notification Failed: {str(e)}")
    
    # Test 5: Get notification templates
    try:
        response = requests.get(f"{base_url}/notifications/templates", timeout=5)
        print(f"✅ Templates: {response.status_code}")
        if response.status_code == 200:
            templates = response.json().get('templates', [])
            print(f"   Available Templates: {len(templates)}")
            for template in templates[:3]:  # Show first 3
                print(f"      - {template.get('type')}: {template.get('title')}")
    except Exception as e:
        print(f"❌ Templates Failed: {str(e)}")
    
    # Test 6: Get user preferences
    try:
        response = requests.get(f"{base_url}/preferences/1", timeout=5)
        print(f"✅ User Preferences: {response.status_code}")
        if response.status_code == 200:
            prefs = response.json()
            print(f"   User {prefs.get('user_id')} preferences loaded")
    except Exception as e:
        print(f"❌ User Preferences Failed: {str(e)}")
    
    # Test 7: Get analytics
    try:
        response = requests.get(f"{base_url}/analytics/dashboard", timeout=5)
        print(f"✅ Analytics Dashboard: {response.status_code}")
        if response.status_code == 200:
            analytics = response.json()
            overview = analytics.get('overview', {})
            print(f"   Total Notifications: {overview.get('total_notifications')}")
            print(f"   Active Devices: {overview.get('active_devices')}")
            print(f"   Delivery Rate: {overview.get('delivery_rate')}%")
    except Exception as e:
        print(f"❌ Analytics Dashboard Failed: {str(e)}")
    
    # Test 8: Get notification history
    try:
        response = requests.get(f"{base_url}/history/1", timeout=5)
        print(f"✅ Notification History: {response.status_code}")
        if response.status_code == 200:
            history = response.json()
            print(f"   History entries for user 1: {len(history.get('history', []))}")
    except Exception as e:
        print(f"❌ Notification History Failed: {str(e)}")
    
    print("\n🎉 Enhanced Notification Service test completed!")
    print(f"📱 Dashboard available at: {base_url}/dashboard")
    print(f"📊 Analytics available at: {base_url}/analytics/dashboard")
    
    return True

if __name__ == "__main__":
    # Wait a moment for service to be ready
    print("⏳ Waiting for notification service to be ready...")
    time.sleep(2)
    
    test_notification_service()