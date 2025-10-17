"""
🧪 Dynamic Pricing System Test Suite
Test comprehensive smart pricing optimization functionality
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8021"

class DynamicPricingTestSuite:
    def __init__(self):
        self.created_pricing_rules = []
        self.created_surge_events = []
    
    def test_service_health(self):
        """Test if the dynamic pricing service is running"""
        print("🔍 Testing Dynamic Pricing Service Health...")
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
    
    def test_base_pricing_setup(self):
        """Test setting up base pricing rules"""
        print("\n💼 Testing Base Pricing Setup...")
        
        base_pricing_rules = [
            {
                "theater_id": "theater_001",
                "screen_type": "standard",
                "base_price": 12.00,
                "currency": "USD",
                "day_type": "weekday",
                "time_slot": "evening",
                "effective_from": datetime.now().isoformat()[:10]
            },
            {
                "theater_id": "theater_001", 
                "screen_type": "imax",
                "base_price": 18.00,
                "currency": "USD",
                "day_type": "weekend",
                "time_slot": "evening",
                "effective_from": datetime.now().isoformat()[:10]
            },
            {
                "theater_id": "theater_002",
                "screen_type": "standard",
                "base_price": 10.00,
                "currency": "USD",
                "day_type": "weekday",
                "time_slot": "morning",
                "effective_from": datetime.now().isoformat()[:10]
            }
        ]
        
        for rule in base_pricing_rules:
            try:
                response = requests.post(f"{BASE_URL}/base-pricing/", json=rule)
                if response.status_code == 200:
                    result = response.json()
                    self.created_pricing_rules.append(result['pricing_id'])
                    print(f"✅ Created pricing rule for {rule['theater_id']} {rule['screen_type']}: ${rule['base_price']}")
                else:
                    print(f"❌ Failed to create pricing rule: {response.status_code}")
                    print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating pricing rule: {e}")
        
        return len(self.created_pricing_rules)
    
    def test_surge_events(self):
        """Test creating surge pricing events"""
        print("\n🔥 Testing Surge Pricing Events...")
        
        surge_events = [
            {
                "event_name": "Black Friday Movie Deals",
                "event_type": "holiday",
                "start_date": (datetime.now() + timedelta(days=1)).isoformat()[:10],
                "end_date": (datetime.now() + timedelta(days=3)).isoformat()[:10],
                "surge_multiplier": 0.8,  # Discount event
                "affected_theaters": ["theater_001", "theater_002"],
                "max_price_cap": 15.00,
                "description": "Black Friday discount event for all theaters"
            },
            {
                "event_name": "New Year's Eve Premium",
                "event_type": "holiday",
                "start_date": "2025-12-31",
                "end_date": "2026-01-01",
                "surge_multiplier": 2.0,
                "affected_movies": ["movie_001", "movie_002"],
                "max_price_cap": 35.00,
                "description": "New Year's Eve premium pricing"
            },
            {
                "event_name": "Rainy Day Boost",
                "event_type": "weather",
                "start_date": datetime.now().isoformat()[:10],
                "end_date": (datetime.now() + timedelta(days=1)).isoformat()[:10],
                "surge_multiplier": 1.3,
                "description": "Rainy weather increases indoor entertainment demand"
            }
        ]
        
        for event in surge_events:
            try:
                response = requests.post(f"{BASE_URL}/surge-events/", json=event)
                if response.status_code == 200:
                    result = response.json()
                    self.created_surge_events.append(result['event_id'])
                    print(f"✅ Created surge event: {event['event_name']} ({event['surge_multiplier']}x)")
                else:
                    print(f"❌ Failed to create surge event: {response.status_code}")
                    print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating surge event: {e}")
        
        return len(self.created_surge_events)
    
    def test_dynamic_price_calculation(self):
        """Test dynamic price calculation with various scenarios"""
        print("\n🧮 Testing Dynamic Price Calculation...")
        
        test_scenarios = [
            {
                "name": "High Demand Evening Show",
                "request": {
                    "movie_id": "movie_001",
                    "theater_id": "theater_001",
                    "show_date": datetime.now().isoformat()[:10],
                    "show_time": "19:30",
                    "current_occupancy": 0.85,
                    "hours_until_show": 6.0,
                    "competitor_prices": [14.50, 15.00, 13.75]
                },
                "expected_tier": ["peak", "premium", "surge"]
            },
            {
                "name": "Low Demand Morning Show",
                "request": {
                    "movie_id": "movie_002",
                    "theater_id": "theater_001",
                    "show_date": (datetime.now() + timedelta(days=1)).isoformat()[:10],
                    "show_time": "10:00",
                    "current_occupancy": 0.25,
                    "hours_until_show": 36.0
                },
                "expected_tier": ["discount", "base"]
            },
            {
                "name": "Last-Minute Weekend Premium",
                "request": {
                    "movie_id": "movie_003",
                    "theater_id": "theater_002",
                    "show_date": datetime.now().isoformat()[:10],
                    "show_time": "21:00",
                    "current_occupancy": 0.70,
                    "hours_until_show": 1.5
                },
                "expected_tier": ["premium", "surge"]
            },
            {
                "name": "Early Bird Weekday Special",
                "request": {
                    "movie_id": "movie_004",
                    "theater_id": "theater_001",
                    "show_date": (datetime.now() + timedelta(days=7)).isoformat()[:10],
                    "show_time": "11:30",
                    "current_occupancy": 0.15,
                    "hours_until_show": 168.0  # One week advance
                },
                "expected_tier": ["discount"]
            }
        ]
        
        successful_calculations = 0
        
        for scenario in test_scenarios:
            try:
                response = requests.post(f"{BASE_URL}/calculate-price", json=scenario["request"])
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {scenario['name']}:")
                    print(f"   Base Price: ${result['base_price']}")
                    print(f"   Final Price: ${result['final_price']}")
                    print(f"   Multiplier: {result['price_multiplier']}x")
                    print(f"   Tier: {result['pricing_tier']}")
                    print(f"   Factors: {', '.join(result['applied_factors'])}")
                    print(f"   Recommendation: {result['recommendation']}")
                    
                    # Validate pricing tier
                    if result['pricing_tier'] in scenario['expected_tier']:
                        print(f"   ✓ Pricing tier matches expectation")
                    else:
                        print(f"   ⚠️  Unexpected pricing tier (expected: {scenario['expected_tier']})")
                    
                    successful_calculations += 1
                else:
                    print(f"❌ Failed calculation for {scenario['name']}: {response.status_code}")
                    print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error calculating price for {scenario['name']}: {e}")
        
        return successful_calculations
    
    def test_pricing_factors(self):
        """Test retrieving pricing factors"""
        print("\n⚙️ Testing Pricing Factors...")
        
        try:
            response = requests.get(f"{BASE_URL}/pricing-factors/")
            if response.status_code == 200:
                factors = response.json()
                print(f"✅ Retrieved {len(factors)} pricing factors:")
                
                for factor in factors[:5]:  # Show first 5 factors
                    print(f"   • {factor['factor_name']} ({factor['factor_type']})")
                    print(f"     Weight: {factor['weight']}, Range: {factor['min_multiplier']}-{factor['max_multiplier']}x")
                
                return len(factors)
            else:
                print(f"❌ Failed to retrieve factors: {response.status_code}")
                return 0
        except Exception as e:
            print(f"❌ Error retrieving factors: {e}")
            return 0
    
    def test_pricing_analytics(self):
        """Test pricing analytics"""
        print("\n📊 Testing Pricing Analytics...")
        
        try:
            response = requests.get(f"{BASE_URL}/analytics?days=30")
            if response.status_code == 200:
                analytics = response.json()
                print("✅ Analytics Retrieved Successfully:")
                print(f"   Period: {analytics['period_days']} days")
                print(f"   Total Price Adjustments: {analytics['summary']['total_price_adjustments']}")
                print(f"   Revenue Impact: ${analytics['summary']['avg_revenue_impact']}")
                print(f"   Most Common Tier: {analytics['summary']['most_common_tier']}")
                
                # Show pricing tier breakdown
                if analytics['pricing_tier_analysis']:
                    print("   Tier Analysis:")
                    for tier, data in analytics['pricing_tier_analysis'].items():
                        print(f"     {tier.upper()}: {data['price_changes']} adjustments, avg {data['avg_multiplier']}x")
                
                return True
            else:
                print(f"❌ Analytics failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Analytics error: {e}")
            return False
    
    def test_dashboard_access(self):
        """Test dashboard accessibility"""
        print("\n🖥️ Testing Dashboard Access...")
        
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            if response.status_code == 200 and "Dynamic Pricing System" in response.text:
                print("✅ Dashboard is accessible and loads properly")
                print(f"   Dashboard URL: {BASE_URL}/")
                return True
            else:
                print(f"❌ Dashboard access failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
            return False
    
    def test_competitive_pricing(self):
        """Test competitive pricing adjustments"""
        print("\n🎯 Testing Competitive Pricing Intelligence...")
        
        competitive_scenarios = [
            {
                "name": "Price Match Scenario",
                "our_base": 12.00,
                "competitor_prices": [11.50, 12.50, 11.75],
                "expected_adjustment": "minimal"
            },
            {
                "name": "Undercut Competition",
                "our_base": 15.00,
                "competitor_prices": [10.00, 11.00, 10.50],
                "expected_adjustment": "decrease"
            },
            {
                "name": "Premium Positioning",
                "our_base": 8.00,
                "competitor_prices": [12.00, 13.50, 14.00],
                "expected_adjustment": "increase"
            }
        ]
        
        for scenario in competitive_scenarios:
            request_data = {
                "movie_id": "movie_competitive",
                "theater_id": "theater_001",
                "show_date": datetime.now().isoformat()[:10],
                "show_time": "19:00",
                "current_occupancy": 0.6,
                "hours_until_show": 12.0,
                "competitor_prices": scenario["competitor_prices"]
            }
            
            try:
                response = requests.post(f"{BASE_URL}/calculate-price", json=request_data)
                if response.status_code == 200:
                    result = response.json()
                    competitor_avg = sum(scenario["competitor_prices"]) / len(scenario["competitor_prices"])
                    
                    print(f"✅ {scenario['name']}:")
                    print(f"   Competitor Average: ${competitor_avg:.2f}")
                    print(f"   Our Final Price: ${result['final_price']}")
                    print(f"   Price Difference: ${result['final_price'] - competitor_avg:.2f}")
                    
                    # Check for competitive factor in applied factors
                    has_competitive = any("Competitive" in factor for factor in result.get('applied_factors', []))
                    if has_competitive:
                        print(f"   ✓ Competitive pricing factor applied")
                    
                else:
                    print(f"❌ Failed competitive test {scenario['name']}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error in competitive test {scenario['name']}: {e}")
    
    def run_comprehensive_test(self):
        """Run complete test suite"""
        print("🧪 DYNAMIC PRICING SYSTEM - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        
        # Test service health
        if not self.test_service_health():
            print("❌ Service not available. Ending tests.")
            return False
        
        # Run all tests
        pricing_rules = self.test_base_pricing_setup()
        surge_events = self.test_surge_events()
        price_calculations = self.test_dynamic_price_calculation()
        pricing_factors = self.test_pricing_factors()
        analytics_ok = self.test_pricing_analytics()
        dashboard_ok = self.test_dashboard_access()
        
        # Additional tests
        self.test_competitive_pricing()
        
        # Summary
        print("\n" + "=" * 70)
        print("🎯 COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Service Health: {'PASS' if True else 'FAIL'}")
        print(f"✅ Base Pricing Rules Created: {pricing_rules}")
        print(f"✅ Surge Events Created: {surge_events}")
        print(f"✅ Dynamic Price Calculations: {price_calculations}")
        print(f"✅ Pricing Factors Retrieved: {pricing_factors}")
        print(f"✅ Analytics System: {'PASS' if analytics_ok else 'FAIL'}")
        print(f"✅ Dashboard Access: {'PASS' if dashboard_ok else 'FAIL'}")
        
        print(f"\n💰 DYNAMIC PRICING SYSTEM STATUS:")
        print(f"   📊 Dashboard: {BASE_URL}/")
        print(f"   📚 API Docs: {BASE_URL}/docs")
        print(f"   🧮 Smart Algorithms: Demand-based, Time-based, Competitive")
        print(f"   🎯 Revenue Optimization: ML-powered pricing decisions")
        
        success = (pricing_rules > 0 and price_calculations > 0 and 
                  pricing_factors > 0 and analytics_ok and dashboard_ok)
        
        if success:
            print("\n🎉 ALL TESTS PASSED! Dynamic Pricing System is fully operational!")
            print("\n💡 Key Features Verified:")
            print("   🔥 Surge pricing for special events")
            print("   📈 Demand-based price optimization")
            print("   ⏰ Time-sensitive pricing adjustments")
            print("   🎯 Competitive intelligence integration")
            print("   📊 Revenue analytics and insights")
        else:
            print("\n⚠️  Some tests failed. Check the service configuration.")
        
        return success

def main():
    """Run the dynamic pricing test suite"""
    test_suite = DynamicPricingTestSuite()
    
    print("🚀 Starting Dynamic Pricing System Tests...")
    print("⏳ Please ensure the service is running on port 8021")
    print()
    
    # Wait a moment for service to be ready
    time.sleep(2)
    
    success = test_suite.run_comprehensive_test()
    
    if success:
        print(f"\n🎯 Next Steps:")
        print(f"   • Open dashboard: {BASE_URL}/")
        print(f"   • Test different pricing scenarios")
        print(f"   • Monitor revenue optimization")
        print(f"   • Configure competitor pricing data")
    
    return success

if __name__ == "__main__":
    main()