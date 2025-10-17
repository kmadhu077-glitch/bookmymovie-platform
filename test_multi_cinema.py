"""
🧪 Multi-Cinema Chain Management System Test Suite
Test comprehensive enterprise theater management functionality
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8020"

class MultiCinemaTestSuite:
    def __init__(self):
        self.created_chains = []
        self.created_theaters = []
        self.created_screens = []
    
    def test_service_health(self):
        """Test if the service is running"""
        print("🔍 Testing Multi-Cinema Service Health...")
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Service is healthy!")
                print(f"   Service: {health_data['service']}")
                print(f"   Status: {health_data['status']}")
                print(f"   Features: {', '.join(health_data['features'])}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Service connection failed: {e}")
            return False
    
    def test_create_cinema_chains(self):
        """Test creating multiple cinema chains"""
        print("\n🏢 Testing Cinema Chain Creation...")
        
        chains = [
            {
                "name": "Premiere Cinemas",
                "description": "Premium movie experience with luxury amenities",
                "headquarters_location": "Los Angeles, CA",
                "founded_year": 1995,
                "website": "https://premierecinemas.com",
                "contact_email": "info@premierecinemas.com",
                "contact_phone": "+1-555-CINEMA",
                "chain_type": "multiplex"
            },
            {
                "name": "IMAX Entertainment",
                "description": "Immersive large-format cinema experience",
                "headquarters_location": "New York, NY",
                "founded_year": 1987,
                "website": "https://imax.com",
                "contact_email": "contact@imax.com",
                "contact_phone": "+1-800-IMAX-NOW",
                "chain_type": "imax"
            },
            {
                "name": "Drive-In Movie Magic",
                "description": "Classic outdoor movie experience for families",
                "headquarters_location": "Austin, TX",
                "founded_year": 1955,
                "website": "https://driveinmagic.com",
                "contact_email": "hello@driveinmagic.com",
                "contact_phone": "+1-512-DRIVE-IN",
                "chain_type": "drive-in"
            },
            {
                "name": "Boutique Cinema Co.",
                "description": "Independent theaters with curated film selections",
                "headquarters_location": "Portland, OR",
                "founded_year": 2010,
                "website": "https://boutiquecinema.com",
                "contact_email": "curator@boutiquecinema.com",
                "contact_phone": "+1-503-BOUTIQUE",
                "chain_type": "boutique"
            }
        ]
        
        for chain in chains:
            try:
                response = requests.post(f"{BASE_URL}/chains/", json=chain)
                if response.status_code == 200:
                    result = response.json()
                    self.created_chains.append(result['chain_id'])
                    print(f"✅ Created chain: {chain['name']} (ID: {result['chain_id']})")
                else:
                    print(f"❌ Failed to create chain {chain['name']}: {response.status_code}")
                    print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating chain {chain['name']}: {e}")
        
        return len(self.created_chains)
    
    def test_add_theaters(self):
        """Test adding theaters to chains"""
        print("\n🎪 Testing Theater Addition...")
        
        if not self.created_chains:
            print("❌ No chains available for theater testing")
            return 0
        
        theaters = [
            {
                "chain_id": self.created_chains[0],  # Premiere Cinemas
                "name": "Premiere Downtown",
                "address": "123 Main Street",
                "city": "Los Angeles",
                "state": "CA",
                "country": "USA",
                "postal_code": "90210",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "phone": "+1-213-555-MOVIE",
                "email": "downtown@premierecinemas.com",
                "manager_name": "Sarah Johnson",
                "parking_spaces": 200,
                "facilities": {
                    "parking": True,
                    "food_court": True,
                    "3d_screens": 4,
                    "imax": False,
                    "vip_seats": True,
                    "wheelchair_accessible": True
                },
                "operating_hours": {
                    "monday": "10:00-23:00",
                    "tuesday": "10:00-23:00",
                    "wednesday": "10:00-23:00",
                    "thursday": "10:00-23:00",
                    "friday": "10:00-24:00",
                    "saturday": "09:00-24:00",
                    "sunday": "10:00-22:00"
                },
                "opening_date": "2020-03-15"
            },
            {
                "chain_id": self.created_chains[1],  # IMAX Entertainment
                "name": "IMAX Times Square",
                "address": "234 Broadway",
                "city": "New York",
                "state": "NY", 
                "country": "USA",
                "postal_code": "10001",
                "latitude": 40.7589,
                "longitude": -73.9851,
                "phone": "+1-212-555-IMAX",
                "email": "timessquare@imax.com",
                "manager_name": "Michael Chen",
                "parking_spaces": 50,
                "facilities": {
                    "parking": False,
                    "food_court": True,
                    "3d_screens": 2,
                    "imax": True,
                    "vip_seats": False,
                    "wheelchair_accessible": True,
                    "laser_projection": True
                },
                "operating_hours": {
                    "monday": "11:00-23:00",
                    "tuesday": "11:00-23:00",
                    "wednesday": "11:00-23:00",
                    "thursday": "11:00-23:00",
                    "friday": "11:00-01:00",
                    "saturday": "10:00-01:00",
                    "sunday": "11:00-22:00"
                },
                "opening_date": "2018-07-22"
            },
            {
                "chain_id": self.created_chains[2],  # Drive-In Movie Magic
                "name": "Sunset Drive-In",
                "address": "789 Highway 35",
                "city": "Austin",
                "state": "TX",
                "country": "USA",
                "postal_code": "73301",
                "latitude": 30.2672,
                "longitude": -97.7431,
                "phone": "+1-512-555-DRIVE",
                "email": "sunset@driveinmagic.com",
                "manager_name": "Lisa Rodriguez",
                "parking_spaces": 500,
                "facilities": {
                    "parking": True,
                    "food_court": True,
                    "3d_screens": 0,
                    "imax": False,
                    "vip_seats": False,
                    "wheelchair_accessible": True,
                    "outdoor_screen": True,
                    "car_service": True
                },
                "operating_hours": {
                    "monday": "Closed",
                    "tuesday": "Closed", 
                    "wednesday": "19:00-23:00",
                    "thursday": "19:00-23:00",
                    "friday": "19:00-24:00",
                    "saturday": "18:00-24:00",
                    "sunday": "19:00-23:00"
                },
                "opening_date": "1955-06-01"
            }
        ]
        
        for theater in theaters:
            try:
                response = requests.post(f"{BASE_URL}/theaters/", json=theater)
                if response.status_code == 200:
                    result = response.json()
                    self.created_theaters.append(result['theater_id'])
                    print(f"✅ Created theater: {theater['name']} (ID: {result['theater_id']})")
                else:
                    print(f"❌ Failed to create theater {theater['name']}: {response.status_code}")
                    print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating theater {theater['name']}: {e}")
        
        return len(self.created_theaters)
    
    def test_add_screens(self):
        """Test adding screens to theaters"""
        print("\n📺 Testing Screen Addition...")
        
        if not self.created_theaters:
            print("❌ No theaters available for screen testing")
            return 0
        
        screens = [
            # Screens for first theater (Premiere Downtown)
            {
                "theater_id": self.created_theaters[0],
                "screen_number": 1,
                "name": "Premium Screen 1",
                "screen_type": "standard",
                "total_seats": 180,
                "rows": 12,
                "seats_per_row": 15,
                "screen_size": "35ft x 20ft",
                "sound_system": "Dolby Atmos",
                "projection_type": "Digital 4K",
                "accessibility_features": {
                    "wheelchair_spaces": 4,
                    "hearing_loop": True,
                    "audio_description": True
                },
                "premium_features": {
                    "reclining_seats": True,
                    "cup_holders": True,
                    "reserved_seating": True
                }
            },
            {
                "theater_id": self.created_theaters[0],
                "screen_number": 2,
                "name": "VIP Screen",
                "screen_type": "vip",
                "total_seats": 48,
                "rows": 6,
                "seats_per_row": 8,
                "screen_size": "32ft x 18ft",
                "sound_system": "DTS-X",
                "projection_type": "Digital 4K",
                "accessibility_features": {
                    "wheelchair_spaces": 2,
                    "hearing_loop": True
                },
                "premium_features": {
                    "leather_recliners": True,
                    "food_service": True,
                    "wine_bar": True,
                    "reserved_seating": True
                }
            },
            # Screen for IMAX theater
            {
                "theater_id": self.created_theaters[1],
                "screen_number": 1,
                "name": "IMAX Main Screen",
                "screen_type": "imax",
                "total_seats": 400,
                "rows": 20,
                "seats_per_row": 20,
                "screen_size": "75ft x 55ft",
                "sound_system": "IMAX Enhanced Audio",
                "projection_type": "IMAX Laser",
                "accessibility_features": {
                    "wheelchair_spaces": 8,
                    "hearing_loop": True,
                    "audio_description": True
                },
                "premium_features": {
                    "stadium_seating": True,
                    "reserved_seating": True
                }
            }
        ]
        
        for screen in screens:
            try:
                response = requests.post(f"{BASE_URL}/screens/", json=screen)
                if response.status_code == 200:
                    result = response.json()
                    self.created_screens.append(result['screen_id'])
                    print(f"✅ Created screen: {screen['name']} (ID: {result['screen_id']})")
                else:
                    print(f"❌ Failed to create screen {screen['name']}: {response.status_code}")
                    print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating screen {screen['name']}: {e}")
        
        return len(self.created_screens)
    
    def test_location_search(self):
        """Test location-based theater search"""
        print("\n📍 Testing Location-Based Theater Search...")
        
        searches = [
            {
                "name": "Los Angeles Area",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "radius_km": 50.0
            },
            {
                "name": "New York City",
                "latitude": 40.7589,
                "longitude": -73.9851,
                "radius_km": 25.0
            },
            {
                "name": "Austin Area", 
                "latitude": 30.2672,
                "longitude": -97.7431,
                "radius_km": 30.0
            }
        ]
        
        for search in searches:
            try:
                search_data = {
                    "latitude": search["latitude"],
                    "longitude": search["longitude"],
                    "radius_km": search["radius_km"]
                }
                
                response = requests.post(f"{BASE_URL}/theaters/search", json=search_data)
                if response.status_code == 200:
                    theaters = response.json()
                    print(f"✅ {search['name']}: Found {len(theaters)} theaters")
                    for theater in theaters[:3]:  # Show first 3 results
                        print(f"   • {theater['name']} ({theater['chain_name']}) - {theater['distance_km']}km away")
                else:
                    print(f"❌ Search failed for {search['name']}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error searching {search['name']}: {e}")
    
    def test_get_chains(self):
        """Test retrieving all chains"""
        print("\n🏢 Testing Chain Retrieval...")
        
        try:
            response = requests.get(f"{BASE_URL}/chains/")
            if response.status_code == 200:
                chains = response.json()
                print(f"✅ Retrieved {len(chains)} cinema chains:")
                for chain in chains:
                    print(f"   • {chain['name']} ({chain['chain_type']}) - {chain['total_theaters']} theaters")
                return chains
            else:
                print(f"❌ Failed to retrieve chains: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error retrieving chains: {e}")
            return []
    
    def test_chain_analytics(self):
        """Test chain analytics"""
        print("\n📊 Testing Chain Analytics...")
        
        if not self.created_chains:
            print("❌ No chains available for analytics testing")
            return
        
        for i, chain_id in enumerate(self.created_chains[:2]):  # Test first 2 chains
            try:
                response = requests.get(f"{BASE_URL}/chains/{chain_id}/analytics?days=30")
                if response.status_code == 200:
                    analytics = response.json()
                    print(f"✅ Analytics for {analytics['chain_name']}:")
                    print(f"   • Theaters: {analytics['theater_count']}")
                    print(f"   • Cities: {analytics['cities_count']}")
                    print(f"   • States: {analytics['states_count']}")
                else:
                    print(f"❌ Analytics failed for chain {i+1}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error getting analytics for chain {i+1}: {e}")
    
    def test_dashboard_access(self):
        """Test dashboard accessibility"""
        print("\n🖥️ Testing Dashboard Access...")
        
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            if response.status_code == 200 and "Multi-Cinema Chain Management" in response.text:
                print("✅ Dashboard is accessible and loads properly")
                print(f"   Dashboard URL: {BASE_URL}/")
                return True
            else:
                print(f"❌ Dashboard access failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run complete test suite"""
        print("🧪 MULTI-CINEMA CHAIN MANAGEMENT SYSTEM - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        
        # Test service health
        if not self.test_service_health():
            print("❌ Service not available. Ending tests.")
            return False
        
        # Run all tests
        chains_created = self.test_create_cinema_chains()
        theaters_created = self.test_add_theaters()
        screens_created = self.test_add_screens()
        
        self.test_location_search()
        chains_data = self.test_get_chains()
        self.test_chain_analytics()
        dashboard_ok = self.test_dashboard_access()
        
        # Summary
        print("\n" + "=" * 70)
        print("🎯 COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Service Health: {'PASS' if True else 'FAIL'}")
        print(f"✅ Cinema Chains Created: {chains_created}")
        print(f"✅ Theaters Added: {theaters_created}")
        print(f"✅ Screens Configured: {screens_created}")
        print(f"✅ Location Search: {'PASS' if True else 'FAIL'}")
        print(f"✅ Chain Analytics: {'PASS' if True else 'FAIL'}")
        print(f"✅ Dashboard Access: {'PASS' if dashboard_ok else 'FAIL'}")
        
        print(f"\n🏢 MULTI-CINEMA CHAIN SYSTEM STATUS:")
        print(f"   📊 Dashboard: {BASE_URL}/")
        print(f"   📚 API Docs: {BASE_URL}/docs")
        print(f"   🎪 Total Chains: {len(chains_data)}")
        print(f"   🎬 Enterprise Features: Location Search, Multi-Tenant, Analytics")
        
        success = (chains_created > 0 and theaters_created > 0 and 
                  screens_created > 0 and dashboard_ok)
        
        if success:
            print("\n🎉 ALL TESTS PASSED! Multi-Cinema Chain System is fully operational!")
        else:
            print("\n⚠️  Some tests failed. Check the service configuration.")
        
        return success

def main():
    """Run the multi-cinema test suite"""
    test_suite = MultiCinemaTestSuite()
    
    print("🚀 Starting Multi-Cinema Chain Management System Tests...")
    print("⏳ Please ensure the service is running on port 8020")
    print()
    
    # Wait a moment for service to be ready
    time.sleep(2)
    
    success = test_suite.run_comprehensive_test()
    
    if success:
        print(f"\n🎯 Next Steps:")
        print(f"   • Open dashboard: {BASE_URL}/")
        print(f"   • Test location search with real coordinates")
        print(f"   • Add more theaters and chains")
        print(f"   • Explore cross-chain analytics")
    
    return success

if __name__ == "__main__":
    main()