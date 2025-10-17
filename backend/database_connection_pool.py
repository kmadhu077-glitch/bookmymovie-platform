"""
Advanced Database Connection Pool Manager
Enterprise-grade database connection pooling with automatic failover
"""

import asyncio
import logging
import sqlite3
import asyncpg
import threading
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, Dict, Any, List
import time
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

@dataclass
class ConnectionPoolConfig:
    """Database connection pool configuration"""
    min_connections: int = 5
    max_connections: int = 100
    connection_timeout: int = 30
    idle_timeout: int = 600
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 60

@dataclass
class PoolMetrics:
    """Connection pool performance metrics"""
    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    failed_connections: int = 0
    average_response_time: float = 0.0
    peak_connections: int = 0
    last_health_check: float = 0.0

class DatabaseConnectionPool:
    """Enterprise database connection pool manager"""
    
    def __init__(self, config: ConnectionPoolConfig):
        self.config = config
        self.metrics = PoolMetrics()
        self._connections = asyncio.Queue(maxsize=config.max_connections)
        self._active_connections = set()
        self._connection_semaphore = asyncio.Semaphore(config.max_connections)
        self._lock = asyncio.Lock()
        self._health_check_task = None
        self._initialized = False
        
    async def initialize(self, database_url: str):
        """Initialize the connection pool"""
        if self._initialized:
            return
            
        logger.info(f"Initializing database pool with {self.config.min_connections}-{self.config.max_connections} connections")
        
        # Create minimum number of connections
        for _ in range(self.config.min_connections):
            try:
                if database_url.startswith('postgresql://'):
                    conn = await asyncpg.connect(database_url, timeout=self.config.connection_timeout)
                else:
                    # SQLite connection (for development)
                    conn = sqlite3.connect(database_url, timeout=self.config.connection_timeout)
                    
                await self._connections.put(conn)
                self.metrics.total_connections += 1
                self.metrics.idle_connections += 1
                
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
                self.metrics.failed_connections += 1
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._initialized = True
        
        logger.info(f"Database pool initialized with {self.metrics.total_connections} connections")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        start_time = time.time()
        connection = None
        
        try:
            # Wait for available connection slot
            await self._connection_semaphore.acquire()
            
            async with self._lock:
                if self._connections.empty():
                    # Create new connection if under max limit
                    if self.metrics.total_connections < self.config.max_connections:
                        connection = await self._create_new_connection()
                    else:
                        # Wait for available connection
                        connection = await asyncio.wait_for(
                            self._connections.get(),
                            timeout=self.config.connection_timeout
                        )
                else:
                    connection = await self._connections.get()
                
                if connection:
                    self._active_connections.add(connection)
                    self.metrics.active_connections += 1
                    self.metrics.idle_connections -= 1
                    
                    # Update peak connections
                    if self.metrics.active_connections > self.metrics.peak_connections:
                        self.metrics.peak_connections = self.metrics.active_connections
            
            yield connection
            
        except asyncio.TimeoutError:
            logger.error("Database connection timeout")
            raise
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            # Return connection to pool
            if connection:
                async with self._lock:
                    if connection in self._active_connections:
                        self._active_connections.remove(connection)
                        self.metrics.active_connections -= 1
                        self.metrics.idle_connections += 1
                        
                        # Validate connection before returning to pool
                        if await self._validate_connection(connection):
                            await self._connections.put(connection)
                        else:
                            # Connection is invalid, create replacement
                            self.metrics.total_connections -= 1
                            asyncio.create_task(self._replace_connection())
            
            self._connection_semaphore.release()
            
            # Update response time metrics
            response_time = time.time() - start_time
            self.metrics.average_response_time = (
                (self.metrics.average_response_time * 0.9) + (response_time * 0.1)
            )
    
    async def _create_new_connection(self):
        """Create a new database connection"""
        try:
            # This would be configured based on database type
            database_url = os.getenv('DATABASE_URL', 'sqlite:///bookmymovie.db')
            
            if database_url.startswith('postgresql://'):
                conn = await asyncpg.connect(database_url, timeout=self.config.connection_timeout)
            else:
                conn = sqlite3.connect(database_url.replace('sqlite:///', ''), timeout=self.config.connection_timeout)
            
            self.metrics.total_connections += 1
            logger.debug("Created new database connection")
            return conn
            
        except Exception as e:
            logger.error(f"Failed to create new connection: {e}")
            self.metrics.failed_connections += 1
            return None
    
    async def _validate_connection(self, connection) -> bool:
        """Validate if a connection is still healthy"""
        try:
            if hasattr(connection, 'fetchval'):  # asyncpg
                await connection.fetchval('SELECT 1')
            else:  # sqlite3
                connection.execute('SELECT 1')
            return True
        except Exception:
            return False
    
    async def _replace_connection(self):
        """Replace a failed connection"""
        new_connection = await self._create_new_connection()
        if new_connection:
            await self._connections.put(new_connection)
            self.metrics.idle_connections += 1
    
    async def _health_check_loop(self):
        """Periodic health check for connections"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _perform_health_check(self):
        """Perform health check on idle connections"""
        async with self._lock:
            connections_to_check = []
            
            # Get all idle connections for checking
            while not self._connections.empty():
                conn = await self._connections.get()
                connections_to_check.append(conn)
            
            healthy_connections = []
            
            for conn in connections_to_check:
                if await self._validate_connection(conn):
                    healthy_connections.append(conn)
                else:
                    self.metrics.total_connections -= 1
                    self.metrics.idle_connections -= 1
                    self.metrics.failed_connections += 1
            
            # Return healthy connections to pool
            for conn in healthy_connections:
                await self._connections.put(conn)
            
            # Create replacement connections if needed
            missing_connections = self.config.min_connections - len(healthy_connections)
            for _ in range(missing_connections):
                new_conn = await self._create_new_connection()
                if new_conn:
                    await self._connections.put(new_conn)
                    self.metrics.idle_connections += 1
            
            self.metrics.last_health_check = time.time()
            
            logger.debug(f"Health check complete. Healthy connections: {len(healthy_connections)}")
    
    async def close_all(self):
        """Close all connections and cleanup"""
        if self._health_check_task:
            self._health_check_task.cancel()
            
        async with self._lock:
            # Close all idle connections
            while not self._connections.empty():
                conn = await self._connections.get()
                try:
                    if hasattr(conn, 'close'):
                        await conn.close()
                    else:
                        conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            
            # Close active connections
            for conn in self._active_connections:
                try:
                    if hasattr(conn, 'close'):
                        await conn.close()
                    else:
                        conn.close()
                except Exception as e:
                    logger.error(f"Error closing active connection: {e}")
            
            self._active_connections.clear()
            
        logger.info("All database connections closed")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current pool metrics"""
        return {
            "active_connections": self.metrics.active_connections,
            "idle_connections": self.metrics.idle_connections,
            "total_connections": self.metrics.total_connections,
            "failed_connections": self.metrics.failed_connections,
            "average_response_time": round(self.metrics.average_response_time, 3),
            "peak_connections": self.metrics.peak_connections,
            "last_health_check": self.metrics.last_health_check,
            "pool_utilization": round(
                (self.metrics.active_connections / self.config.max_connections) * 100, 2
            )
        }

class SQLiteConnectionPool:
    """Specialized SQLite connection pool for development"""
    
    def __init__(self, db_path: str, max_connections: int = 20):
        self.db_path = db_path
        self.max_connections = max_connections
        self._connections = []
        self._lock = threading.Lock()
        self._active_count = 0
    
    @contextmanager
    def get_connection(self):
        """Get SQLite connection (synchronous)"""
        connection = None
        
        try:
            with self._lock:
                if self._connections and len(self._connections) > 0:
                    connection = self._connections.pop()
                else:
                    connection = sqlite3.connect(
                        self.db_path,
                        timeout=30.0,
                        isolation_level=None,  # autocommit mode
                        check_same_thread=False
                    )
                    # Enable WAL mode for better concurrency
                    connection.execute('PRAGMA journal_mode=WAL')
                    connection.execute('PRAGMA synchronous=NORMAL')
                    connection.execute('PRAGMA cache_size=10000')
                
                self._active_count += 1
            
            yield connection
            
        finally:
            if connection:
                with self._lock:
                    self._active_count -= 1
                    if len(self._connections) < self.max_connections:
                        self._connections.append(connection)
                    else:
                        connection.close()
    
    def close_all(self):
        """Close all connections"""
        with self._lock:
            for conn in self._connections:
                conn.close()
            self._connections.clear()

# Global connection pool instances
_async_pool: Optional[DatabaseConnectionPool] = None
_sqlite_pool: Optional[SQLiteConnectionPool] = None

async def init_database_pools():
    """Initialize database connection pools"""
    global _async_pool, _sqlite_pool
    
    # Configuration from environment
    config = ConnectionPoolConfig(
        min_connections=int(os.getenv('DB_MIN_CONNECTIONS', '5')),
        max_connections=int(os.getenv('DB_MAX_CONNECTIONS', '50')),
        connection_timeout=int(os.getenv('DB_CONNECTION_TIMEOUT', '30')),
        idle_timeout=int(os.getenv('DB_IDLE_TIMEOUT', '600'))
    )
    
    # Initialize async pool
    _async_pool = DatabaseConnectionPool(config)
    database_url = os.getenv('DATABASE_URL', 'sqlite:///bookmymovie.db')
    await _async_pool.initialize(database_url)
    
    # Initialize SQLite pool for synchronous operations
    sqlite_path = os.getenv('SQLITE_PATH', 'bookmymovie.db')
    _sqlite_pool = SQLiteConnectionPool(sqlite_path)
    
    logger.info("Database connection pools initialized")

async def get_async_connection():
    """Get async database connection"""
    if not _async_pool:
        await init_database_pools()
    return _async_pool.get_connection()

def get_sqlite_connection():
    """Get SQLite connection (synchronous)"""
    if not _sqlite_pool:
        sqlite_path = os.getenv('SQLITE_PATH', 'bookmymovie.db')
        global _sqlite_pool
        _sqlite_pool = SQLiteConnectionPool(sqlite_path)
    return _sqlite_pool.get_connection()

async def close_database_pools():
    """Close all database pools"""
    if _async_pool:
        await _async_pool.close_all()
    if _sqlite_pool:
        _sqlite_pool.close_all()
    
    logger.info("Database connection pools closed")

def get_pool_metrics() -> Dict[str, Any]:
    """Get metrics from all pools"""
    metrics = {}
    
    if _async_pool:
        metrics['async_pool'] = _async_pool.get_metrics()
    
    if _sqlite_pool:
        metrics['sqlite_pool'] = {
            'active_connections': _sqlite_pool._active_count,
            'available_connections': len(_sqlite_pool._connections),
            'max_connections': _sqlite_pool.max_connections
        }
    
    return metrics