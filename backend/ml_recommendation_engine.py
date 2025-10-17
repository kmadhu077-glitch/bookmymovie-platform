"""
Advanced Machine Learning Recommendation Engine
Deep learning-based recommendation system with neural collaborative filtering,
content-based filtering, and hybrid approaches
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model, callbacks
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler, LabelEncoder
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import pickle
import redis
import hashlib
from concurrent.futures import ThreadPoolExecutor
import joblib

logger = logging.getLogger(__name__)

@dataclass
class RecommendationRequest:
    """Recommendation request structure"""
    user_id: str
    num_recommendations: int = 10
    recommendation_type: str = "hybrid"  # collaborative, content, hybrid
    exclude_watched: bool = True
    include_metadata: bool = True
    context: Dict[str, Any] = None  # time, location, device, etc.

@dataclass
class MovieRecommendation:
    """Movie recommendation structure"""
    movie_id: str
    title: str
    predicted_rating: float
    confidence_score: float
    recommendation_reason: str
    genres: List[str]
    release_year: int
    poster_url: str = None
    trailer_url: str = None
    metadata: Dict[str, Any] = None

@dataclass
class UserProfile:
    """Enhanced user profile for recommendations"""
    user_id: str
    age_group: str
    gender: str
    location: str
    preferred_genres: List[str]
    preferred_languages: List[str]
    favorite_actors: List[str]
    favorite_directors: List[str]
    viewing_history: List[Dict[str, Any]]
    rating_history: List[Dict[str, Any]]
    booking_patterns: Dict[str, Any]
    social_connections: List[str]
    last_updated: datetime

class NeuralCollaborativeFiltering:
    """Neural Collaborative Filtering model for movie recommendations"""
    
    def __init__(self, num_users: int, num_movies: int, embedding_size: int = 128, 
                 hidden_layers: List[int] = [256, 128, 64]):
        self.num_users = num_users
        self.num_movies = num_movies
        self.embedding_size = embedding_size
        self.hidden_layers = hidden_layers
        self.model = None
        self.user_encoder = LabelEncoder()
        self.movie_encoder = LabelEncoder()
        
    def build_model(self):
        """Build Neural Collaborative Filtering model"""
        
        # Input layers
        user_input = layers.Input(shape=(), name='user_id')
        movie_input = layers.Input(shape=(), name='movie_id')
        
        # Embedding layers
        user_embedding = layers.Embedding(
            input_dim=self.num_users,
            output_dim=self.embedding_size,
            name='user_embedding'
        )(user_input)
        
        movie_embedding = layers.Embedding(
            input_dim=self.num_movies,
            output_dim=self.embedding_size,
            name='movie_embedding'
        )(movie_input)
        
        # Flatten embeddings
        user_vec = layers.Flatten(name='user_flatten')(user_embedding)
        movie_vec = layers.Flatten(name='movie_flatten')(movie_embedding)
        
        # Concatenate user and movie embeddings
        concat = layers.Concatenate(name='concat')([user_vec, movie_vec])
        
        # Hidden layers with dropout
        x = concat
        for i, hidden_size in enumerate(self.hidden_layers):
            x = layers.Dense(
                hidden_size, 
                activation='relu',
                name=f'hidden_{i+1}'
            )(x)
            x = layers.Dropout(0.3, name=f'dropout_{i+1}')(x)
        
        # Output layer
        output = layers.Dense(1, activation='sigmoid', name='rating_prediction')(x)
        
        # Create model
        self.model = Model(
            inputs=[user_input, movie_input],
            outputs=output,
            name='neural_collaborative_filtering'
        )
        
        # Compile model
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mean_squared_error',
            metrics=['mae', 'mse']
        )
        
        return self.model
    
    def prepare_data(self, ratings_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for training"""
        
        # Encode users and movies
        ratings_df['user_encoded'] = self.user_encoder.fit_transform(ratings_df['user_id'])
        ratings_df['movie_encoded'] = self.movie_encoder.fit_transform(ratings_df['movie_id'])
        
        # Normalize ratings to 0-1 scale
        ratings_df['rating_normalized'] = ratings_df['rating'] / 5.0
        
        # Prepare features and target
        users = ratings_df['user_encoded'].values
        movies = ratings_df['movie_encoded'].values
        ratings = ratings_df['rating_normalized'].values
        
        return users, movies, ratings
    
    def train(self, ratings_df: pd.DataFrame, validation_split: float = 0.2, 
              epochs: int = 100, batch_size: int = 256):
        """Train the NCF model"""
        
        logger.info("Preparing training data...")
        users, movies, ratings = self.prepare_data(ratings_df)
        
        if self.model is None:
            self.build_model()
        
        # Callbacks
        early_stopping = callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        reduce_lr = callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-7
        )
        
        model_checkpoint = callbacks.ModelCheckpoint(
            'models/ncf_best_model.h5',
            monitor='val_loss',
            save_best_only=True,
            save_weights_only=False
        )
        
        logger.info("Starting model training...")
        history = self.model.fit(
            [users, movies], ratings,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr, model_checkpoint],
            verbose=1
        )
        
        logger.info("Training completed!")
        return history
    
    def predict(self, user_ids: List[str], movie_ids: List[str]) -> np.ndarray:
        """Predict ratings for user-movie pairs"""
        
        # Encode user and movie IDs
        user_encoded = []
        movie_encoded = []
        
        for user_id in user_ids:
            try:
                encoded = self.user_encoder.transform([user_id])[0]
                user_encoded.append(encoded)
            except ValueError:
                # Handle unknown users
                user_encoded.append(0)
        
        for movie_id in movie_ids:
            try:
                encoded = self.movie_encoder.transform([movie_id])[0]
                movie_encoded.append(encoded)
            except ValueError:
                # Handle unknown movies
                movie_encoded.append(0)
        
        # Predict ratings
        predictions = self.model.predict([
            np.array(user_encoded),
            np.array(movie_encoded)
        ])
        
        # Denormalize predictions (0-1 -> 1-5 scale)
        return predictions.flatten() * 5.0
    
    def get_user_recommendations(self, user_id: str, candidate_movies: List[str], 
                                top_k: int = 10) -> List[Tuple[str, float]]:
        """Get top-k movie recommendations for a user"""
        
        user_ids = [user_id] * len(candidate_movies)
        predictions = self.predict(user_ids, candidate_movies)
        
        # Sort by predicted rating
        movie_scores = list(zip(candidate_movies, predictions))
        movie_scores.sort(key=lambda x: x[1], reverse=True)
        
        return movie_scores[:top_k]

class ContentBasedRecommender:
    """Content-based recommendation using movie features"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.movie_features = None
        self.movie_similarity_matrix = None
        self.scaler = StandardScaler()
        
    def prepare_movie_features(self, movies_df: pd.DataFrame):
        """Prepare movie feature matrix"""
        
        # Text features (genres, plot, cast, director)
        text_features = []
        for _, movie in movies_df.iterrows():
            text = " ".join([
                " ".join(movie.get('genres', [])),
                movie.get('plot', ''),
                " ".join(movie.get('cast', [])[:5]),  # Top 5 cast members
                movie.get('director', ''),
                " ".join(movie.get('keywords', []))
            ])
            text_features.append(text)
        
        # Create TF-IDF matrix
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(text_features)
        
        # Numerical features
        numerical_features = []
        for _, movie in movies_df.iterrows():
            features = [
                movie.get('release_year', 2000) / 2025.0,  # Normalized year
                movie.get('runtime', 120) / 300.0,  # Normalized runtime
                movie.get('budget', 0) / 200000000.0,  # Normalized budget
                movie.get('average_rating', 0) / 10.0,  # Normalized rating
                movie.get('vote_count', 0) / 10000.0,  # Normalized vote count
            ]
            numerical_features.append(features)
        
        numerical_matrix = self.scaler.fit_transform(numerical_features)
        
        # Combine text and numerical features
        self.movie_features = np.hstack([
            tfidf_matrix.toarray(),
            numerical_matrix
        ])
        
        # Calculate similarity matrix
        self.movie_similarity_matrix = cosine_similarity(self.movie_features)
        
        return self.movie_features
    
    def get_similar_movies(self, movie_id: str, movie_index_map: Dict[str, int], 
                          top_k: int = 10) -> List[Tuple[str, float]]:
        """Get similar movies based on content features"""
        
        if movie_id not in movie_index_map:
            return []
        
        movie_idx = movie_index_map[movie_id]
        similarity_scores = self.movie_similarity_matrix[movie_idx]
        
        # Get most similar movies
        similar_indices = similarity_scores.argsort()[::-1][1:top_k+1]  # Exclude self
        
        # Map back to movie IDs
        index_to_movie = {v: k for k, v in movie_index_map.items()}
        similar_movies = [
            (index_to_movie[idx], similarity_scores[idx])
            for idx in similar_indices
        ]
        
        return similar_movies
    
    def get_content_recommendations(self, user_profile: UserProfile, 
                                  movies_df: pd.DataFrame, 
                                  movie_index_map: Dict[str, int],
                                  top_k: int = 10) -> List[Tuple[str, float]]:
        """Get content-based recommendations for user"""
        
        # Get user's favorite movies
        liked_movies = [
            rating['movie_id'] for rating in user_profile.rating_history
            if rating['rating'] >= 4.0
        ]
        
        # Calculate user's content profile
        user_content_scores = {}
        
        for movie_id in liked_movies:
            similar_movies = self.get_similar_movies(movie_id, movie_index_map, top_k=50)
            
            for sim_movie_id, similarity in similar_movies:
                if sim_movie_id not in user_content_scores:
                    user_content_scores[sim_movie_id] = 0
                user_content_scores[sim_movie_id] += similarity
        
        # Normalize scores
        if user_content_scores:
            max_score = max(user_content_scores.values())
            for movie_id in user_content_scores:
                user_content_scores[movie_id] /= max_score
        
        # Sort and return top recommendations
        recommendations = sorted(
            user_content_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return recommendations

class HybridRecommendationEngine:
    """Hybrid recommendation engine combining multiple approaches"""
    
    def __init__(self):
        self.ncf_model = None
        self.content_recommender = ContentBasedRecommender()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Recommendation weights
        self.weights = {
            'collaborative': 0.4,
            'content': 0.3,
            'popularity': 0.15,
            'temporal': 0.15
        }
    
    async def initialize_models(self, ratings_df: pd.DataFrame, movies_df: pd.DataFrame):
        """Initialize all recommendation models"""
        
        logger.info("Initializing recommendation models...")
        
        # Initialize NCF model
        num_users = ratings_df['user_id'].nunique()
        num_movies = ratings_df['movie_id'].nunique()
        
        self.ncf_model = NeuralCollaborativeFiltering(
            num_users=num_users,
            num_movies=num_movies,
            embedding_size=128
        )
        
        # Train NCF model (in background)
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.ncf_model.train,
            ratings_df
        )
        
        # Prepare content features
        movie_index_map = {
            movie_id: idx for idx, movie_id in enumerate(movies_df['movie_id'])
        }
        
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self.content_recommender.prepare_movie_features,
            movies_df
        )
        
        # Cache movie index map
        self.movie_index_map = movie_index_map
        self.movies_df = movies_df
        
        logger.info("Models initialized successfully!")
    
    async def get_recommendations(self, request: RecommendationRequest) -> List[MovieRecommendation]:
        """Get hybrid recommendations for user"""
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_result = self.redis_client.get(cache_key)
            
            if cached_result and not request.context.get('refresh_cache', False):
                logger.info(f"Returning cached recommendations for user {request.user_id}")
                return pickle.loads(cached_result)
            
            # Get user profile
            user_profile = await self._get_user_profile(request.user_id)
            if not user_profile:
                return await self._get_popularity_recommendations(request.num_recommendations)
            
            # Get candidate movies
            candidate_movies = await self._get_candidate_movies(user_profile, request)
            
            # Generate recommendations from different approaches
            tasks = []
            
            if request.recommendation_type in ['collaborative', 'hybrid']:
                tasks.append(self._get_collaborative_recommendations(
                    user_profile, candidate_movies, request.num_recommendations
                ))
            
            if request.recommendation_type in ['content', 'hybrid']:
                tasks.append(self._get_content_recommendations(
                    user_profile, candidate_movies, request.num_recommendations
                ))
            
            if request.recommendation_type == 'hybrid':
                tasks.extend([
                    self._get_popularity_recommendations(request.num_recommendations),
                    self._get_temporal_recommendations(user_profile, candidate_movies, request.num_recommendations)
                ])
            
            # Execute all recommendation approaches
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine recommendations
            final_recommendations = self._combine_recommendations(
                results, request.recommendation_type, request.num_recommendations
            )
            
            # Add metadata and format
            enriched_recommendations = await self._enrich_recommendations(final_recommendations)
            
            # Cache results (expire in 1 hour)
            self.redis_client.setex(
                cache_key, 
                3600, 
                pickle.dumps(enriched_recommendations)
            )
            
            logger.info(f"Generated {len(enriched_recommendations)} recommendations for user {request.user_id}")
            return enriched_recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {request.user_id}: {e}")
            return await self._get_fallback_recommendations(request.num_recommendations)
    
    async def _get_collaborative_recommendations(self, user_profile: UserProfile, 
                                              candidate_movies: List[str], 
                                              top_k: int) -> List[Tuple[str, float, str]]:
        """Get collaborative filtering recommendations"""
        
        if not self.ncf_model:
            return []
        
        try:
            movie_scores = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.ncf_model.get_user_recommendations,
                user_profile.user_id,
                candidate_movies,
                top_k
            )
            
            return [(movie_id, score, "collaborative") for movie_id, score in movie_scores]
            
        except Exception as e:
            logger.error(f"Collaborative filtering error: {e}")
            return []
    
    async def _get_content_recommendations(self, user_profile: UserProfile,
                                        candidate_movies: List[str],
                                        top_k: int) -> List[Tuple[str, float, str]]:
        """Get content-based recommendations"""
        
        try:
            content_scores = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.content_recommender.get_content_recommendations,
                user_profile,
                self.movies_df,
                self.movie_index_map,
                top_k
            )
            
            return [(movie_id, score, "content") for movie_id, score in content_scores]
            
        except Exception as e:
            logger.error(f"Content-based filtering error: {e}")
            return []
    
    async def _get_popularity_recommendations(self, top_k: int) -> List[Tuple[str, float, str]]:
        """Get popularity-based recommendations"""
        
        try:
            # Get popular movies (this would come from your database)
            popular_movies = [
                ("movie_popular_1", 4.5, "popularity"),
                ("movie_popular_2", 4.4, "popularity"),
                ("movie_popular_3", 4.3, "popularity"),
            ]
            
            return popular_movies[:top_k]
            
        except Exception as e:
            logger.error(f"Popularity recommendations error: {e}")
            return []
    
    async def _get_temporal_recommendations(self, user_profile: UserProfile,
                                         candidate_movies: List[str],
                                         top_k: int) -> List[Tuple[str, float, str]]:
        """Get time-sensitive recommendations"""
        
        try:
            # Consider time of day, day of week, season, etc.
            current_time = datetime.now()
            
            # Weekend movie recommendations
            if current_time.weekday() >= 5:  # Saturday or Sunday
                temporal_boost = 1.2
            else:
                temporal_boost = 1.0
            
            # Evening time boost for popular movies
            if 18 <= current_time.hour <= 22:
                temporal_boost *= 1.1
            
            # This is a simplified temporal model
            temporal_scores = []
            for movie_id in candidate_movies[:top_k]:
                base_score = 3.5  # Base temporal score
                temporal_scores.append((movie_id, base_score * temporal_boost, "temporal"))
            
            return temporal_scores
            
        except Exception as e:
            logger.error(f"Temporal recommendations error: {e}")
            return []
    
    def _combine_recommendations(self, results: List, recommendation_type: str, 
                               top_k: int) -> List[Tuple[str, float, str]]:
        """Combine recommendations from different approaches"""
        
        combined_scores = {}
        
        for result in results:
            if isinstance(result, Exception):
                continue
            
            for movie_id, score, source in result:
                if movie_id not in combined_scores:
                    combined_scores[movie_id] = {'total': 0, 'sources': []}
                
                # Apply weights based on source
                weight = self.weights.get(source, 0.1)
                combined_scores[movie_id]['total'] += score * weight
                combined_scores[movie_id]['sources'].append(source)
        
        # Sort by combined score
        final_recommendations = [
            (movie_id, data['total'], ','.join(data['sources']))
            for movie_id, data in combined_scores.items()
        ]
        
        final_recommendations.sort(key=lambda x: x[1], reverse=True)
        return final_recommendations[:top_k]
    
    async def _enrich_recommendations(self, recommendations: List[Tuple[str, float, str]]) -> List[MovieRecommendation]:
        """Enrich recommendations with movie metadata"""
        
        enriched = []
        
        for movie_id, score, sources in recommendations:
            # Get movie details (this would query your database)
            movie_data = await self._get_movie_details(movie_id)
            
            if movie_data:
                recommendation = MovieRecommendation(
                    movie_id=movie_id,
                    title=movie_data.get('title', 'Unknown Movie'),
                    predicted_rating=min(score, 5.0),  # Cap at 5.0
                    confidence_score=self._calculate_confidence(score, sources),
                    recommendation_reason=self._generate_reason(sources),
                    genres=movie_data.get('genres', []),
                    release_year=movie_data.get('release_year', 2024),
                    poster_url=movie_data.get('poster_url'),
                    trailer_url=movie_data.get('trailer_url'),
                    metadata={
                        'sources': sources,
                        'raw_score': score
                    }
                )
                enriched.append(recommendation)
        
        return enriched
    
    def _calculate_confidence(self, score: float, sources: str) -> float:
        """Calculate confidence score for recommendation"""
        
        # Base confidence from score
        confidence = min(score / 5.0, 1.0)
        
        # Boost confidence if multiple sources agree
        source_count = len(sources.split(','))
        if source_count >= 2:
            confidence = min(confidence * 1.2, 1.0)
        
        return confidence
    
    def _generate_reason(self, sources: str) -> str:
        """Generate human-readable recommendation reason"""
        
        source_list = sources.split(',')
        
        if 'collaborative' in source_list and 'content' in source_list:
            return "Recommended based on similar users and movie content"
        elif 'collaborative' in source_list:
            return "Users with similar taste also liked this movie"
        elif 'content' in source_list:
            return "Matches your favorite genres and movie preferences"
        elif 'popularity' in source_list:
            return "Currently popular and highly rated"
        elif 'temporal' in source_list:
            return "Perfect for your current time and mood"
        else:
            return "Recommended for you"
    
    async def _get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile for recommendations"""
        
        # This would query your user service/database
        # Returning mock data for demonstration
        return UserProfile(
            user_id=user_id,
            age_group="25-34",
            gender="M",
            location="New York",
            preferred_genres=["Action", "Sci-Fi", "Thriller"],
            preferred_languages=["English"],
            favorite_actors=["Chris Evans", "Scarlett Johansson"],
            favorite_directors=["Christopher Nolan", "Marvel Studios"],
            viewing_history=[
                {"movie_id": "movie_1", "watched_at": datetime.now() - timedelta(days=5)},
                {"movie_id": "movie_2", "watched_at": datetime.now() - timedelta(days=10)}
            ],
            rating_history=[
                {"movie_id": "movie_1", "rating": 4.5, "rated_at": datetime.now() - timedelta(days=5)},
                {"movie_id": "movie_2", "rating": 4.0, "rated_at": datetime.now() - timedelta(days=10)}
            ],
            booking_patterns={
                "preferred_time": "evening",
                "preferred_day": "weekend",
                "booking_frequency": "weekly"
            },
            social_connections=["friend_1", "friend_2"],
            last_updated=datetime.now()
        )
    
    async def _get_candidate_movies(self, user_profile: UserProfile, 
                                  request: RecommendationRequest) -> List[str]:
        """Get candidate movies for recommendation"""
        
        # This would query your movie database
        # Filter based on user preferences, exclude watched movies, etc.
        candidate_movies = [
            f"movie_candidate_{i}" for i in range(1, 101)  # Mock candidate movies
        ]
        
        if request.exclude_watched:
            watched_movie_ids = [item['movie_id'] for item in user_profile.viewing_history]
            candidate_movies = [m for m in candidate_movies if m not in watched_movie_ids]
        
        return candidate_movies
    
    async def _get_movie_details(self, movie_id: str) -> Dict[str, Any]:
        """Get movie details from database"""
        
        # Mock movie data - this would come from your database
        return {
            'title': f'Movie Title {movie_id}',
            'genres': ['Action', 'Adventure'],
            'release_year': 2024,
            'poster_url': f'https://example.com/poster_{movie_id}.jpg',
            'trailer_url': f'https://youtube.com/watch?v={movie_id}',
            'average_rating': 4.2,
            'plot': 'An exciting movie plot...'
        }
    
    async def _get_fallback_recommendations(self, num_recommendations: int) -> List[MovieRecommendation]:
        """Fallback recommendations when main system fails"""
        
        fallback_movies = [
            MovieRecommendation(
                movie_id=f"fallback_{i}",
                title=f"Popular Movie {i}",
                predicted_rating=4.0,
                confidence_score=0.7,
                recommendation_reason="Currently trending",
                genres=["Action", "Adventure"],
                release_year=2024
            )
            for i in range(1, num_recommendations + 1)
        ]
        
        return fallback_movies
    
    def _generate_cache_key(self, request: RecommendationRequest) -> str:
        """Generate cache key for recommendations"""
        
        key_data = f"{request.user_id}_{request.num_recommendations}_{request.recommendation_type}_{request.exclude_watched}"
        return f"rec:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def update_user_feedback(self, user_id: str, movie_id: str, 
                                 feedback_type: str, value: Any):
        """Update recommendation model based on user feedback"""
        
        try:
            feedback_data = {
                'user_id': user_id,
                'movie_id': movie_id,
                'feedback_type': feedback_type,  # 'rating', 'like', 'dislike', 'not_interested'
                'value': value,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store feedback for model retraining
            feedback_key = f"feedback:{user_id}:{movie_id}:{feedback_type}"
            self.redis_client.setex(feedback_key, 86400 * 7, json.dumps(feedback_data))  # Keep for 7 days
            
            # Invalidate user's recommendation cache
            cache_pattern = f"rec:*{user_id}*"
            for key in self.redis_client.scan_iter(match=cache_pattern):
                self.redis_client.delete(key)
            
            logger.info(f"Updated feedback for user {user_id} on movie {movie_id}")
            
        except Exception as e:
            logger.error(f"Error updating user feedback: {e}")

# Global recommendation engine instance
recommendation_engine = HybridRecommendationEngine()

# Utility functions
async def get_personalized_recommendations(user_id: str, num_recommendations: int = 10) -> List[MovieRecommendation]:
    """Get personalized movie recommendations for user"""
    
    request = RecommendationRequest(
        user_id=user_id,
        num_recommendations=num_recommendations,
        recommendation_type="hybrid"
    )
    
    return await recommendation_engine.get_recommendations(request)

async def get_similar_movies(movie_id: str, num_recommendations: int = 10) -> List[MovieRecommendation]:
    """Get movies similar to a given movie"""
    
    # This would use the content-based recommender
    similar_movies = recommendation_engine.content_recommender.get_similar_movies(
        movie_id, 
        recommendation_engine.movie_index_map,
        num_recommendations
    )
    
    # Convert to MovieRecommendation format
    recommendations = []
    for sim_movie_id, similarity in similar_movies:
        movie_data = await recommendation_engine._get_movie_details(sim_movie_id)
        
        if movie_data:
            recommendation = MovieRecommendation(
                movie_id=sim_movie_id,
                title=movie_data.get('title', 'Unknown Movie'),
                predicted_rating=similarity * 5.0,
                confidence_score=similarity,
                recommendation_reason="Similar to your selected movie",
                genres=movie_data.get('genres', []),
                release_year=movie_data.get('release_year', 2024),
                poster_url=movie_data.get('poster_url'),
                trailer_url=movie_data.get('trailer_url')
            )
            recommendations.append(recommendation)
    
    return recommendations

async def update_recommendation_feedback(user_id: str, movie_id: str, rating: float):
    """Update user's movie rating for improved recommendations"""
    
    await recommendation_engine.update_user_feedback(
        user_id=user_id,
        movie_id=movie_id,
        feedback_type="rating",
        value=rating
    )

async def get_trending_recommendations(num_recommendations: int = 10) -> List[MovieRecommendation]:
    """Get trending movie recommendations"""
    
    request = RecommendationRequest(
        user_id="anonymous",
        num_recommendations=num_recommendations,
        recommendation_type="popularity"
    )
    
    return await recommendation_engine.get_recommendations(request)