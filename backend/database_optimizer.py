#!/usr/bin/env python3
"""
Database Optimization for BookMyMovie Platform
Indexes, Connection Pooling, and Query Performance Enhancements
"""

import logging
from sqlalchemy import text, Index, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from models import Base, User, Movie, Theater, Screen, Showtime, Booking, Payment, Review
from db_config import SQLITE_URL
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Database performance optimization manager"""
    
    def __init__(self):
        self.database_url = SQLITE_URL
        self.optimized_engine = None
        
    def create_optimized_engine(self) -> Engine:
        """Create optimized database engine with connection pooling"""
        
        # Enhanced connection pool settings
        engine = create_engine(
            self.database_url,
            # Connection pool settings
            poolclass=QueuePool,
            pool_size=10,              # Number of connections to maintain
            max_overflow=20,           # Additional connections beyond pool_size
            pool_pre_ping=True,        # Validate connections before use
            pool_recycle=3600,         # Recycle connections after 1 hour
            
            # Query optimization
            echo=False,                # Set to True for SQL debugging
            future=True,               # Use SQLAlchemy 2.0 style
            
            # SQLite specific optimizations
            connect_args={
                "check_same_thread": False,
                # SQLite performance optimizations
                "isolation_level": None,  # Enable autocommit mode
            } if "sqlite" in self.database_url else {}
        )
        
        # SQLite-specific optimizations
        if "sqlite" in self.database_url:
            with engine.connect() as conn:
                # Enable WAL mode for better concurrency
                conn.execute(text("PRAGMA journal_mode = WAL"))
                
                # Increase cache size (negative value = KB)
                conn.execute(text("PRAGMA cache_size = -64000"))  # 64MB cache
                
                # Optimize synchronization for development
                conn.execute(text("PRAGMA synchronous = NORMAL"))
                
                # Memory-mapped I/O
                conn.execute(text("PRAGMA mmap_size = 268435456"))  # 256MB
                
                # Optimize temp store
                conn.execute(text("PRAGMA temp_store = MEMORY"))
                
                conn.commit()
                
        logger.info("✅ Optimized database engine created")
        self.optimized_engine = engine
        return engine
    
    def create_performance_indexes(self):
        """Create strategic database indexes for better query performance"""
        
        if not self.optimized_engine:
            self.create_optimized_engine()
            
        with self.optimized_engine.connect() as conn:
            
            # User table indexes
            user_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
                "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)",
                "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(username)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email)"
            ]
            
            # Movie table indexes
            movie_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title)",
                "CREATE INDEX IF NOT EXISTS idx_movies_genre ON movies(genre)",
                "CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies(rating)",
                "CREATE INDEX IF NOT EXISTS idx_movies_release_date ON movies(release_date)",
                "CREATE INDEX IF NOT EXISTS idx_movies_duration ON movies(duration)",
                "CREATE INDEX IF NOT EXISTS idx_movies_active ON movies(is_active)"
            ]
            
            # Theater and Screen indexes
            theater_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_theaters_name ON theaters(name)",
                "CREATE INDEX IF NOT EXISTS idx_theaters_location ON theaters(location)",
                "CREATE INDEX IF NOT EXISTS idx_screens_theater_id ON screens(theater_id)",
                "CREATE INDEX IF NOT EXISTS idx_screens_name ON screens(name)"
            ]
            
            # Showtime indexes (critical for booking performance)
            showtime_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_showtimes_movie_id ON showtimes(movie_id)",
                "CREATE INDEX IF NOT EXISTS idx_showtimes_screen_id ON showtimes(screen_id)",
                "CREATE INDEX IF NOT EXISTS idx_showtimes_show_date ON showtimes(show_date)",
                "CREATE INDEX IF NOT EXISTS idx_showtimes_show_time ON showtimes(show_time)",
                "CREATE INDEX IF NOT EXISTS idx_showtimes_movie_date ON showtimes(movie_id, show_date)",
                "CREATE INDEX IF NOT EXISTS idx_showtimes_screen_date ON showtimes(screen_id, show_date)"
            ]
            
            # Booking indexes (high frequency queries)
            booking_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_bookings_showtime_id ON bookings(showtime_id)",
                "CREATE INDEX IF NOT EXISTS idx_bookings_booking_date ON bookings(booking_date)",
                "CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(booking_status)",
                "CREATE INDEX IF NOT EXISTS idx_bookings_user_date ON bookings(user_id, booking_date)",
                "CREATE INDEX IF NOT EXISTS idx_bookings_showtime_status ON bookings(showtime_id, booking_status)"
            ]
            
            # Payment indexes (financial queries)
            payment_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_payments_booking_id ON payments(booking_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date)",
                "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(payment_status)",
                "CREATE INDEX IF NOT EXISTS idx_payments_amount ON payments(amount)",
                "CREATE INDEX IF NOT EXISTS idx_payments_user_date ON payments(user_id, payment_date)",
                "CREATE INDEX IF NOT EXISTS idx_payments_fraud_score ON payments(fraud_score)"
            ]
            
            # Review indexes
            review_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_reviews_movie_id ON reviews(movie_id)",
                "CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating)",
                "CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at)"
            ]
            
            # Analytics indexes
            analytics_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics(event_type)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_analytics_event_date ON analytics(event_type, timestamp)"
            ]
            
            # Execute all index creation statements
            all_indexes = (user_indexes + movie_indexes + theater_indexes + 
                          showtime_indexes + booking_indexes + payment_indexes +
                          review_indexes + analytics_indexes)
            
            success_count = 0
            for index_sql in all_indexes:
                try:
                    conn.execute(text(index_sql))
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
            
            conn.commit()
            
        logger.info(f"✅ Created {success_count}/{len(all_indexes)} database indexes")
        return success_count
    
    def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze database query performance"""
        
        if not self.optimized_engine:
            self.create_optimized_engine()
            
        performance_stats = {}
        
        with self.optimized_engine.connect() as conn:
            
            # Test common query patterns
            test_queries = [
                ("user_lookup", "SELECT * FROM users WHERE username = 'testuser' LIMIT 1"),
                ("movie_search", "SELECT * FROM movies WHERE title LIKE '%action%' LIMIT 10"),
                ("showtime_lookup", "SELECT * FROM showtimes WHERE show_date = date('now') LIMIT 20"),
                ("user_bookings", "SELECT * FROM bookings WHERE user_id = 1 ORDER BY booking_date DESC LIMIT 10"),
                ("payment_history", "SELECT * FROM payments WHERE user_id = 1 ORDER BY payment_date DESC LIMIT 10")
            ]
            
            for query_name, sql in test_queries:
                try:
                    start_time = time.time()
                    result = conn.execute(text(sql))
                    result.fetchall()  # Ensure full query execution
                    end_time = time.time()
                    
                    performance_stats[query_name] = {
                        "execution_time_ms": round((end_time - start_time) * 1000, 2),
                        "status": "success"
                    }
                    
                except Exception as e:
                    performance_stats[query_name] = {
                        "execution_time_ms": 0,
                        "status": "error",
                        "error": str(e)
                    }
        
        return performance_stats
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        
        if not self.optimized_engine:
            self.create_optimized_engine()
            
        stats = {}
        
        with self.optimized_engine.connect() as conn:
            
            # Table row counts
            tables = ['users', 'movies', 'theaters', 'screens', 'showtimes', 
                     'bookings', 'payments', 'reviews', 'analytics', 'admins', 'notifications']
            
            table_stats = {}
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
                    count = result.fetchone()[0]
                    table_stats[table] = count
                except Exception as e:
                    table_stats[table] = f"Error: {e}"
            
            stats['table_counts'] = table_stats
            
            # SQLite specific stats
            if "sqlite" in self.database_url:
                try:
                    # Database size
                    result = conn.execute(text("PRAGMA page_count"))
                    page_count = result.fetchone()[0]
                    
                    result = conn.execute(text("PRAGMA page_size"))
                    page_size = result.fetchone()[0]
                    
                    db_size_bytes = page_count * page_size
                    db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
                    
                    # Cache hit ratio
                    result = conn.execute(text("PRAGMA cache_size"))
                    cache_size = result.fetchone()[0]
                    
                    stats['database_info'] = {
                        "size_mb": db_size_mb,
                        "page_count": page_count,
                        "page_size": page_size,
                        "cache_size": cache_size
                    }
                    
                except Exception as e:
                    stats['database_info'] = f"Error: {e}"
        
        return stats
    
    def optimize_database(self) -> Dict[str, Any]:
        """Run complete database optimization"""
        
        logger.info("🚀 Starting database optimization...")
        start_time = time.time()
        
        results = {
            "optimization_start": time.time(),
            "steps": {}
        }
        
        # Step 1: Create optimized engine
        try:
            self.create_optimized_engine()
            results['steps']['engine_optimization'] = "✅ Success"
        except Exception as e:
            results['steps']['engine_optimization'] = f"❌ Error: {e}"
        
        # Step 2: Create performance indexes
        try:
            index_count = self.create_performance_indexes()
            results['steps']['index_creation'] = f"✅ Created {index_count} indexes"
        except Exception as e:
            results['steps']['index_creation'] = f"❌ Error: {e}"
        
        # Step 3: Analyze performance
        try:
            performance = self.analyze_query_performance()
            results['steps']['performance_analysis'] = "✅ Completed"
            results['query_performance'] = performance
        except Exception as e:
            results['steps']['performance_analysis'] = f"❌ Error: {e}"
        
        # Step 4: Gather statistics
        try:
            stats = self.get_database_stats()
            results['steps']['statistics_gathering'] = "✅ Completed"
            results['database_stats'] = stats
        except Exception as e:
            results['steps']['statistics_gathering'] = f"❌ Error: {e}"
        
        end_time = time.time()
        results['optimization_duration'] = round(end_time - start_time, 2)
        results['optimization_complete'] = True
        
        logger.info(f"✅ Database optimization completed in {results['optimization_duration']} seconds")
        
        return results

def run_database_optimization():
    """Run database optimization and display results"""
    
    print("🔧 BOOKMYMOVIE DATABASE OPTIMIZATION")
    print("=" * 50)
    
    optimizer = DatabaseOptimizer()
    results = optimizer.optimize_database()
    
    print(f"\n📊 OPTIMIZATION RESULTS")
    print("-" * 30)
    
    for step, result in results['steps'].items():
        print(f"{step.replace('_', ' ').title()}: {result}")
    
    print(f"\n⏱️  Total Duration: {results['optimization_duration']} seconds")
    
    # Display performance results
    if 'query_performance' in results:
        print(f"\n🚀 QUERY PERFORMANCE ANALYSIS")
        print("-" * 35)
        for query, perf in results['query_performance'].items():
            status_icon = "✅" if perf['status'] == 'success' else "❌"
            print(f"{status_icon} {query.replace('_', ' ').title()}: {perf['execution_time_ms']}ms")
    
    # Display database stats
    if 'database_stats' in results:
        print(f"\n📈 DATABASE STATISTICS")
        print("-" * 25)
        
        if 'table_counts' in results['database_stats']:
            total_records = sum([v for v in results['database_stats']['table_counts'].values() if isinstance(v, int)])
            print(f"Total Records: {total_records:,}")
            
            for table, count in results['database_stats']['table_counts'].items():
                if isinstance(count, int):
                    print(f"  {table.title()}: {count:,}")
        
        if 'database_info' in results['database_stats']:
            db_info = results['database_stats']['database_info']
            if isinstance(db_info, dict):
                print(f"Database Size: {db_info.get('size_mb', 'N/A')} MB")
    
    print(f"\n🎉 Database optimization complete!")
    print(f"Your BookMyMovie platform now has enhanced performance!")
    
    return results

if __name__ == "__main__":
    run_database_optimization()