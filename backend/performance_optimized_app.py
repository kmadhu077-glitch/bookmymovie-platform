"""
Performance-Optimized BookMyMovie Application
Main application with integrated performance enhancements
"""

import asyncio
import logging
import os
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import performance optimization framework
from performance_optimization_framework import (
    create_optimized_app, 
    get_performance_config_from_env,
    performance_optimizer,
    run_performance_benchmark
)

# Import existing services
from enhanced_booking_service import BookingService
from enhanced_user_service import UserService
from enhanced_catalog_service import CatalogService
from enhanced_payment_service import PaymentService
from ai_recommendation_engine import AIRecommendationEngine
from notification_service import NotificationService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceOptimizedBookMyMovie:
    """Main application class with performance optimizations"""
    
    def __init__(self):
        self.config = get_performance_config_from_env()
        self.app = None
        self.services = {}
        
    def create_app(self) -> FastAPI:
        """Create the optimized FastAPI application"""
        
        # Create optimized app with performance framework
        self.app = create_optimized_app(self.config)
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount static files
        if os.path.exists("static"):
            self.app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # Initialize services
        self._init_services()
        
        # Setup routes
        self._setup_routes()
        
        return self.app
    
    def _init_services(self):
        """Initialize all application services"""
        logger.info("🔧 Initializing application services...")
        
        try:
            self.services = {
                'booking': BookingService(),
                'user': UserService(), 
                'catalog': CatalogService(),
                'payment': PaymentService(),
                'ai_recommendations': AIRecommendationEngine(),
                'notifications': NotificationService()
            }
            logger.info("✅ Application services initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            raise
    
    def _setup_routes(self):
        """Setup all application routes"""
        
        # Home and basic routes
        @self.app.get("/")
        async def root():
            return {
                "message": "Welcome to BookMyMovie - Performance Optimized Edition",
                "version": "2.0.0",
                "features": [
                    "Advanced Database Connection Pooling",
                    "Redis Caching Layer",
                    "Intelligent Rate Limiting",
                    "Background Task Processing", 
                    "Real-time Performance Monitoring",
                    "Prometheus Metrics Integration"
                ],
                "performance_status": await performance_optimizer.get_performance_report()
            }
        
        # User Management Routes
        @self.app.post("/api/users/register")
        async def register_user(user_data: dict, background_tasks: BackgroundTasks):
            """Register new user with performance optimizations"""
            try:
                # Use cached user service
                result = await self._cached_operation(
                    'user_registration',
                    self.services['user'].register_user,
                    user_data,
                    ttl=0  # Don't cache registration
                )
                
                # Queue welcome email in background
                background_tasks.add_task(
                    self._send_welcome_email,
                    user_data.get('email'),
                    user_data.get('name')
                )
                
                return result
            except Exception as e:
                logger.error(f"User registration failed: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/users/{user_id}")
        async def get_user_profile(user_id: str):
            """Get user profile with caching"""
            return await self._cached_operation(
                f'user_profile_{user_id}',
                self.services['user'].get_user_profile,
                user_id,
                ttl=1800  # Cache for 30 minutes
            )
        
        # Movie Catalog Routes
        @self.app.get("/api/movies")
        async def get_movies(
            page: int = 1,
            limit: int = 20,
            genre: str = None,
            search: str = None
        ):
            """Get movies with advanced caching"""
            cache_key = f"movies_p{page}_l{limit}_g{genre}_s{search}"
            
            return await self._cached_operation(
                cache_key,
                self.services['catalog'].get_movies,
                page, limit, genre, search,
                ttl=3600  # Cache for 1 hour
            )
        
        @self.app.get("/api/movies/{movie_id}")
        async def get_movie_details(movie_id: str):
            """Get movie details with caching"""
            return await self._cached_operation(
                f'movie_details_{movie_id}',
                self.services['catalog'].get_movie_details,
                movie_id,
                ttl=7200  # Cache for 2 hours
            )
        
        @self.app.get("/api/movies/{movie_id}/recommendations")
        async def get_movie_recommendations(movie_id: str, user_id: str = None):
            """Get AI-powered movie recommendations with caching"""
            cache_key = f"recommendations_{movie_id}_{user_id}"
            
            return await self._cached_operation(
                cache_key,
                self.services['ai_recommendations'].get_similar_movies,
                movie_id, user_id,
                ttl=1800  # Cache for 30 minutes
            )
        
        # Booking Routes
        @self.app.post("/api/bookings")
        async def create_booking(booking_data: dict, background_tasks: BackgroundTasks):
            """Create booking with performance optimizations"""
            try:
                # Create booking (no caching for write operations)
                result = await self.services['booking'].create_booking(booking_data)
                
                # Queue confirmation tasks in background
                background_tasks.add_task(
                    self._process_booking_confirmation,
                    result.get('booking_id'),
                    booking_data.get('user_email')
                )
                
                return result
            except Exception as e:
                logger.error(f"Booking creation failed: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/bookings/{booking_id}")
        async def get_booking_details(booking_id: str):
            """Get booking details with caching"""
            return await self._cached_operation(
                f'booking_details_{booking_id}',
                self.services['booking'].get_booking_details,
                booking_id,
                ttl=600  # Cache for 10 minutes
            )
        
        @self.app.get("/api/users/{user_id}/bookings")
        async def get_user_bookings(user_id: str):
            """Get user bookings with caching"""
            return await self._cached_operation(
                f'user_bookings_{user_id}',
                self.services['booking'].get_user_bookings,
                user_id,
                ttl=300  # Cache for 5 minutes
            )
        
        # Payment Routes
        @self.app.post("/api/payments/process")
        async def process_payment(payment_data: dict, background_tasks: BackgroundTasks):
            """Process payment with background fraud detection"""
            try:
                # Process payment
                result = await self.services['payment'].process_payment(payment_data)
                
                # Queue fraud detection in background
                background_tasks.add_task(
                    self._fraud_detection_check,
                    payment_data,
                    result.get('transaction_id')
                )
                
                return result
            except Exception as e:
                logger.error(f"Payment processing failed: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        # Search Routes with Performance Optimization
        @self.app.get("/api/search")
        async def search_movies(q: str, page: int = 1, limit: int = 10):
            """Advanced search with caching and performance tracking"""
            import hashlib
            
            # Create cache key from query
            query_hash = hashlib.md5(f"{q}_{page}_{limit}".encode()).hexdigest()
            cache_key = f"search_results_{query_hash}"
            
            # Record search analytics
            from performance_monitoring import performance_monitor
            performance_monitor.record_movie_view(f"search:{q}")
            
            return await self._cached_operation(
                cache_key,
                self.services['catalog'].search_movies,
                q, page, limit,
                ttl=1800  # Cache search results for 30 minutes
            )
        
        # Analytics and Performance Routes
        @self.app.get("/api/analytics/performance")
        async def get_performance_analytics():
            """Get detailed performance analytics"""
            return {
                "performance_report": await performance_optimizer.get_performance_report(),
                "optimization_suggestions": await performance_optimizer.optimize_performance(),
                "benchmark_results": await run_performance_benchmark()
            }
        
        @self.app.post("/api/analytics/benchmark")
        async def run_benchmark():
            """Run performance benchmark"""
            return await run_performance_benchmark()
        
        # Admin Routes
        @self.app.get("/api/admin/performance/dashboard")
        async def admin_performance_dashboard():
            """Admin performance dashboard"""
            return await performance_optimizer.get_performance_report()
        
        @self.app.post("/api/admin/cache/warm")
        async def warm_cache(background_tasks: BackgroundTasks):
            """Warm up cache with popular data"""
            background_tasks.add_task(self._warm_cache)
            return {"message": "Cache warming initiated"}
        
        @self.app.post("/api/admin/performance/optimize")
        async def trigger_optimization():
            """Trigger performance optimization"""
            return await performance_optimizer.optimize_performance()
    
    async def _cached_operation(self, cache_key: str, func, *args, ttl: int = 3600, **kwargs):
        """Generic cached operation wrapper"""
        from redis_cache_manager import cache_manager
        
        if cache_manager:
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key, namespace='api')
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            if ttl > 0:  # Only cache if TTL > 0
                await cache_manager.set(cache_key, result, ttl, namespace='api')
            
            return result
        else:
            # No cache available, execute directly
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
    
    async def _send_welcome_email(self, email: str, name: str):
        """Background task: Send welcome email"""
        try:
            await self.services['notifications'].send_email(
                to=email,
                subject="Welcome to BookMyMovie!",
                template="welcome",
                context={"name": name}
            )
            logger.info(f"Welcome email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {e}")
    
    async def _process_booking_confirmation(self, booking_id: str, user_email: str):
        """Background task: Process booking confirmation"""
        try:
            # Send confirmation email
            await self.services['notifications'].send_booking_confirmation(
                booking_id=booking_id,
                user_email=user_email
            )
            
            # Update analytics
            from performance_monitoring import performance_monitor
            performance_monitor.record_booking('confirmed', 'unknown', 0.0)
            
            logger.info(f"Booking confirmation processed for {booking_id}")
        except Exception as e:
            logger.error(f"Failed to process booking confirmation {booking_id}: {e}")
    
    async def _fraud_detection_check(self, payment_data: dict, transaction_id: str):
        """Background task: Fraud detection"""
        try:
            # Simulate fraud detection analysis
            await asyncio.sleep(2)  # Simulate processing time
            
            # This would integrate with fraud detection service
            fraud_score = 0.1  # Placeholder
            
            if fraud_score > 0.8:
                # High fraud risk - flag for review
                logger.warning(f"High fraud risk detected for transaction {transaction_id}")
            
            logger.info(f"Fraud detection completed for transaction {transaction_id}")
        except Exception as e:
            logger.error(f"Fraud detection failed for transaction {transaction_id}: {e}")
    
    async def _warm_cache(self):
        """Background task: Warm up cache with popular data"""
        try:
            logger.info("Starting cache warm-up process...")
            
            # Warm up popular movies
            popular_movies = await self.services['catalog'].get_popular_movies()
            
            # Warm up movie categories
            categories = ['action', 'comedy', 'drama', 'thriller', 'sci-fi']
            for category in categories:
                await self.services['catalog'].get_movies_by_genre(category)
            
            logger.info("Cache warm-up completed successfully")
        except Exception as e:
            logger.error(f"Cache warm-up failed: {e}")

def create_app() -> FastAPI:
    """Factory function to create the optimized app"""
    app_instance = PerformanceOptimizedBookMyMovie()
    return app_instance.create_app()

# Create app instance
app = create_app()

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║              BookMyMovie Performance Optimized                 ║
║                    🚀 Enterprise Edition                       ║
╚════════════════════════════════════════════════════════════════╝

🎯 PERFORMANCE FEATURES ENABLED:
──────────────────────────────────────────────────────────────────
🔄 Database Connection Pooling    → 5-50 concurrent connections
⚡ Redis Caching Layer           → Intelligent TTL management
🛡️  Advanced Rate Limiting       → DDoS protection & smart throttling  
🔧 Background Task Processing     → Celery distributed task queue
📊 Real-time Monitoring          → Prometheus metrics & alerting
🚀 Performance Middleware        → Request timing & optimization

🌐 ENHANCED API ENDPOINTS:
──────────────────────────────────────────────────────────────────
📱 API Routes                    → /api/* (with caching & rate limiting)
📊 Performance Analytics         → /api/analytics/performance
🔧 Admin Performance Dashboard   → /api/admin/performance/dashboard
📈 Prometheus Metrics           → /performance/metrics
💚 Health Checks                → /health/comprehensive

🚨 MONITORING & OPTIMIZATION:
──────────────────────────────────────────────────────────────────
• Real-time performance tracking with automatic optimization
• Background task processing for heavy operations
• Intelligent caching with Redis cluster support
• Advanced rate limiting with DDoS protection
• Comprehensive metrics collection and alerting
""")
    
    # Run with optimized settings
    uvicorn.run(
        "performance_optimized_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for production performance
        workers=1,     # Use multiple workers in production
        loop="uvloop", # Use uvloop for better performance
        log_level="info",
        access_log=True
    )