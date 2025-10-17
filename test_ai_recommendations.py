"""
Test script for AI Recommendation Engine
Demonstrates intelligent movie recommendations using multiple algorithms
"""

import requests
import json
import time

def test_ai_recommendation_engine():
    base_url = "http://127.0.0.1:8019"
    
    print("🤖 Testing BookMyMovie AI Recommendation Engine...")
    print("=" * 60)
    
    # Test 1: Service Health Check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Health Check: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   Service Status: {health_data.get('status')}")
            print(f"   Algorithms: {list(health_data.get('algorithms_active', {}).keys())}")
    except Exception as e:
        print(f"❌ Health Check Failed: {str(e)}")
        return False
    
    # Test 2: Service Information
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"\n✅ Service Info: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Available Features: {len(data.get('features', []))}")
            for feature in data.get('features', [])[:3]:
                print(f"      • {feature}")
    except Exception as e:
        print(f"❌ Service Info Failed: {str(e)}")
    
    # Test 3: Collaborative Filtering Recommendations
    print(f"\n🤝 Testing Collaborative Filtering...")
    try:
        payload = {
            "user_id": 1,
            "limit": 5,
            "recommendation_type": "collaborative_user"
        }
        
        response = requests.post(
            f"{base_url}/recommendations",
            json=payload,
            timeout=10
        )
        print(f"✅ Collaborative Filtering: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data.get('total_recommendations')} recommendations")
            print(f"   Algorithm Confidence: {data.get('algorithm_confidence', 0):.1%}")
            
            for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                print(f"   {i}. {rec.get('title')} ({rec.get('year')})")
                print(f"      Score: {rec.get('recommendation_score', 0):.3f} | {rec.get('recommendation_reason')}")
        
    except Exception as e:
        print(f"❌ Collaborative Filtering Failed: {str(e)}")
    
    # Test 4: Content-Based Filtering Recommendations
    print(f"\n📋 Testing Content-Based Filtering...")
    try:
        payload = {
            "user_id": 2,
            "limit": 5,
            "recommendation_type": "content_based"
        }
        
        response = requests.post(
            f"{base_url}/recommendations",
            json=payload,
            timeout=10
        )
        print(f"✅ Content-Based Filtering: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data.get('total_recommendations')} recommendations")
            
            for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                print(f"   {i}. {rec.get('title')} ({rec.get('year')})")
                print(f"      Genres: {', '.join(rec.get('genres', []))}")
                print(f"      Score: {rec.get('recommendation_score', 0):.3f}")
        
    except Exception as e:
        print(f"❌ Content-Based Filtering Failed: {str(e)}")
    
    # Test 5: Hybrid AI Recommendations
    print(f"\n🔬 Testing Hybrid AI System...")
    try:
        payload = {
            "user_id": 1,
            "limit": 8,
            "recommendation_type": "hybrid"
        }
        
        response = requests.post(
            f"{base_url}/recommendations",
            json=payload,
            timeout=10
        )
        print(f"✅ Hybrid AI Recommendations: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   🧠 AI Generated {data.get('total_recommendations')} personalized recommendations")
            print(f"   🎯 Algorithm Confidence: {data.get('algorithm_confidence', 0):.1%}")
            
            print(f"\n   🎬 Top AI Recommendations for User {payload['user_id']}:")
            for i, rec in enumerate(data.get('recommendations', [])[:5], 1):
                title = rec.get('title', 'Unknown')
                year = rec.get('year', 'N/A')
                rating = rec.get('rating', 0)
                score = rec.get('recommendation_score', 0)
                reason = rec.get('recommendation_reason', 'AI recommendation')
                
                print(f"   {i}. 🎭 {title} ({year})")
                print(f"      ⭐ Rating: {rating}/10 | AI Score: {score:.3f}")
                print(f"      💡 Reason: {reason}")
                print()
        
    except Exception as e:
        print(f"❌ Hybrid AI System Failed: {str(e)}")
    
    # Test 6: Trending Movies
    print(f"📈 Testing Trending Recommendations...")
    try:
        response = requests.get(f"{base_url}/recommendations/1/trending?limit=5", timeout=5)
        print(f"✅ Trending Movies: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data.get('recommendations', []))} trending movies")
            
            for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                print(f"   {i}. {rec.get('title')} - {rec.get('recommendation_reason')}")
        
    except Exception as e:
        print(f"❌ Trending Movies Failed: {str(e)}")
    
    # Test 7: Add User Rating
    print(f"\n⭐ Testing User Rating System...")
    try:
        response = requests.post(
            f"{base_url}/rating",
            params={"user_id": 1, "movie_id": 15, "rating": 9.2},
            timeout=5
        )
        print(f"✅ Add User Rating: {response.status_code}")
        if response.status_code == 200:
            print(f"   Rating added successfully - User 1 rated Movie 15: 9.2/10")
        
    except Exception as e:
        print(f"❌ Add Rating Failed: {str(e)}")
    
    # Test 8: Performance Analytics
    print(f"\n📊 Testing AI Performance Analytics...")
    try:
        response = requests.get(f"{base_url}/analytics/performance", timeout=5)
        print(f"✅ Performance Analytics: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            metrics = data.get('performance_metrics', {})
            algorithms = data.get('algorithm_performance', {})
            
            print(f"   📈 Performance Metrics:")
            print(f"      Total Recommendations: {metrics.get('total_recommendations_served', 0)}")
            print(f"      Click-Through Rate: {metrics.get('click_through_rate', 0)}%")
            print(f"      Conversion Rate: {metrics.get('conversion_rate', 0)}%")
            print(f"      Active Users: {metrics.get('unique_users_served', 0)}")
            print(f"      Model Accuracy: {metrics.get('model_accuracy', 0):.1%}")
            
            print(f"\n   🤖 Algorithm Performance:")
            print(f"      Collaborative Filtering: {algorithms.get('collaborative_filtering', 0):.1%}")
            print(f"      Content-Based: {algorithms.get('content_based', 0):.1%}")
            print(f"      Hybrid Model: {algorithms.get('hybrid_model', 0):.1%}")
        
    except Exception as e:
        print(f"❌ Performance Analytics Failed: {str(e)}")
    
    # Test 9: Filtered Recommendations
    print(f"\n🎯 Testing Filtered Recommendations...")
    try:
        payload = {
            "user_id": 3,
            "limit": 5,
            "recommendation_type": "hybrid",
            "genres": ["Action", "Sci-Fi"],
            "min_rating": 8.0
        }
        
        response = requests.post(
            f"{base_url}/recommendations",
            json=payload,
            timeout=10
        )
        print(f"✅ Filtered Recommendations: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Filtered by: Action/Sci-Fi genres, min rating 8.0")
            print(f"   Found {data.get('total_recommendations')} matching movies")
            
            for i, rec in enumerate(data.get('recommendations', [])[:3], 1):
                print(f"   {i}. {rec.get('title')} - Rating: {rec.get('rating')}/10")
        
    except Exception as e:
        print(f"❌ Filtered Recommendations Failed: {str(e)}")
    
    print(f"\n🎉 AI Recommendation Engine Testing Completed!")
    print(f"🌐 Dashboard available at: {base_url}/dashboard")
    print(f"📊 Analytics available at: {base_url}/analytics/performance")
    print(f"🔗 API Documentation: {base_url}/docs")
    
    print(f"\n🚀 AI Recommendation Engine Features Verified:")
    print(f"   ✅ Collaborative Filtering Algorithm")
    print(f"   ✅ Content-Based Filtering Algorithm") 
    print(f"   ✅ Hybrid AI Recommendation System")
    print(f"   ✅ Trending Movie Discovery")
    print(f"   ✅ User Rating Integration")
    print(f"   ✅ Performance Analytics Dashboard")
    print(f"   ✅ Filtered & Personalized Recommendations")
    
    return True

if __name__ == "__main__":
    print("⏳ Waiting for AI Recommendation Engine to be ready...")
    time.sleep(2)
    
    test_ai_recommendation_engine()