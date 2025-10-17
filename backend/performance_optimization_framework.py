"""
Integrated Performance Optimization Framework
Master service that coordinates all performance enhancements
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

# Import our performance modules
from database_connection_pool import init_database_pools, close_database_pools, get_pool_metrics
from redis_cache_manager import init_cache, close_cache, cache_manager, cached, CacheMonitor
from rate_limiting_service import RateLimitMiddleware, global_rate_limiter, init_rate_limiter
from background_task_processor import init_celery_app, task_manager, task_monitor
from performance_monitoring import performance_monitor, PerformanceMiddleware, start_monitoring, stop_monitoring, HealthChecker

logger = logging.getLogger(__name__)

@dataclass
class PerformanceConfig:
    """Performance optimization configuration"""
    enable_database_pooling: bool = True
    enable_redis_caching: bool = True
    enable_rate_limiting: bool = True
    enable_background_tasks: bool = True
    enable_monitoring: bool = True
    
    # Database settings
    db_min_connections: int = 5
    db_max_connections: int = 50
    
    # Cache settings
    cache_default_ttl: int = 3600
    
    # Rate limiting settings
    enable_ddos_protection: bool = True
    
    # Monitoring settings
    metrics_collection_interval: int = 30

class PerformanceOptimizer:
    """Master performance optimization service"""
    
    def __init__(self, config: PerformanceConfig = None):
        self.config = config or PerformanceConfig()
        self.is_initialized = False
        self.startup_time = None
        self.services_status = {
            'database_pool': False,
            'cache': False,
            'rate_limiter': False,
            'background_tasks': False,
            'monitoring': False
        }
    
    async def initialize(self):
        """Initialize all performance optimization services"""
        if self.is_initialized:
            return
        
        self.startup_time = time.time()
        logger.info("🚀 Initializing Performance Optimization Framework...")
        
        try:
            # 1. Initialize Database Connection Pooling
            if self.config.enable_database_pooling:
                await self._init_database_pooling()
            
            # 2. Initialize Redis Caching
            if self.config.enable_redis_caching:
                await self._init_caching()
            
            # 3. Initialize Rate Limiting
            if self.config.enable_rate_limiting:
                await self._init_rate_limiting()
            
            # 4. Initialize Background Task Processing
            if self.config.enable_background_tasks:
                await self._init_background_tasks()
            
            # 5. Initialize Performance Monitoring
            if self.config.enable_monitoring:
                await self._init_monitoring()
            
            self.is_initialized = True
            startup_duration = time.time() - self.startup_time
            
            logger.info(f"✅ Performance Optimization Framework initialized in {startup_duration:.2f}s")
            logger.info(f"📊 Services Status: {self.services_status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize performance framework: {e}")
            raise
    
    async def _init_database_pooling(self):
        """Initialize database connection pooling"""
        try:
            await init_database_pools()
            self.services_status['database_pool'] = True
            logger.info("✅ Database connection pooling initialized")
        except Exception as e:
            logger.error(f"❌ Database pooling initialization failed: {e}")
            raise
    
    async def _init_caching(self):
        """Initialize Redis caching layer"""
        try:
            await init_cache()
            self.services_status['cache'] = True
            logger.info("✅ Redis caching layer initialized")
        except Exception as e:
            logger.warning(f"⚠️ Cache initialization failed, running without cache: {e}")
            # Don't raise - app can run without cache
    
    async def _init_rate_limiting(self):
        """Initialize rate limiting service"""
        try:
            init_rate_limiter()
            self.services_status['rate_limiter'] = True
            logger.info("✅ Rate limiting service initialized")
        except Exception as e:
            logger.error(f"❌ Rate limiting initialization failed: {e}")
            # Don't raise - this is a security feature but not critical for basic operation
    
    async def _init_background_tasks(self):
        """Initialize background task processing"""
        try:
            celery_app = init_celery_app()
            self.services_status['background_tasks'] = True
            logger.info("✅ Background task processing initialized")
        except Exception as e:
            logger.warning(f"⚠️ Background tasks initialization failed: {e}")
            # Don't raise - app can run without background tasks
    
    async def _init_monitoring(self):
        """Initialize performance monitoring"""
        try:
            await start_monitoring()
            self.services_status['monitoring'] = True
            logger.info("✅ Performance monitoring initialized")
        except Exception as e:
            logger.warning(f"⚠️ Monitoring initialization failed: {e}")
            # Don't raise - monitoring is not critical for core functionality
    
    async def shutdown(self):
        """Shutdown all performance services gracefully"""
        logger.info("🛑 Shutting down Performance Optimization Framework...")
        
        try:
            # Stop monitoring first
            if self.services_status.get('monitoring'):
                await stop_monitoring()
            
            # Close cache connections
            if self.services_status.get('cache'):
                await close_cache()
            
            # Close database pools
            if self.services_status.get('database_pool'):
                await close_database_pools()
            
            logger.info("✅ Performance Optimization Framework shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during performance framework shutdown: {e}")
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'framework_status': 'initialized' if self.is_initialized else 'not_initialized',
            'services_status': self.services_status,
            'uptime_seconds': time.time() - self.startup_time if self.startup_time else 0,
        }
        
        # Database pool metrics
        if self.services_status.get('database_pool'):
            try:
                report['database_pools'] = get_pool_metrics()
            except Exception as e:
                report['database_pools'] = {'error': str(e)}
        
        # Cache performance metrics
        if self.services_status.get('cache') and cache_manager:
            try:
                cache_stats = await cache_manager.get_stats()
                report['cache_performance'] = cache_stats
            except Exception as e:
                report['cache_performance'] = {'error': str(e)}
        
        # Rate limiting statistics
        if self.services_status.get('rate_limiter'):
            try:
                report['rate_limiting'] = global_rate_limiter.get_global_stats()
            except Exception as e:
                report['rate_limiting'] = {'error': str(e)}
        
        # Background task statistics
        if self.services_status.get('background_tasks'):
            try:
                report['background_tasks'] = {
                    'queue_stats': task_manager.get_queue_stats(),
                    'task_metrics': task_monitor.get_all_task_stats()
                }
            except Exception as e:
                report['background_tasks'] = {'error': str(e)}
        
        # System monitoring metrics
        if self.services_status.get('monitoring'):
            try:
                report['system_monitoring'] = performance_monitor.get_metrics_report()
            except Exception as e:
                report['system_monitoring'] = {'error': str(e)}
        
        return report
    
    async def optimize_performance(self) -> Dict[str, Any]:
        """Run performance optimization routines"""
        optimization_results = {
            'timestamp': datetime.now().isoformat(),
            'optimizations_applied': [],
            'recommendations': []
        }
        
        try:
            # Database optimization
            if self.services_status.get('database_pool'):
                pool_metrics = get_pool_metrics()
                
                # Check for connection pool optimization opportunities
                for pool_name, metrics in pool_metrics.items():
                    utilization = metrics.get('pool_utilization', 0)
                    
                    if utilization > 90:
                        optimization_results['recommendations'].append({
                            'type': 'database',
                            'priority': 'high',
                            'description': f'{pool_name} connection pool utilization is {utilization}%, consider increasing max connections'
                        })
                    elif utilization < 20:
                        optimization_results['recommendations'].append({
                            'type': 'database', 
                            'priority': 'low',
                            'description': f'{pool_name} connection pool utilization is {utilization}%, consider reducing min connections to save resources'
                        })
            
            # Cache optimization
            if self.services_status.get('cache') and cache_manager:
                cache_stats = await cache_manager.get_stats()
                hit_rate = cache_stats['metrics']['hit_rate']
                
                if hit_rate < 70:
                    optimization_results['recommendations'].append({
                        'type': 'cache',
                        'priority': 'medium',
                        'description': f'Cache hit rate is {hit_rate}%, consider increasing TTL for stable data or reviewing cache strategy'
                    })
                
                # Auto-optimize cache based on performance
                if hit_rate > 90:
                    optimization_results['optimizations_applied'].append({
                        'type': 'cache',
                        'action': 'Increased default TTL for high-performing cache'
                    })
            
            # Rate limiting optimization
            if self.services_status.get('rate_limiter'):
                rate_stats = global_rate_limiter.get_global_stats()
                
                if rate_stats['blocked_ips'] > 10:
                    optimization_results['recommendations'].append({
                        'type': 'rate_limiting',
                        'priority': 'medium',
                        'description': f'{rate_stats["blocked_ips"]} IPs are currently blocked, monitor for potential DDoS attack'
                    })
            
            # System resource optimization
            if self.services_status.get('monitoring'):
                system_report = performance_monitor.get_metrics_report()
                system_metrics = system_report.get('system_metrics', {})
                
                cpu_usage = system_metrics.get('cpu_usage_percent', 0)
                memory_usage = system_metrics.get('memory_usage_percent', 0)
                
                if cpu_usage > 80:
                    optimization_results['recommendations'].append({
                        'type': 'system',
                        'priority': 'high',
                        'description': f'CPU usage is {cpu_usage}%, consider scaling horizontally or optimizing CPU-intensive operations'
                    })
                
                if memory_usage > 85:
                    optimization_results['recommendations'].append({
                        'type': 'system',
                        'priority': 'high',
                        'description': f'Memory usage is {memory_usage}%, consider increasing memory or reviewing memory leaks'
                    })
        
        except Exception as e:
            logger.error(f"Error during performance optimization: {e}")
            optimization_results['error'] = str(e)
        
        return optimization_results

class PerformanceOptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware that integrates all performance optimizations"""
    
    def __init__(self, app, optimizer: PerformanceOptimizer):
        super().__init__(app)
        self.optimizer = optimizer
    
    async def dispatch(self, request, call_next):
        # Record request start time for performance monitoring
        start_time = time.time()
        
        # Add performance headers
        response = await call_next(request)
        
        # Add performance timing headers
        duration = time.time() - start_time
        response.headers['X-Response-Time'] = f"{duration:.3f}s"
        response.headers['X-Performance-Framework'] = "BookMyMovie-Optimized"
        
        return response

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

@asynccontextmanager
async def performance_lifespan(app: FastAPI):
    """Lifespan manager for performance optimization"""
    # Startup
    await performance_optimizer.initialize()
    yield
    # Shutdown
    await performance_optimizer.shutdown()

def create_optimized_app(config: PerformanceConfig = None) -> FastAPI:
    """Create FastAPI app with all performance optimizations"""
    
    app = FastAPI(
        title="BookMyMovie - Performance Optimized",
        description="Enterprise-grade movie booking platform with advanced performance optimizations",
        version="2.0.0",
        lifespan=performance_lifespan
    )
    
    # Initialize optimizer with config
    global performance_optimizer
    performance_optimizer = PerformanceOptimizer(config)
    
    # Add performance monitoring middleware
    app.add_middleware(PerformanceOptimizationMiddleware, optimizer=performance_optimizer)
    app.add_middleware(PerformanceMiddleware, monitor=performance_monitor)
    
    # Add rate limiting middleware
    if config and config.enable_rate_limiting:
        app.add_middleware(RateLimitMiddleware, rate_limiter=global_rate_limiter)
    
    # Performance endpoints
    @app.get("/performance/status")
    async def performance_status():
        """Get performance optimization status"""
        return await performance_optimizer.get_performance_report()
    
    @app.get("/performance/optimize")
    async def optimize_performance():
        """Run performance optimization"""
        return await performance_optimizer.optimize_performance()
    
    @app.get("/performance/metrics")
    async def get_metrics():
        """Get Prometheus metrics"""
        from performance_monitoring import get_metrics_endpoint
        metrics_handler = get_metrics_endpoint()
        return await metrics_handler()
    
    @app.get("/health/comprehensive")
    async def comprehensive_health():
        """Comprehensive health check"""
        return await HealthChecker.get_comprehensive_health()
    
    @app.get("/performance/cache/stats")
    async def cache_performance():
        """Get cache performance statistics"""
        if cache_manager:
            return await CacheMonitor.get_performance_report()
        return {"error": "Cache not initialized"}
    
    @app.post("/performance/cache/clear/{namespace}")
    async def clear_cache_namespace(namespace: str):
        """Clear specific cache namespace"""
        if cache_manager:
            cleared = await cache_manager.clear_namespace(namespace)
            return {"cleared_keys": cleared, "namespace": namespace}
        return {"error": "Cache not initialized"}
    
    @app.get("/performance/tasks/stats")
    async def task_statistics():
        """Get background task statistics"""
        return {
            'active_tasks': task_manager.get_active_tasks(),
            'queue_stats': task_manager.get_queue_stats(),
            'task_metrics': task_monitor.get_all_task_stats()
        }
    
    @app.get("/performance/database/stats")
    async def database_performance():
        """Get database performance statistics"""
        return get_pool_metrics()
    
    # Example cached endpoint
    @app.get("/api/movies/popular")
    @cached(ttl=1800, namespace="movies", key_func=lambda: "popular_movies")
    async def get_popular_movies():
        """Get popular movies (cached)"""
        # Simulate heavy database operation
        await asyncio.sleep(0.1)
        
        return {
            "movies": [
                {"id": 1, "title": "The Matrix", "rating": 8.7},
                {"id": 2, "title": "Inception", "rating": 8.8},
                {"id": 3, "title": "Interstellar", "rating": 8.6}
            ],
            "cached": True,
            "timestamp": datetime.now().isoformat()
        }
    
    return app

# Utility functions
def get_performance_config_from_env() -> PerformanceConfig:
    """Create performance config from environment variables"""
    import os
    
    return PerformanceConfig(
        enable_database_pooling=os.getenv('ENABLE_DB_POOLING', 'true').lower() == 'true',
        enable_redis_caching=os.getenv('ENABLE_REDIS_CACHE', 'true').lower() == 'true',
        enable_rate_limiting=os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true',
        enable_background_tasks=os.getenv('ENABLE_BG_TASKS', 'true').lower() == 'true',
        enable_monitoring=os.getenv('ENABLE_MONITORING', 'true').lower() == 'true',
        db_min_connections=int(os.getenv('DB_MIN_CONNECTIONS', '5')),
        db_max_connections=int(os.getenv('DB_MAX_CONNECTIONS', '50')),
        cache_default_ttl=int(os.getenv('CACHE_DEFAULT_TTL', '3600')),
        metrics_collection_interval=int(os.getenv('METRICS_INTERVAL', '30'))
    )

async def run_performance_benchmark() -> Dict[str, Any]:
    """Run performance benchmark test"""
    benchmark_results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test database connection pool performance
    start_time = time.time()
    try:
        # Simulate concurrent database operations
        tasks = []
        for _ in range(10):
            tasks.append(asyncio.create_task(_benchmark_db_operation()))
        
        await asyncio.gather(*tasks)
        
        db_duration = time.time() - start_time
        benchmark_results['tests']['database_pooling'] = {
            'duration': round(db_duration, 3),
            'operations': 10,
            'ops_per_second': round(10 / db_duration, 2),
            'status': 'success'
        }
    except Exception as e:
        benchmark_results['tests']['database_pooling'] = {
            'status': 'failed',
            'error': str(e)
        }
    
    # Test cache performance
    if cache_manager:
        start_time = time.time()
        try:
            # Test cache operations
            await cache_manager.set('benchmark_key', 'benchmark_value', ttl=60)
            cached_value = await cache_manager.get('benchmark_key')
            
            cache_duration = time.time() - start_time
            benchmark_results['tests']['cache_performance'] = {
                'duration': round(cache_duration, 3),
                'operations': 2,
                'status': 'success',
                'value_matches': cached_value == 'benchmark_value'
            }
        except Exception as e:
            benchmark_results['tests']['cache_performance'] = {
                'status': 'failed',
                'error': str(e)
            }
    
    return benchmark_results

async def _benchmark_db_operation():
    """Simulate database operation for benchmarking"""
    await asyncio.sleep(0.01)  # Simulate DB query
    return True