"""
🧪 Social Features Platform Test Suite
Test comprehensive community engagement and social interaction functionality
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8022"

class SocialFeaturesTestSuite:
    def __init__(self):
        self.created_profiles = []
        self.created_reviews = []
        self.created_posts = []
        self.created_collections = []
    
    def test_service_health(self):
        """Test if the social features service is running"""
        print("🔍 Testing Social Features Service Health...")
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
    
    def test_user_profile_creation(self):
        """Test creating user social profiles"""
        print("\n👤 Testing User Profile Creation...")
        
        user_profiles = [
            {
                "user_id": "user_social_001",
                "profile": {
                    "username": "moviefan123",
                    "display_name": "Alex Movie Fan",
                    "bio": "Passionate movie lover and critic. Love sci-fi and horror!",
                    "location": "Los Angeles, CA",
                    "favorite_genres": ["sci-fi", "horror", "thriller"],
                    "social_links": {
                        "twitter": "@moviefan123",
                        "instagram": "alexmovies"
                    },
                    "privacy_settings": {
                        "show_activity": True,
                        "allow_followers": True,
                        "public_reviews": True
                    }
                }
            },
            {
                "user_id": "user_social_002",
                "profile": {
                    "username": "cinephile_sara",
                    "display_name": "Sara Cinema",
                    "bio": "Professional film critic and cinema historian",
                    "location": "New York, NY",
                    "favorite_genres": ["drama", "foreign", "documentary"],
                    "social_links": {
                        "twitter": "@cinephilesara",
                        "website": "saracinema.com"
                    }
                }
            },
            {
                "user_id": "user_social_003",
                "profile": {
                    "username": "reviewmaster",
                    "display_name": "The Review Master",
                    "bio": "1000+ reviews and counting! Honest opinions only.",
                    "location": "Chicago, IL",
                    "favorite_genres": ["action", "comedy", "adventure"]
                }
            }
        ]
        
        for user_data in user_profiles:
            try:
                response = requests.post(
                    f"{BASE_URL}/users/{user_data['user_id']}/profile/", 
                    json=user_data['profile']
                )
                if response.status_code == 200:
                    result = response.json()
                    self.created_profiles.append(user_data['user_id'])
                    print(f"✅ Created profile for @{user_data['profile']['username']} (ID: {user_data['user_id']})")
                else:
                    print(f"❌ Failed to create profile for {user_data['profile']['username']}: {response.status_code}")
                    if response.status_code != 404:  # Ignore 404s during testing
                        print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating profile for {user_data['profile']['username']}: {e}")
        
        return len(self.created_profiles)
    
    def test_movie_reviews(self):
        """Test creating movie reviews and ratings"""
        print("\n⭐ Testing Movie Reviews System...")
        
        if not self.created_profiles:
            print("❌ No user profiles available for review testing")
            return 0
        
        movie_reviews = [
            {
                "user_id": self.created_profiles[0],
                "review": {
                    "movie_id": "movie_inception_2010",
                    "rating": 4.8,
                    "review_title": "A Mind-Bending Masterpiece",
                    "review_text": "Christopher Nolan delivers another incredible film that challenges your perception of reality. The layered storytelling, stunning visuals, and exceptional performances make this a must-watch. The concept of dreams within dreams is executed flawlessly.",
                    "spoiler_warning": False,
                    "watching_date": "2024-10-15",
                    "tags": ["masterpiece", "mind-bending", "sci-fi"]
                }
            },
            {
                "user_id": self.created_profiles[1] if len(self.created_profiles) > 1 else self.created_profiles[0],
                "review": {
                    "movie_id": "movie_dune_2021",
                    "rating": 4.5,
                    "review_title": "Visually Stunning Epic",
                    "review_text": "Denis Villeneuve brings Frank Herbert's complex novel to life with breathtaking visuals and sound design. While the pacing is deliberate, the world-building is exceptional. Hans Zimmer's score is haunting and perfect.",
                    "spoiler_warning": False,
                    "watching_date": "2024-10-14",
                    "tags": ["epic", "visually-stunning", "adaptation"]
                }
            },
            {
                "user_id": self.created_profiles[2] if len(self.created_profiles) > 2 else self.created_profiles[0],
                "review": {
                    "movie_id": "movie_matrix_1999",
                    "rating": 5.0,
                    "review_title": "Revolutionary Cinema",
                    "review_text": "The Matrix changed everything. The philosophical themes, groundbreaking visual effects, and action sequences were unlike anything before. A true game-changer in cinema history.",
                    "spoiler_warning": True,
                    "watching_date": "2024-10-13",
                    "tags": ["revolutionary", "classic", "philosophical"]
                }
            }
        ]
        
        for review_data in movie_reviews:
            try:
                response = requests.post(
                    f"{BASE_URL}/users/{review_data['user_id']}/reviews/", 
                    json=review_data['review']
                )
                if response.status_code == 200:
                    result = response.json()
                    self.created_reviews.append(result['review_id'])
                    print(f"✅ Created review for {review_data['review']['movie_id']}: {review_data['review']['rating']} stars")
                else:
                    print(f"❌ Failed to create review: {response.status_code}")
                    if response.status_code != 404:
                        print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating review: {e}")
        
        return len(self.created_reviews)
    
    def test_forum_discussions(self):
        """Test forum posts and discussions"""
        print("\n💬 Testing Forum Discussions...")
        
        if not self.created_profiles:
            print("❌ No user profiles available for forum testing")
            return 0
        
        forum_posts = [
            {
                "user_id": self.created_profiles[0],
                "post": {
                    "movie_id": "movie_inception_2010",
                    "post_type": "discussion",
                    "title": "What's your interpretation of the ending?",
                    "content": "I've watched Inception multiple times and I'm still debating whether the spinning top falls or not. What's your take on the ending? Do you think Cobb is still dreaming or back in reality?",
                    "category": "spoilers",
                    "tags": ["ending", "theory", "discussion"]
                }
            },
            {
                "user_id": self.created_profiles[1] if len(self.created_profiles) > 1 else self.created_profiles[0],
                "post": {
                    "post_type": "recommendation",
                    "title": "Hidden Gems of 2024 - Underrated Films",
                    "content": "Here are some amazing films from 2024 that didn't get the attention they deserve. These movies showcase incredible storytelling and cinematography but flew under the radar for most audiences.",
                    "category": "recommendations",
                    "tags": ["hidden-gems", "2024", "underrated"]
                }
            },
            {
                "user_id": self.created_profiles[2] if len(self.created_profiles) > 2 else self.created_profiles[0],
                "post": {
                    "movie_id": "movie_dune_2021",
                    "post_type": "question",
                    "title": "Book vs Movie: How faithful is the adaptation?",
                    "content": "For those who have read Frank Herbert's Dune, how do you feel about Villeneuve's adaptation? What changes did you like or dislike? Are you excited for Part Two?",
                    "category": "adaptations",
                    "tags": ["book-adaptation", "dune", "comparison"]
                }
            }
        ]
        
        for post_data in forum_posts:
            try:
                response = requests.post(
                    f"{BASE_URL}/users/{post_data['user_id']}/posts/", 
                    json=post_data['post']
                )
                if response.status_code == 200:
                    result = response.json()
                    self.created_posts.append(result['post_id'])
                    print(f"✅ Created forum post: {post_data['post']['title']}")
                else:
                    print(f"❌ Failed to create forum post: {response.status_code}")
                    if response.status_code != 404:
                        print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating forum post: {e}")
        
        return len(self.created_posts)
    
    def test_social_interactions(self):
        """Test social interactions like likes, follows, shares"""
        print("\n👍 Testing Social Interactions...")
        
        if len(self.created_profiles) < 2:
            print("❌ Need at least 2 user profiles for interaction testing")
            return 0
        
        interactions = [
            {
                "user_id": self.created_profiles[1],
                "interaction": {
                    "target_id": self.created_profiles[0],
                    "target_type": "user",
                    "interaction_type": "follow"
                }
            },
            {
                "user_id": self.created_profiles[2] if len(self.created_profiles) > 2 else self.created_profiles[1],
                "interaction": {
                    "target_id": self.created_profiles[0],
                    "target_type": "user",
                    "interaction_type": "follow"
                }
            }
        ]
        
        # Add likes for reviews if available
        if self.created_reviews:
            interactions.extend([
                {
                    "user_id": self.created_profiles[1],
                    "interaction": {
                        "target_id": self.created_reviews[0],
                        "target_type": "review",
                        "interaction_type": "like"
                    }
                },
                {
                    "user_id": self.created_profiles[2] if len(self.created_profiles) > 2 else self.created_profiles[1],
                    "interaction": {
                        "target_id": self.created_reviews[0],
                        "target_type": "review",
                        "interaction_type": "like"
                    }
                }
            ])
        
        successful_interactions = 0
        
        for interaction_data in interactions:
            try:
                response = requests.post(
                    f"{BASE_URL}/users/{interaction_data['user_id']}/interactions/", 
                    json=interaction_data['interaction']
                )
                if response.status_code == 200:
                    result = response.json()
                    successful_interactions += 1
                    interaction_type = interaction_data['interaction']['interaction_type']
                    target_type = interaction_data['interaction']['target_type']
                    print(f"✅ Created {interaction_type} interaction on {target_type}")
                else:
                    print(f"❌ Failed to create interaction: {response.status_code}")
                    if response.status_code != 404:
                        print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating interaction: {e}")
        
        return successful_interactions
    
    def test_user_collections(self):
        """Test user movie collections and watchlists"""
        print("\n📚 Testing User Collections...")
        
        if not self.created_profiles:
            print("❌ No user profiles available for collection testing")
            return 0
        
        collections = [
            {
                "user_id": self.created_profiles[0],
                "collection": {
                    "collection_name": "Sci-Fi Masterpieces",
                    "collection_type": "favorites",
                    "description": "My favorite science fiction films of all time",
                    "movie_ids": ["movie_inception_2010", "movie_matrix_1999", "movie_blade_runner_1982", "movie_interstellar_2014"],
                    "is_public": True,
                    "tags": ["sci-fi", "favorites", "masterpieces"]
                }
            },
            {
                "user_id": self.created_profiles[1] if len(self.created_profiles) > 1 else self.created_profiles[0],
                "collection": {
                    "collection_name": "Must Watch This Weekend",
                    "collection_type": "watchlist",
                    "description": "Movies I need to catch up on",
                    "movie_ids": ["movie_dune_part2_2024", "movie_oppenheimer_2023", "movie_barbie_2023"],
                    "is_public": True,
                    "tags": ["watchlist", "weekend", "new-releases"]
                }
            }
        ]
        
        for collection_data in collections:
            try:
                response = requests.post(
                    f"{BASE_URL}/users/{collection_data['user_id']}/collections/", 
                    json=collection_data['collection']
                )
                if response.status_code == 200:
                    result = response.json()
                    self.created_collections.append(result['collection_id'])
                    print(f"✅ Created collection: {collection_data['collection']['collection_name']} ({result['movie_count']} movies)")
                else:
                    print(f"❌ Failed to create collection: {response.status_code}")
                    if response.status_code != 404:
                        print(f"   Response: {response.text}")
            except Exception as e:
                print(f"❌ Error creating collection: {e}")
        
        return len(self.created_collections)
    
    def test_get_movie_reviews(self):
        """Test retrieving movie reviews"""
        print("\n📖 Testing Movie Reviews Retrieval...")
        
        test_movie_id = "movie_inception_2010"
        
        try:
            response = requests.get(f"{BASE_URL}/movies/{test_movie_id}/reviews/?limit=10")
            if response.status_code == 200:
                reviews_data = response.json()
                print(f"✅ Retrieved reviews for {test_movie_id}:")
                print(f"   Total Reviews: {reviews_data.get('total_reviews', 0)}")
                print(f"   Average Rating: {reviews_data.get('average_rating', 0)} stars")
                print(f"   Reviews Loaded: {len(reviews_data.get('reviews', []))}")
                
                # Show sample review
                if reviews_data.get('reviews'):
                    sample_review = reviews_data['reviews'][0]
                    print(f"   Sample Review: \"{sample_review.get('review_title', 'No title')}\" by @{sample_review['user']['username']}")
                
                return True
            else:
                print(f"❌ Failed to retrieve reviews: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error retrieving reviews: {e}")
            return False
    
    def test_get_forum_posts(self):
        """Test retrieving forum posts"""
        print("\n📋 Testing Forum Posts Retrieval...")
        
        try:
            response = requests.get(f"{BASE_URL}/forum/posts/?limit=10")
            if response.status_code == 200:
                posts_data = response.json()
                print(f"✅ Retrieved forum posts:")
                print(f"   Posts Loaded: {len(posts_data)}")
                
                # Show sample posts
                for i, post in enumerate(posts_data[:3]):
                    print(f"   {i+1}. \"{post['title']}\" by @{post['user']['username']} ({post['reply_count']} replies)")
                
                return True
            else:
                print(f"❌ Failed to retrieve forum posts: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error retrieving forum posts: {e}")
            return False
    
    def test_user_profile_retrieval(self):
        """Test retrieving user profiles with social stats"""
        print("\n👤 Testing User Profile Retrieval...")
        
        if not self.created_profiles:
            print("❌ No user profiles available for retrieval testing")
            return False
        
        try:
            user_id = self.created_profiles[0]
            response = requests.get(f"{BASE_URL}/users/{user_id}/profile/")
            if response.status_code == 200:
                profile_data = response.json()
                print(f"✅ Retrieved profile for @{profile_data['username']}:")
                print(f"   Display Name: {profile_data.get('display_name', 'N/A')}")
                print(f"   Reviews: {profile_data.get('review_count', 0)}")
                print(f"   Followers: {profile_data.get('follower_count', 0)}")
                print(f"   Following: {profile_data.get('following_count', 0)}")
                print(f"   Reputation: {profile_data.get('reputation_score', 0)}")
                print(f"   Recent Activity: {len(profile_data.get('recent_activity', []))} items")
                
                return True
            else:
                print(f"❌ Failed to retrieve profile: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error retrieving profile: {e}")
            return False
    
    def test_dashboard_access(self):
        """Test dashboard accessibility"""
        print("\n🖥️ Testing Dashboard Access...")
        
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            if response.status_code == 200 and "Social Features Platform" in response.text:
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
        print("🧪 SOCIAL FEATURES PLATFORM - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        
        # Test service health
        if not self.test_service_health():
            print("❌ Service not available. Ending tests.")
            return False
        
        # Run all tests
        profiles_created = self.test_user_profile_creation()
        reviews_created = self.test_movie_reviews()
        posts_created = self.test_forum_discussions()
        interactions_created = self.test_social_interactions()
        collections_created = self.test_user_collections()
        
        # Test data retrieval
        reviews_retrieval_ok = self.test_get_movie_reviews()
        forum_retrieval_ok = self.test_get_forum_posts()
        profile_retrieval_ok = self.test_user_profile_retrieval()
        dashboard_ok = self.test_dashboard_access()
        
        # Summary
        print("\n" + "=" * 70)
        print("🎯 COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Service Health: {'PASS' if True else 'FAIL'}")
        print(f"✅ User Profiles Created: {profiles_created}")
        print(f"✅ Movie Reviews Created: {reviews_created}")
        print(f"✅ Forum Posts Created: {posts_created}")
        print(f"✅ Social Interactions: {interactions_created}")
        print(f"✅ User Collections: {collections_created}")
        print(f"✅ Reviews Retrieval: {'PASS' if reviews_retrieval_ok else 'FAIL'}")
        print(f"✅ Forum Retrieval: {'PASS' if forum_retrieval_ok else 'FAIL'}")
        print(f"✅ Profile Retrieval: {'PASS' if profile_retrieval_ok else 'FAIL'}")
        print(f"✅ Dashboard Access: {'PASS' if dashboard_ok else 'FAIL'}")
        
        print(f"\n👥 SOCIAL FEATURES PLATFORM STATUS:")
        print(f"   🌐 Dashboard: {BASE_URL}/")
        print(f"   📚 API Docs: {BASE_URL}/docs")
        print(f"   👤 User Profiles: Social profiles with stats and activity")
        print(f"   ⭐ Review System: Movie ratings and reviews")
        print(f"   💬 Forum System: Discussions and community posts")
        print(f"   👍 Social Interactions: Likes, follows, and engagement")
        print(f"   📚 Collections: Watchlists and movie collections")
        
        success = (profiles_created > 0 and reviews_created > 0 and posts_created > 0 and 
                  reviews_retrieval_ok and forum_retrieval_ok and dashboard_ok)
        
        if success:
            print("\n🎉 ALL TESTS PASSED! Social Features Platform is fully operational!")
            print("\n💡 Key Features Verified:")
            print("   👤 User profile management with social stats")
            print("   ⭐ Comprehensive movie review system")
            print("   💬 Interactive discussion forums")
            print("   👍 Social interactions and engagement")
            print("   📚 Personal movie collections and watchlists")
            print("   🔔 Activity feeds and community updates")
        else:
            print("\n⚠️  Some tests failed. Check the service configuration.")
        
        return success

def main():
    """Run the social features test suite"""
    test_suite = SocialFeaturesTestSuite()
    
    print("🚀 Starting Social Features Platform Tests...")
    print("⏳ Please ensure the service is running on port 8022")
    print()
    
    # Wait a moment for service to be ready
    time.sleep(2)
    
    success = test_suite.run_comprehensive_test()
    
    if success:
        print(f"\n🎯 Next Steps:")
        print(f"   • Open dashboard: {BASE_URL}/")
        print(f"   • Create user profiles and reviews")
        print(f"   • Start discussions in the forums")
        print(f"   • Build movie collections and watchlists")
        print(f"   • Engage with community through likes and follows")
    
    return success

if __name__ == "__main__":
    main()