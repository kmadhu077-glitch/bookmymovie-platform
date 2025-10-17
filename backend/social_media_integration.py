"""
Social Media Integration Service
Integration with Facebook, Twitter, Instagram, Google APIs
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os
from enum import Enum
import hashlib
import hmac
import base64
from urllib.parse import quote, urlencode

logger = logging.getLogger(__name__)

class SocialPlatform(Enum):
    """Supported social media platforms"""
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    GOOGLE = "google"
    LINKEDIN = "linkedin"

class PostType(Enum):
    """Types of social media posts"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"
    STORY = "story"

@dataclass
class SocialPost:
    """Social media post structure"""
    content: str
    post_type: PostType = PostType.TEXT
    image_url: str = None
    video_url: str = None
    link_url: str = None
    hashtags: List[str] = None
    mentions: List[str] = None
    scheduled_time: datetime = None
    platform: SocialPlatform = None

@dataclass
class SocialUser:
    """Social media user profile"""
    platform_id: str
    username: str
    display_name: str
    email: str = None
    profile_picture: str = None
    followers_count: int = 0
    following_count: int = 0
    verified: bool = False
    platform: SocialPlatform = None
    raw_data: Dict[str, Any] = None

@dataclass
class PostResult:
    """Result of social media post"""
    success: bool
    post_id: str = None
    post_url: str = None
    error_message: str = None
    platform: SocialPlatform = None
    timestamp: datetime = None

class FacebookService:
    """Facebook Graph API integration"""
    
    def __init__(self):
        self.app_id = os.getenv('FACEBOOK_APP_ID')
        self.app_secret = os.getenv('FACEBOOK_APP_SECRET')
        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.page_id = os.getenv('FACEBOOK_PAGE_ID')
        self.base_url = "https://graph.facebook.com/v18.0"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def post_to_page(self, post: SocialPost) -> PostResult:
        """Post content to Facebook page"""
        try:
            if not self.page_id or not self.access_token:
                return PostResult(
                    success=False,
                    error_message="Facebook credentials not configured",
                    platform=SocialPlatform.FACEBOOK,
                    timestamp=datetime.now()
                )
            
            # Build post data
            post_data = {
                'message': post.content,
                'access_token': self.access_token
            }
            
            # Add media if provided
            if post.image_url and post.post_type == PostType.IMAGE:
                post_data['link'] = post.image_url
            elif post.link_url and post.post_type == PostType.LINK:
                post_data['link'] = post.link_url
            
            # Add hashtags to message
            if post.hashtags:
                hashtag_string = ' '.join([f'#{tag}' for tag in post.hashtags])
                post_data['message'] += f'\n\n{hashtag_string}'
            
            async with self.session.post(f"{self.base_url}/{self.page_id}/feed", data=post_data) as response:
                if response.status == 200:
                    result = await response.json()
                    post_id = result.get('id')
                    
                    return PostResult(
                        success=True,
                        post_id=post_id,
                        post_url=f"https://facebook.com/{post_id}",
                        platform=SocialPlatform.FACEBOOK,
                        timestamp=datetime.now()
                    )
                else:
                    error_data = await response.json()
                    return PostResult(
                        success=False,
                        error_message=error_data.get('error', {}).get('message', 'Facebook API error'),
                        platform=SocialPlatform.FACEBOOK,
                        timestamp=datetime.now()
                    )
        
        except Exception as e:
            logger.error(f"Facebook post failed: {e}")
            return PostResult(
                success=False,
                error_message=str(e),
                platform=SocialPlatform.FACEBOOK,
                timestamp=datetime.now()
            )
    
    async def get_page_insights(self, metrics: List[str] = None) -> Dict[str, Any]:
        """Get Facebook page insights"""
        try:
            default_metrics = [
                'page_impressions',
                'page_engaged_users',
                'page_post_engagements',
                'page_fans'
            ]
            
            metrics = metrics or default_metrics
            
            params = {
                'metric': ','.join(metrics),
                'access_token': self.access_token,
                'period': 'day'
            }
            
            async with self.session.get(f"{self.base_url}/{self.page_id}/insights", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get Facebook insights: {response.status}")
                    return {}
        
        except Exception as e:
            logger.error(f"Failed to get Facebook insights: {e}")
            return {}
    
    async def get_user_profile(self, user_access_token: str) -> Optional[SocialUser]:
        """Get user profile from Facebook"""
        try:
            params = {
                'fields': 'id,name,email,picture',
                'access_token': user_access_token
            }
            
            async with self.session.get(f"{self.base_url}/me", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return SocialUser(
                        platform_id=data.get('id'),
                        username=data.get('id'),  # Facebook doesn't have usernames
                        display_name=data.get('name'),
                        email=data.get('email'),
                        profile_picture=data.get('picture', {}).get('data', {}).get('url'),
                        platform=SocialPlatform.FACEBOOK,
                        raw_data=data
                    )
                
            return None
        
        except Exception as e:
            logger.error(f"Failed to get Facebook user profile: {e}")
            return None

class TwitterService:
    """Twitter API v2 integration"""
    
    def __init__(self):
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.base_url = "https://api.twitter.com/2"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def post_tweet(self, post: SocialPost) -> PostResult:
        """Post tweet to Twitter"""
        try:
            if not self.bearer_token:
                return PostResult(
                    success=False,
                    error_message="Twitter credentials not configured",
                    platform=SocialPlatform.TWITTER,
                    timestamp=datetime.now()
                )
            
            # Prepare tweet text
            tweet_text = post.content
            
            # Add hashtags
            if post.hashtags:
                hashtag_string = ' '.join([f'#{tag}' for tag in post.hashtags])
                tweet_text += f'\n{hashtag_string}'
            
            # Add link if provided
            if post.link_url:
                tweet_text += f'\n{post.link_url}'
            
            # Ensure tweet doesn't exceed character limit
            if len(tweet_text) > 280:
                tweet_text = tweet_text[:277] + '...'
            
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json'
            }
            
            tweet_data = {
                'text': tweet_text
            }
            
            async with self.session.post(f"{self.base_url}/tweets", headers=headers, json=tweet_data) as response:
                if response.status == 201:
                    result = await response.json()
                    tweet_id = result.get('data', {}).get('id')
                    
                    return PostResult(
                        success=True,
                        post_id=tweet_id,
                        post_url=f"https://twitter.com/user/status/{tweet_id}",
                        platform=SocialPlatform.TWITTER,
                        timestamp=datetime.now()
                    )
                else:
                    error_data = await response.json()
                    return PostResult(
                        success=False,
                        error_message=error_data.get('title', 'Twitter API error'),
                        platform=SocialPlatform.TWITTER,
                        timestamp=datetime.now()
                    )
        
        except Exception as e:
            logger.error(f"Twitter post failed: {e}")
            return PostResult(
                success=False,
                error_message=str(e),
                platform=SocialPlatform.TWITTER,
                timestamp=datetime.now()
            )
    
    async def get_user_tweets(self, user_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent tweets"""
        try:
            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
            
            params = {
                'max_results': min(max_results, 100),
                'tweet.fields': 'created_at,public_metrics,text'
            }
            
            async with self.session.get(f"{self.base_url}/users/{user_id}/tweets", 
                                      headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.error(f"Failed to get user tweets: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Failed to get user tweets: {e}")
            return []

class InstagramService:
    """Instagram Basic Display API integration"""
    
    def __init__(self):
        self.app_id = os.getenv('INSTAGRAM_APP_ID')
        self.app_secret = os.getenv('INSTAGRAM_APP_SECRET')
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.base_url = "https://graph.instagram.com"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_user_profile(self, access_token: str) -> Optional[SocialUser]:
        """Get Instagram user profile"""
        try:
            params = {
                'fields': 'id,username,media_count,account_type',
                'access_token': access_token
            }
            
            async with self.session.get(f"{self.base_url}/me", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return SocialUser(
                        platform_id=data.get('id'),
                        username=data.get('username'),
                        display_name=data.get('username'),
                        followers_count=data.get('media_count', 0),
                        platform=SocialPlatform.INSTAGRAM,
                        raw_data=data
                    )
                
            return None
        
        except Exception as e:
            logger.error(f"Failed to get Instagram profile: {e}")
            return None
    
    async def get_user_media(self, access_token: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get user's Instagram media"""
        try:
            params = {
                'fields': 'id,caption,media_type,media_url,permalink,timestamp',
                'access_token': access_token,
                'limit': limit
            }
            
            async with self.session.get(f"{self.base_url}/me/media", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.error(f"Failed to get Instagram media: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Failed to get Instagram media: {e}")
            return []

class GoogleService:
    """Google APIs integration (YouTube, Google+, etc.)"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.youtube_base_url = "https://www.googleapis.com/youtube/v3"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_youtube_videos(self, query: str, max_results: int = 25) -> List[Dict[str, Any]]:
        """Search YouTube videos"""
        try:
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': max_results,
                'key': self.api_key
            }
            
            async with self.session.get(f"{self.youtube_base_url}/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('items', [])
                else:
                    logger.error(f"YouTube search failed: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return []
    
    async def get_user_profile_google(self, access_token: str) -> Optional[SocialUser]:
        """Get Google user profile"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            async with self.session.get("https://www.googleapis.com/oauth2/v2/userinfo", 
                                      headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return SocialUser(
                        platform_id=data.get('id'),
                        username=data.get('email'),
                        display_name=data.get('name'),
                        email=data.get('email'),
                        profile_picture=data.get('picture'),
                        verified=data.get('verified_email', False),
                        platform=SocialPlatform.GOOGLE,
                        raw_data=data
                    )
                
            return None
        
        except Exception as e:
            logger.error(f"Failed to get Google profile: {e}")
            return None

class SocialMediaService:
    """Unified social media service orchestrator"""
    
    def __init__(self):
        self.facebook_service = FacebookService()
        self.twitter_service = TwitterService()
        self.instagram_service = InstagramService()
        self.google_service = GoogleService()
        
        # Content templates for different platforms
        self.platform_templates = {
            'movie_promotion': {
                SocialPlatform.FACEBOOK: "🎬 Now showing: {movie_title}! Book your tickets now at BookMyMovie. {link} #Movies #Cinema #BookMyMovie",
                SocialPlatform.TWITTER: "🎬 {movie_title} is now showing! Get your tickets: {link} #Movies #Cinema #BookMyMovie",
                SocialPlatform.INSTAGRAM: "🎬✨ {movie_title} - An unforgettable cinematic experience awaits! 🍿 #Movies #Cinema #BookMyMovie #NowShowing"
            },
            'special_offer': {
                SocialPlatform.FACEBOOK: "🔥 Special Offer Alert! Get {discount}% off on {movie_title} tickets. Limited time only! {link} #Discount #Movies #BookMyMovie",
                SocialPlatform.TWITTER: "🔥 {discount}% OFF {movie_title} tickets! Limited time: {link} #MovieDeals #BookMyMovie",
                SocialPlatform.INSTAGRAM: "🔥 SPECIAL OFFER 🔥 {discount}% off {movie_title}! Don't miss out! 🎬 #MovieDeals #SpecialOffer #BookMyMovie"
            },
            'new_release': {
                SocialPlatform.FACEBOOK: "🆕 Just Released: {movie_title}! Experience the magic in theaters. Book now: {link} #NewRelease #Movies #BookMyMovie",
                SocialPlatform.TWITTER: "🆕 {movie_title} just hit theaters! Book your seats: {link} #NewRelease #Movies",
                SocialPlatform.INSTAGRAM: "🆕✨ NEW RELEASE ALERT ✨ {movie_title} is here! 🎬🍿 #NewRelease #Movies #BookMyMovie"
            }
        }
    
    async def post_to_platform(self, platform: SocialPlatform, post: SocialPost) -> PostResult:
        """Post content to specific platform"""
        try:
            if platform == SocialPlatform.FACEBOOK:
                async with self.facebook_service as service:
                    return await service.post_to_page(post)
            
            elif platform == SocialPlatform.TWITTER:
                async with self.twitter_service as service:
                    return await service.post_tweet(post)
            
            elif platform == SocialPlatform.INSTAGRAM:
                # Instagram requires manual posting through their app
                return PostResult(
                    success=False,
                    error_message="Instagram posting requires manual action",
                    platform=platform,
                    timestamp=datetime.now()
                )
            
            else:
                return PostResult(
                    success=False,
                    error_message=f"Platform {platform} not supported for posting",
                    platform=platform,
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            logger.error(f"Social media post failed for {platform}: {e}")
            return PostResult(
                success=False,
                error_message=str(e),
                platform=platform,
                timestamp=datetime.now()
            )
    
    async def post_to_all_platforms(self, post: SocialPost, platforms: List[SocialPlatform] = None) -> Dict[SocialPlatform, PostResult]:
        """Post content to multiple platforms"""
        platforms = platforms or [SocialPlatform.FACEBOOK, SocialPlatform.TWITTER]
        
        tasks = []
        for platform in platforms:
            # Customize post for each platform
            platform_post = self._customize_post_for_platform(post, platform)
            tasks.append(self.post_to_platform(platform, platform_post))
        
        results = await asyncio.gather(*tasks)
        
        return dict(zip(platforms, results))
    
    def _customize_post_for_platform(self, post: SocialPost, platform: SocialPlatform) -> SocialPost:
        """Customize post content for specific platform"""
        customized_post = SocialPost(
            content=post.content,
            post_type=post.post_type,
            image_url=post.image_url,
            video_url=post.video_url,
            link_url=post.link_url,
            hashtags=post.hashtags,
            mentions=post.mentions,
            scheduled_time=post.scheduled_time,
            platform=platform
        )
        
        # Platform-specific customizations
        if platform == SocialPlatform.TWITTER:
            # Ensure content fits Twitter's character limit
            if len(customized_post.content) > 240:  # Leave room for hashtags and links
                customized_post.content = customized_post.content[:237] + "..."
        
        elif platform == SocialPlatform.INSTAGRAM:
            # Instagram posts typically need more hashtags
            if customized_post.hashtags and len(customized_post.hashtags) < 5:
                customized_post.hashtags.extend(['cinema', 'movies', 'entertainment'])
        
        return customized_post
    
    async def create_movie_promotion_post(self, movie_data: Dict[str, Any], platforms: List[SocialPlatform] = None) -> Dict[SocialPlatform, PostResult]:
        """Create and post movie promotion across platforms"""
        
        # Create base post content
        template_data = {
            'movie_title': movie_data.get('title', ''),
            'link': movie_data.get('booking_link', 'https://bookmymovie.com'),
            'discount': movie_data.get('discount', '20')
        }
        
        results = {}
        platforms = platforms or [SocialPlatform.FACEBOOK, SocialPlatform.TWITTER]
        
        for platform in platforms:
            template = self.platform_templates['movie_promotion'].get(platform)
            if template:
                content = template.format(**template_data)
                
                post = SocialPost(
                    content=content,
                    post_type=PostType.LINK if movie_data.get('booking_link') else PostType.TEXT,
                    link_url=movie_data.get('booking_link'),
                    image_url=movie_data.get('poster_url'),
                    hashtags=['Movies', 'Cinema', 'BookMyMovie', movie_data.get('title', '').replace(' ', '')],
                    platform=platform
                )
                
                result = await self.post_to_platform(platform, post)
                results[platform] = result
        
        return results
    
    async def get_user_social_profiles(self, user_tokens: Dict[str, str]) -> Dict[SocialPlatform, Optional[SocialUser]]:
        """Get user profiles from multiple social platforms"""
        profiles = {}
        
        # Get Facebook profile
        if 'facebook' in user_tokens:
            async with self.facebook_service as service:
                profiles[SocialPlatform.FACEBOOK] = await service.get_user_profile(user_tokens['facebook'])
        
        # Get Instagram profile
        if 'instagram' in user_tokens:
            async with self.instagram_service as service:
                profiles[SocialPlatform.INSTAGRAM] = await service.get_user_profile(user_tokens['instagram'])
        
        # Get Google profile
        if 'google' in user_tokens:
            async with self.google_service as service:
                profiles[SocialPlatform.GOOGLE] = await service.get_user_profile_google(user_tokens['google'])
        
        return profiles
    
    async def get_social_media_analytics(self) -> Dict[str, Any]:
        """Get analytics from all social media platforms"""
        analytics = {}
        
        # Facebook analytics
        async with self.facebook_service as service:
            analytics['facebook'] = await service.get_page_insights()
        
        # Add other platform analytics here
        analytics['twitter'] = {'placeholder': 'Twitter analytics would go here'}
        analytics['instagram'] = {'placeholder': 'Instagram analytics would go here'}
        
        return analytics
    
    async def schedule_posts(self, posts: List[SocialPost], platforms: List[SocialPlatform]) -> Dict[str, List[PostResult]]:
        """Schedule posts for future publishing (placeholder implementation)"""
        # This would integrate with a job scheduler like Celery
        scheduled_posts = {}
        
        for post in posts:
            if post.scheduled_time and post.scheduled_time > datetime.now():
                # In a real implementation, this would queue the post for later
                scheduled_posts[post.scheduled_time.isoformat()] = []
                
                for platform in platforms:
                    # Placeholder for scheduled post
                    result = PostResult(
                        success=True,
                        post_id=f"scheduled_{datetime.now().timestamp()}",
                        platform=platform,
                        timestamp=datetime.now()
                    )
                    scheduled_posts[post.scheduled_time.isoformat()].append(result)
        
        return scheduled_posts

# Global social media service instance
social_media_service = SocialMediaService()

# Utility functions for common use cases
async def promote_new_movie(movie_data: Dict[str, Any], platforms: List[SocialPlatform] = None):
    """Promote a new movie across social media platforms"""
    return await social_media_service.create_movie_promotion_post(movie_data, platforms)

async def share_user_booking(user_id: str, booking_data: Dict[str, Any], user_tokens: Dict[str, str]):
    """Allow user to share their movie booking on social media"""
    share_content = f"Just booked tickets for {booking_data.get('movie_title')}! Can't wait to watch it at {booking_data.get('cinema_name')} 🎬🍿 #Movies #BookMyMovie"
    
    post = SocialPost(
        content=share_content,
        post_type=PostType.TEXT,
        hashtags=['Movies', 'Cinema', 'BookMyMovie'],
    )
    
    results = {}
    
    # Post to platforms where user has provided tokens
    if 'facebook' in user_tokens:
        # Note: This would require user consent and proper OAuth flow
        results['facebook'] = {'message': 'User can share manually on Facebook'}
    
    if 'twitter' in user_tokens:
        # Note: This would require user consent and proper OAuth flow
        results['twitter'] = {'message': 'User can share manually on Twitter'}
    
    return results

async def get_movie_social_buzz(movie_title: str) -> Dict[str, Any]:
    """Get social media buzz/mentions for a movie"""
    buzz_data = {}
    
    # Search YouTube for movie trailers/reviews
    async with social_media_service.google_service as service:
        youtube_videos = await service.search_youtube_videos(f"{movie_title} trailer review")
        buzz_data['youtube_videos'] = len(youtube_videos)
        buzz_data['youtube_results'] = youtube_videos[:5]  # Top 5 results
    
    # In a real implementation, you would search Twitter, Facebook, etc. for mentions
    buzz_data['estimated_mentions'] = {
        'twitter': 'Would search Twitter API for mentions',
        'facebook': 'Would search Facebook API for mentions',
        'instagram': 'Would search Instagram API for mentions'
    }
    
    return buzz_data