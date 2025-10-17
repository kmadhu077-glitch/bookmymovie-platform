"""
👥 Social Features Platform Service
Community engagement with reviews, sharing, and social interaction
Port: 8022
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
import logging
from contextlib import asynccontextmanager
from enum import Enum
import hashlib
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums for social features
class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"

class PostType(str, Enum):
    REVIEW = "review"
    DISCUSSION = "discussion"
    RECOMMENDATION = "recommendation"
    QUESTION = "question"
    POLL = "poll"

class SocialActivityType(str, Enum):
    LIKE = "like"
    SHARE = "share"
    COMMENT = "comment"
    FOLLOW = "follow"
    REVIEW = "review"
    BOOKMARK = "bookmark"

# Database setup
def init_social_platform_db():
    """Initialize the social platform database with comprehensive schema"""
    conn = sqlite3.connect('social_platform.db')
    cursor = conn.cursor()
    
    # User profiles table (extended social data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT,
            bio TEXT,
            avatar_url TEXT,
            location TEXT,
            favorite_genres JSON,
            social_links JSON, -- twitter, instagram, etc.
            privacy_settings JSON,
            reputation_score INTEGER DEFAULT 0,
            review_count INTEGER DEFAULT 0,
            follower_count INTEGER DEFAULT 0,
            following_count INTEGER DEFAULT 0,
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_verified BOOLEAN DEFAULT FALSE,
            is_critic BOOLEAN DEFAULT FALSE,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Movie reviews and ratings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movie_reviews (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            movie_id TEXT NOT NULL,
            rating REAL NOT NULL CHECK (rating >= 0 AND rating <= 5),
            review_title TEXT,
            review_text TEXT,
            review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'approved',
            spoiler_warning BOOLEAN DEFAULT FALSE,
            helpful_votes INTEGER DEFAULT 0,
            total_votes INTEGER DEFAULT 0,
            verified_purchase BOOLEAN DEFAULT FALSE,
            watching_date DATE,
            theater_id TEXT,
            tags JSON, -- drama, action, must-watch, etc.
            FOREIGN KEY (user_id) REFERENCES user_profiles (user_id),
            UNIQUE(user_id, movie_id)
        )
    ''')
    
    # Discussion forums table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_posts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            movie_id TEXT,
            post_type TEXT DEFAULT 'discussion',
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            category TEXT, -- general, spoilers, theories, trivia
            tags JSON,
            view_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            is_pinned BOOLEAN DEFAULT FALSE,
            is_locked BOOLEAN DEFAULT FALSE,
            parent_post_id TEXT,
            FOREIGN KEY (user_id) REFERENCES user_profiles (user_id),
            FOREIGN KEY (parent_post_id) REFERENCES forum_posts (id)
        )
    ''')
    
    # Social interactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS social_interactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            target_id TEXT NOT NULL, -- review_id, post_id, user_id
            target_type TEXT NOT NULL, -- review, post, user
            interaction_type TEXT NOT NULL, -- like, share, comment, follow
            interaction_data JSON, -- additional data like comment text
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
        )
    ''')
    
    # Social sharing and activity feed table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_feed (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            activity_type TEXT NOT NULL, -- reviewed, shared, commented, etc.
            content_id TEXT NOT NULL, -- movie_id, review_id, post_id
            content_type TEXT NOT NULL, -- movie, review, post
            activity_text TEXT,
            activity_data JSON,
            visibility TEXT DEFAULT 'public', -- public, friends, private
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            engagement_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
        )
    ''')
    
    # User connections (followers/following)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_connections (
            id TEXT PRIMARY KEY,
            follower_id TEXT NOT NULL,
            following_id TEXT NOT NULL,
            connection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            connection_type TEXT DEFAULT 'follow', -- follow, friend, block
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (follower_id) REFERENCES user_profiles (user_id),
            FOREIGN KEY (following_id) REFERENCES user_profiles (user_id),
            UNIQUE(follower_id, following_id)
        )
    ''')
    
    # Movie watchlists and collections
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_collections (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            collection_name TEXT NOT NULL,
            collection_type TEXT DEFAULT 'watchlist', -- watchlist, favorites, watched
            description TEXT,
            movie_ids JSON NOT NULL, -- list of movie IDs
            is_public BOOLEAN DEFAULT TRUE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            collection_image TEXT,
            tags JSON,
            FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
        )
    ''')
    
    # Social media integration
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS social_shares (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            content_id TEXT NOT NULL, -- movie_id, review_id
            content_type TEXT NOT NULL, -- movie, review, list
            platform TEXT NOT NULL, -- twitter, facebook, instagram
            share_url TEXT,
            share_text TEXT,
            share_image TEXT,
            shared_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            engagement_metrics JSON, -- likes, shares, comments from platform
            FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
        )
    ''')
    
    # Community events and challenges
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS community_events (
            id TEXT PRIMARY KEY,
            event_name TEXT NOT NULL,
            event_type TEXT NOT NULL, -- challenge, contest, discussion
            description TEXT NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            event_data JSON, -- rules, prizes, requirements
            participant_count INTEGER DEFAULT 0,
            created_by TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (created_by) REFERENCES user_profiles (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Pydantic models
class UserProfile(BaseModel):
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    favorite_genres: Optional[List[str]] = None
    social_links: Optional[Dict[str, str]] = None
    privacy_settings: Optional[Dict[str, bool]] = None

    @field_validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', v):
            raise ValueError('Username must be 3-20 characters, alphanumeric and underscore only')
        return v

class MovieReview(BaseModel):
    movie_id: str
    rating: float
    review_title: Optional[str] = None
    review_text: Optional[str] = None
    spoiler_warning: bool = False
    watching_date: Optional[str] = None
    theater_id: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator('rating')
    def validate_rating(cls, v):
        if not 0 <= v <= 5:
            raise ValueError('Rating must be between 0 and 5')
        return v

class ForumPost(BaseModel):
    movie_id: Optional[str] = None
    post_type: PostType = PostType.DISCUSSION
    title: str
    content: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    parent_post_id: Optional[str] = None

class SocialInteraction(BaseModel):
    target_id: str
    target_type: str  # review, post, user
    interaction_type: SocialActivityType
    interaction_data: Optional[Dict[str, Any]] = None

class UserCollection(BaseModel):
    collection_name: str
    collection_type: str = "watchlist"
    description: Optional[str] = None
    movie_ids: List[str]
    is_public: bool = True
    tags: Optional[List[str]] = None

class SocialShare(BaseModel):
    content_id: str
    content_type: str  # movie, review, list
    platform: str  # twitter, facebook, instagram
    share_text: Optional[str] = None

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_social_platform_db()
    logger.info("👥 Social Features Platform starting up...")
    yield
    # Shutdown
    logger.info("👥 Social Features Platform shutting down...")

app = FastAPI(
    title="👥 Social Features Platform",
    description="Community engagement with reviews, sharing, and social interaction",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SocialPlatformService:
    """Comprehensive Social Features Platform Service"""
    
    def __init__(self):
        self.db_path = 'social_platform.db'
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
    
    # User Profile Management
    def create_user_profile(self, user_id: str, profile_data: UserProfile) -> Dict[str, Any]:
        """Create or update user social profile"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if username is taken
        cursor.execute('SELECT user_id FROM user_profiles WHERE username = ? AND user_id != ?', 
                      (profile_data.username, user_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already taken")
        
        favorite_genres_json = json.dumps(profile_data.favorite_genres) if profile_data.favorite_genres else None
        social_links_json = json.dumps(profile_data.social_links) if profile_data.social_links else None
        privacy_json = json.dumps(profile_data.privacy_settings) if profile_data.privacy_settings else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles 
            (user_id, username, display_name, bio, avatar_url, location,
             favorite_genres, social_links, privacy_settings, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_id, profile_data.username, profile_data.display_name,
            profile_data.bio, profile_data.avatar_url, profile_data.location,
            favorite_genres_json, social_links_json, privacy_json
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "user_id": user_id,
            "username": profile_data.username,
            "status": "created",
            "message": f"Profile created for @{profile_data.username}"
        }
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with social stats"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, display_name, bio, avatar_url, location,
                   favorite_genres, reputation_score, review_count,
                   follower_count, following_count, joined_date, is_verified, is_critic
            FROM user_profiles WHERE user_id = ?
        ''', (user_id,))
        
        profile_row = cursor.fetchone()
        if not profile_row:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get recent activity
        cursor.execute('''
            SELECT activity_type, content_type, activity_text, created_date
            FROM activity_feed WHERE user_id = ?
            ORDER BY created_date DESC LIMIT 10
        ''', (user_id,))
        
        recent_activity = []
        for activity in cursor.fetchall():
            recent_activity.append({
                "type": activity[0],
                "content_type": activity[1],
                "text": activity[2],
                "date": activity[3]
            })
        
        conn.close()
        
        favorite_genres = json.loads(profile_row[5]) if profile_row[5] else []
        
        return {
            "user_id": user_id,
            "username": profile_row[0],
            "display_name": profile_row[1],
            "bio": profile_row[2],
            "avatar_url": profile_row[3],
            "location": profile_row[4],
            "favorite_genres": favorite_genres,
            "reputation_score": profile_row[6],
            "review_count": profile_row[7],
            "follower_count": profile_row[8],
            "following_count": profile_row[9],
            "joined_date": profile_row[10],
            "is_verified": profile_row[11],
            "is_critic": profile_row[12],
            "recent_activity": recent_activity
        }
    
    # Movie Reviews System
    def create_movie_review(self, user_id: str, review_data: MovieReview) -> Dict[str, Any]:
        """Create or update movie review"""
        review_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        tags_json = json.dumps(review_data.tags) if review_data.tags else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO movie_reviews 
            (id, user_id, movie_id, rating, review_title, review_text,
             spoiler_warning, watching_date, theater_id, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            review_id, user_id, review_data.movie_id, review_data.rating,
            review_data.review_title, review_data.review_text,
            review_data.spoiler_warning, review_data.watching_date,
            review_data.theater_id, tags_json
        ))
        
        # Update user review count
        cursor.execute('''
            UPDATE user_profiles 
            SET review_count = review_count + 1,
                reputation_score = reputation_score + 5
            WHERE user_id = ?
        ''', (user_id,))
        
        # Add to activity feed
        self._add_activity(user_id, "review", review_data.movie_id, "movie", 
                          f"Reviewed a movie with {review_data.rating} stars")
        
        conn.commit()
        conn.close()
        
        return {
            "review_id": review_id,
            "movie_id": review_data.movie_id,
            "rating": review_data.rating,
            "status": "created",
            "message": "Review created successfully"
        }
    
    def get_movie_reviews(self, movie_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Get reviews for a specific movie"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.id, r.user_id, u.username, u.display_name, u.avatar_url,
                   r.rating, r.review_title, r.review_text, r.review_date,
                   r.spoiler_warning, r.helpful_votes, r.total_votes,
                   r.verified_purchase, r.tags, u.is_verified, u.is_critic
            FROM movie_reviews r
            JOIN user_profiles u ON r.user_id = u.user_id
            WHERE r.movie_id = ? AND r.status = 'approved'
            ORDER BY r.helpful_votes DESC, r.review_date DESC
            LIMIT ? OFFSET ?
        ''', (movie_id, limit, offset))
        
        reviews = []
        for row in cursor.fetchall():
            tags = json.loads(row[13]) if row[13] else []
            reviews.append({
                "review_id": row[0],
                "user": {
                    "user_id": row[1],
                    "username": row[2],
                    "display_name": row[3],
                    "avatar_url": row[4],
                    "is_verified": row[14],
                    "is_critic": row[15]
                },
                "rating": row[5],
                "review_title": row[6],
                "review_text": row[7],
                "review_date": row[8],
                "spoiler_warning": row[9],
                "helpful_votes": row[10],
                "total_votes": row[11],
                "verified_purchase": row[12],
                "tags": tags,
                "helpfulness_ratio": row[10] / max(row[11], 1)
            })
        
        # Get average rating
        cursor.execute('''
            SELECT AVG(rating), COUNT(*) 
            FROM movie_reviews 
            WHERE movie_id = ? AND status = 'approved'
        ''', (movie_id,))
        
        rating_stats = cursor.fetchone()
        avg_rating = round(rating_stats[0], 1) if rating_stats[0] else 0
        total_reviews = rating_stats[1]
        
        conn.close()
        
        return {
            "movie_id": movie_id,
            "reviews": reviews,
            "total_reviews": total_reviews,
            "average_rating": avg_rating,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(reviews) == limit
            }
        }
    
    # Forum and Discussion System
    def create_forum_post(self, user_id: str, post_data: ForumPost) -> Dict[str, Any]:
        """Create a new forum post or discussion"""
        post_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        tags_json = json.dumps(post_data.tags) if post_data.tags else None
        
        cursor.execute('''
            INSERT INTO forum_posts 
            (id, user_id, movie_id, post_type, title, content, category, tags, parent_post_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_id, user_id, post_data.movie_id, post_data.post_type.value,
            post_data.title, post_data.content, post_data.category,
            tags_json, post_data.parent_post_id
        ))
        
        # Update parent post reply count if this is a reply
        if post_data.parent_post_id:
            cursor.execute('''
                UPDATE forum_posts 
                SET reply_count = reply_count + 1 
                WHERE id = ?
            ''', (post_data.parent_post_id,))
        
        # Add to activity feed
        activity_text = f"Started a discussion: {post_data.title}" if not post_data.parent_post_id else "Replied to a discussion"
        self._add_activity(user_id, "discussion", post_id, "post", activity_text)
        
        conn.commit()
        conn.close()
        
        return {
            "post_id": post_id,
            "title": post_data.title,
            "post_type": post_data.post_type.value,
            "status": "created",
            "message": "Forum post created successfully"
        }
    
    def get_forum_posts(self, movie_id: Optional[str] = None, category: Optional[str] = None,
                       limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get forum posts with optional filtering"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT p.id, p.user_id, u.username, u.display_name, u.avatar_url,
                   p.movie_id, p.post_type, p.title, p.content, p.created_date,
                   p.category, p.view_count, p.reply_count, p.like_count,
                   p.is_pinned, u.is_verified
            FROM forum_posts p
            JOIN user_profiles u ON p.user_id = u.user_id
            WHERE p.status = 'active' AND p.parent_post_id IS NULL
        '''
        
        params = []
        
        if movie_id:
            query += ' AND p.movie_id = ?'
            params.append(movie_id)
        
        if category:
            query += ' AND p.category = ?'
            params.append(category)
        
        query += ' ORDER BY p.is_pinned DESC, p.created_date DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        posts = []
        for row in cursor.fetchall():
            posts.append({
                "post_id": row[0],
                "user": {
                    "user_id": row[1],
                    "username": row[2],
                    "display_name": row[3],
                    "avatar_url": row[4],
                    "is_verified": row[15]
                },
                "movie_id": row[5],
                "post_type": row[6],
                "title": row[7],
                "content": row[8][:200] + "..." if len(row[8]) > 200 else row[8],  # Truncate for list view
                "created_date": row[9],
                "category": row[10],
                "view_count": row[11],
                "reply_count": row[12],
                "like_count": row[13],
                "is_pinned": row[14]
            })
        
        conn.close()
        return posts
    
    # Social Interactions
    def create_social_interaction(self, user_id: str, interaction: SocialInteraction) -> Dict[str, Any]:
        """Create social interaction (like, share, comment, follow)"""
        interaction_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if interaction already exists (for likes/follows)
        if interaction.interaction_type in [SocialActivityType.LIKE, SocialActivityType.FOLLOW]:
            cursor.execute('''
                SELECT id FROM social_interactions 
                WHERE user_id = ? AND target_id = ? AND target_type = ? AND interaction_type = ? AND is_active = TRUE
            ''', (user_id, interaction.target_id, interaction.target_type, interaction.interaction_type.value))
            
            if cursor.fetchone():
                # Toggle existing interaction
                cursor.execute('''
                    UPDATE social_interactions 
                    SET is_active = NOT is_active 
                    WHERE user_id = ? AND target_id = ? AND target_type = ? AND interaction_type = ?
                ''', (user_id, interaction.target_id, interaction.target_type, interaction.interaction_type.value))
                
                conn.commit()
                conn.close()
                return {"status": "toggled", "interaction_type": interaction.interaction_type.value}
        
        interaction_data_json = json.dumps(interaction.interaction_data) if interaction.interaction_data else None
        
        cursor.execute('''
            INSERT INTO social_interactions 
            (id, user_id, target_id, target_type, interaction_type, interaction_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            interaction_id, user_id, interaction.target_id, interaction.target_type,
            interaction.interaction_type.value, interaction_data_json
        ))
        
        # Update counters based on interaction type
        if interaction.interaction_type == SocialActivityType.LIKE:
            if interaction.target_type == "review":
                cursor.execute('UPDATE movie_reviews SET helpful_votes = helpful_votes + 1, total_votes = total_votes + 1 WHERE id = ?', 
                             (interaction.target_id,))
            elif interaction.target_type == "post":
                cursor.execute('UPDATE forum_posts SET like_count = like_count + 1 WHERE id = ?', 
                             (interaction.target_id,))
        
        elif interaction.interaction_type == SocialActivityType.FOLLOW:
            cursor.execute('UPDATE user_profiles SET follower_count = follower_count + 1 WHERE user_id = ?', 
                         (interaction.target_id,))
            cursor.execute('UPDATE user_profiles SET following_count = following_count + 1 WHERE user_id = ?', 
                         (user_id,))
        
        conn.commit()
        conn.close()
        
        return {
            "interaction_id": interaction_id,
            "interaction_type": interaction.interaction_type.value,
            "status": "created",
            "message": f"{interaction.interaction_type.value.title()} interaction created"
        }
    
    # User Collections (Watchlists, Favorites)
    def create_user_collection(self, user_id: str, collection_data: UserCollection) -> Dict[str, Any]:
        """Create user movie collection/watchlist"""
        collection_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        movie_ids_json = json.dumps(collection_data.movie_ids)
        tags_json = json.dumps(collection_data.tags) if collection_data.tags else None
        
        cursor.execute('''
            INSERT INTO user_collections 
            (id, user_id, collection_name, collection_type, description, 
             movie_ids, is_public, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            collection_id, user_id, collection_data.collection_name,
            collection_data.collection_type, collection_data.description,
            movie_ids_json, collection_data.is_public, tags_json
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "collection_id": collection_id,
            "collection_name": collection_data.collection_name,
            "movie_count": len(collection_data.movie_ids),
            "status": "created",
            "message": "Collection created successfully"
        }
    
    def _add_activity(self, user_id: str, activity_type: str, content_id: str, 
                     content_type: str, activity_text: str):
        """Add activity to user's feed"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        activity_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO activity_feed 
            (id, user_id, activity_type, content_id, content_type, activity_text)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (activity_id, user_id, activity_type, content_id, content_type, activity_text))
        
        conn.commit()
        conn.close()
    
    def get_activity_feed(self, user_id: str, include_following: bool = True, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's personalized activity feed"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if include_following:
            # Get activities from user and people they follow
            cursor.execute('''
                SELECT a.id, a.user_id, u.username, u.display_name, u.avatar_url,
                       a.activity_type, a.content_type, a.activity_text, a.created_date,
                       a.engagement_count
                FROM activity_feed a
                JOIN user_profiles u ON a.user_id = u.user_id
                WHERE (a.user_id = ? OR a.user_id IN (
                    SELECT following_id FROM user_connections 
                    WHERE follower_id = ? AND is_active = TRUE
                )) AND a.visibility IN ('public', 'friends')
                ORDER BY a.created_date DESC
                LIMIT ?
            ''', (user_id, user_id, limit))
        else:
            # Get only user's own activities
            cursor.execute('''
                SELECT a.id, a.user_id, u.username, u.display_name, u.avatar_url,
                       a.activity_type, a.content_type, a.activity_text, a.created_date,
                       a.engagement_count
                FROM activity_feed a
                JOIN user_profiles u ON a.user_id = u.user_id
                WHERE a.user_id = ?
                ORDER BY a.created_date DESC
                LIMIT ?
            ''', (user_id, limit))
        
        activities = []
        for row in cursor.fetchall():
            activities.append({
                "activity_id": row[0],
                "user": {
                    "user_id": row[1],
                    "username": row[2],
                    "display_name": row[3],
                    "avatar_url": row[4]
                },
                "activity_type": row[5],
                "content_type": row[6],
                "activity_text": row[7],
                "created_date": row[8],
                "engagement_count": row[9]
            })
        
        conn.close()
        return activities

# Initialize service
social_service = SocialPlatformService()

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Social Features Platform Dashboard"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>👥 Social Features Platform</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                     color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 30px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .social-stat { background: linear-gradient(45deg, #FF6B6B, #4ECDC4); color: white; 
                          padding: 15px; border-radius: 8px; text-align: center; margin: 10px 0; }
            .review-item { border-left: 4px solid #4ECDC4; padding: 10px; margin: 10px 0; background: #f0f8ff; }
            .post-item { border-left: 4px solid #667eea; padding: 10px; margin: 10px 0; background: #f8f9fa; }
            .user-badge { display: inline-block; background: #28a745; color: white; padding: 2px 8px; 
                         border-radius: 12px; font-size: 12px; margin-left: 5px; }
            .critic-badge { background: #ffc107; color: #212529; }
            button { background: #667eea; color: white; border: none; padding: 10px 20px; 
                    border-radius: 5px; cursor: pointer; margin: 5px; }
            button:hover { background: #5a6fd8; }
            .input-box { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            .rating-stars { color: #ffc107; }
            .activity-item { background: #e8f5e8; padding: 10px; margin: 5px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>👥 Social Features Platform</h1>
                <p>Community Engagement • User Reviews • Social Sharing • Discussion Forums</p>
            </div>
            
            <div class="grid">
                <!-- Community Stats -->
                <div class="card">
                    <h3>📊 Community Statistics</h3>
                    <div class="social-stat">
                        <h4>👥 Total Users</h4>
                        <div id="totalUsers">-</div>
                    </div>
                    <div class="social-stat">
                        <h4>⭐ Total Reviews</h4>
                        <div id="totalReviews">-</div>
                    </div>
                    <div class="social-stat">
                        <h4>💬 Forum Posts</h4>
                        <div id="totalPosts">-</div>
                    </div>
                    <button onclick="loadCommunityStats()">🔄 Refresh Stats</button>
                </div>
                
                <!-- Create Review -->
                <div class="card">
                    <h3>✍️ Write Movie Review</h3>
                    <input type="text" id="reviewUserId" placeholder="User ID" class="input-box">
                    <input type="text" id="reviewMovieId" placeholder="Movie ID" class="input-box">
                    <input type="number" id="reviewRating" placeholder="Rating (0-5)" step="0.1" min="0" max="5" class="input-box">
                    <input type="text" id="reviewTitle" placeholder="Review Title" class="input-box">
                    <textarea id="reviewText" placeholder="Write your review..." class="input-box" rows="4"></textarea>
                    <label><input type="checkbox" id="spoilerWarning"> Contains Spoilers</label><br>
                    <button onclick="submitReview()">⭐ Submit Review</button>
                    <div id="reviewResult"></div>
                </div>
                
                <!-- Recent Reviews -->
                <div class="card">
                    <h3>⭐ Recent Movie Reviews</h3>
                    <div id="recentReviews">Loading reviews...</div>
                    <button onclick="loadRecentReviews()">🔄 Refresh Reviews</button>
                </div>
            </div>
            
            <div class="grid" style="margin-top: 20px;">
                <!-- Forum Discussions -->
                <div class="card">
                    <h3>💬 Forum Discussions</h3>
                    <div id="forumPosts">Loading discussions...</div>
                    <button onclick="loadForumPosts()">🔄 Refresh Discussions</button>
                </div>
                
                <!-- Activity Feed -->
                <div class="card">
                    <h3>🔔 Community Activity</h3>
                    <div id="activityFeed">
                        <div class="activity-item">
                            <strong>@moviefan123</strong> reviewed "Inception" ⭐⭐⭐⭐⭐<br>
                            <small>2 hours ago</small>
                        </div>
                        <div class="activity-item">
                            <strong>@cinephile_sara</strong> started a discussion about "Dune"<br>
                            <small>4 hours ago</small>
                        </div>
                        <div class="activity-item">
                            <strong>@reviewmaster</strong> created a watchlist "Must See Sci-Fi"<br>
                            <small>6 hours ago</small>
                        </div>
                    </div>
                </div>
                
                <!-- Social Analytics -->
                <div class="card">
                    <h3>📈 Social Engagement</h3>
                    <canvas id="engagementChart" width="400" height="200"></canvas>
                </div>
            </div>
        </div>
        
        <script>
        let communityData = {};
        
        async function loadCommunityStats() {
            try {
                // Simulated stats for demo
                document.getElementById('totalUsers').textContent = '2,847';
                document.getElementById('totalReviews').textContent = '15,392';
                document.getElementById('totalPosts').textContent = '8,156';
                
                updateEngagementChart();
            } catch (error) {
                console.error('Error loading community stats:', error);
            }
        }
        
        async function submitReview() {
            const userId = document.getElementById('reviewUserId').value;
            const movieId = document.getElementById('reviewMovieId').value;
            const rating = parseFloat(document.getElementById('reviewRating').value);
            const title = document.getElementById('reviewTitle').value;
            const text = document.getElementById('reviewText').value;
            const spoiler = document.getElementById('spoilerWarning').checked;
            
            if (!userId || !movieId || isNaN(rating) || !title) {
                alert('Please fill in all required fields');
                return;
            }
            
            try {
                const reviewData = {
                    movie_id: movieId,
                    rating: rating,
                    review_title: title,
                    review_text: text,
                    spoiler_warning: spoiler
                };
                
                const response = await fetch(`/users/${userId}/reviews/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reviewData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    document.getElementById('reviewResult').innerHTML = `
                        <div style="background: #d4edda; padding: 10px; margin: 10px 0; border-radius: 5px; color: #155724;">
                            ✅ Review submitted successfully!<br>
                            Movie: ${movieId}<br>
                            Rating: ${rating} stars
                        </div>
                    `;
                    
                    // Clear form
                    document.getElementById('reviewTitle').value = '';
                    document.getElementById('reviewText').value = '';
                    document.getElementById('reviewRating').value = '';
                    document.getElementById('spoilerWarning').checked = false;
                    
                    // Refresh reviews
                    setTimeout(loadRecentReviews, 1000);
                } else {
                    throw new Error(result.detail || 'Failed to submit review');
                }
                
            } catch (error) {
                document.getElementById('reviewResult').innerHTML = `
                    <div style="background: #f8d7da; padding: 10px; margin: 10px 0; border-radius: 5px; color: #721c24;">
                        ❌ Error: ${error.message}
                    </div>
                `;
            }
        }
        
        async function loadRecentReviews() {
            document.getElementById('recentReviews').innerHTML = `
                <div class="review-item">
                    <strong>@moviefan123</strong> <span class="user-badge">Verified</span><br>
                    <span class="rating-stars">⭐⭐⭐⭐⭐</span> "Incredible cinematography and story!"<br>
                    <strong>Movie:</strong> Inception<br>
                    <small>2 hours ago • 🔥 Hot take!</small>
                </div>
                <div class="review-item">
                    <strong>@cinephile_sara</strong> <span class="user-badge critic-badge">Critic</span><br>
                    <span class="rating-stars">⭐⭐⭐⭐</span> "A masterpiece of science fiction"<br>
                    <strong>Movie:</strong> Dune<br>
                    <small>4 hours ago • 👍 15 helpful votes</small>
                </div>
                <div class="review-item">
                    <strong>@reviewmaster</strong><br>
                    <span class="rating-stars">⭐⭐⭐</span> "Good but not great"<br>
                    <strong>Movie:</strong> The Matrix Resurrections<br>
                    <small>6 hours ago • ⚠️ Contains spoilers</small>
                </div>
            `;
        }
        
        async function loadForumPosts() {
            document.getElementById('forumPosts').innerHTML = `
                <div class="post-item">
                    <strong>💬 "What's your favorite sci-fi movie of 2024?"</strong><br>
                    by <strong>@scifi_lover</strong> <span class="user-badge">Verified</span><br>
                    <small>💬 24 replies • 👍 18 likes • 2 hours ago</small>
                </div>
                <div class="post-item">
                    <strong>🎭 "Hidden gems in horror movies"</strong><br>
                    by <strong>@horror_expert</strong> <span class="user-badge critic-badge">Critic</span><br>
                    <small>💬 31 replies • 👍 45 likes • 5 hours ago</small>
                </div>
                <div class="post-item">
                    <strong>🤔 "Marvel vs DC: 2024 comparison"</strong><br>
                    by <strong>@superhero_fan</strong><br>
                    <small>💬 67 replies • 👍 23 likes • 8 hours ago</small>
                </div>
            `;
        }
        
        function updateEngagementChart() {
            const ctx = document.getElementById('engagementChart').getContext('2d');
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Reviews',
                        data: [45, 52, 38, 67, 89, 125, 78],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Forum Posts',
                        data: [23, 28, 19, 34, 45, 67, 41],
                        borderColor: '#4ECDC4',
                        backgroundColor: 'rgba(78, 205, 196, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Weekly Social Engagement'
                        }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        // Initialize dashboard
        loadCommunityStats();
        loadRecentReviews();
        loadForumPosts();
        
        // Set demo values
        setTimeout(() => {
            document.getElementById('reviewUserId').value = 'user_demo_001';
            document.getElementById('reviewMovieId').value = 'movie_demo_001';
        }, 500);
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            loadRecentReviews();
            loadForumPosts();
        }, 30000);
        </script>
    </body>
    </html>
    '''

@app.post("/users/{user_id}/profile/")
async def create_user_profile(user_id: str, profile_data: UserProfile):
    """Create or update user social profile"""
    return social_service.create_user_profile(user_id, profile_data)

@app.get("/users/{user_id}/profile/")
async def get_user_profile(user_id: str):
    """Get user profile with social stats"""
    return social_service.get_user_profile(user_id)

@app.post("/users/{user_id}/reviews/")
async def create_movie_review(user_id: str, review_data: MovieReview):
    """Create or update movie review"""
    return social_service.create_movie_review(user_id, review_data)

@app.get("/movies/{movie_id}/reviews/")
async def get_movie_reviews(movie_id: str, limit: int = Query(20, le=100), offset: int = Query(0, ge=0)):
    """Get reviews for a specific movie"""
    return social_service.get_movie_reviews(movie_id, limit, offset)

@app.post("/users/{user_id}/posts/")
async def create_forum_post(user_id: str, post_data: ForumPost):
    """Create a new forum post or discussion"""
    return social_service.create_forum_post(user_id, post_data)

@app.get("/forum/posts/")
async def get_forum_posts(movie_id: Optional[str] = None, category: Optional[str] = None,
                         limit: int = Query(20, le=100), offset: int = Query(0, ge=0)):
    """Get forum posts with optional filtering"""
    return social_service.get_forum_posts(movie_id, category, limit, offset)

@app.post("/users/{user_id}/interactions/")
async def create_social_interaction(user_id: str, interaction: SocialInteraction):
    """Create social interaction (like, share, comment, follow)"""
    return social_service.create_social_interaction(user_id, interaction)

@app.post("/users/{user_id}/collections/")
async def create_user_collection(user_id: str, collection_data: UserCollection):
    """Create user movie collection/watchlist"""
    return social_service.create_user_collection(user_id, collection_data)

@app.get("/users/{user_id}/feed/")
async def get_activity_feed(user_id: str, include_following: bool = Query(True), limit: int = Query(50, le=100)):
    """Get user's personalized activity feed"""
    return social_service.get_activity_feed(user_id, include_following, limit)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Social Features Platform",
        "status": "healthy",
        "port": 8022,
        "timestamp": datetime.now().isoformat(),
        "features": [
            "User Reviews & Ratings",
            "Discussion Forums",
            "Social Media Integration",
            "Community Engagement",
            "Activity Feeds",
            "User Collections"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("👥 Starting Social Features Platform...")
    print("🌐 Service URL: http://127.0.0.1:8022")
    print("👥 Dashboard: http://127.0.0.1:8022/")
    print("📚 API Docs: http://127.0.0.1:8022/docs")
    
    uvicorn.run(app, host="127.0.0.1", port=8022)