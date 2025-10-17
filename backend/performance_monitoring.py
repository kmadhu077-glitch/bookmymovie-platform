"""
Performance Monitoring Stack with Prometheus and Grafana Integration
Advanced monitoring, metrics collection, and alerting system
"""

import asyncio
import time
import logging
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict, deque
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
from prometheus_client.multiprocess import MultiProcessCollector
from fastapi import FastAPI, Response, Request
from fastapi.responses import PlainTextResponse
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class MetricConfig:
    """Metric configuration"""
    name: str
    description: str
    metric_type: str  # counter, gauge, histogram, summary
    labels: List[str] = None

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric: str
    operator: str  # >, <, ==, !=, >=, <=
    threshold: float
    duration: int  # seconds
    severity: str  # critical, warning, info
    description: str
    action: Optional[str] = None

class CustomMetrics:
    """Custom application metrics"""
    
    def __init__(self, registry: CollectorRegistry = None):
        self.registry = registry or CollectorRegistry()
        
        # HTTP Request Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Database Metrics
        self.db_connections_active = Gauge(
            'database_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration',
            ['query_type'],
            registry=self.registry
        )
        
        self.db_errors_total = Counter(
            'database_errors_total',
            'Total database errors',
            ['error_type'],
            registry=self.registry
        )
        
        # Cache Metrics
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_operations_duration = Histogram(
            'cache_operations_duration_seconds',
            'Cache operation duration',
            ['operation', 'cache_type'],
            registry=self.registry
        )
        
        # Business Metrics
        self.bookings_total = Counter(
            'bookings_total',
            'Total bookings',
            ['status', 'theater'],
            registry=self.registry
        )
        
        self.revenue_total = Counter(
            'revenue_total',
            'Total revenue',
            ['currency'],
            registry=self.registry
        )
        
        self.users_active = Gauge(
            'users_active_current',
            'Currently active users',
            registry=self.registry
        )
        
        self.movie_views_total = Counter(
            'movie_views_total',
            'Total movie views',
            ['movie_id'],
            registry=self.registry
        )
        
        # System Metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_bytes',
            'System memory usage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            ['mount_point'],
            registry=self.registry
        )
        
        # Application Info
        self.app_info = Info(
            'application_info',
            'Application information',
            registry=self.registry
        )
        
        # Rate Limiting Metrics
        self.rate_limit_exceeded_total = Counter(
            'rate_limit_exceeded_total',
            'Total rate limit exceeded events',
            ['client_type', 'endpoint'],
            registry=self.registry
        )
        
        # Background Task Metrics
        self.background_tasks_total = Counter(
            'background_tasks_total',
            'Total background tasks',
            ['task_name', 'status'],
            registry=self.registry
        )
        
        self.background_task_duration = Histogram(
            'background_task_duration_seconds',
            'Background task duration',
            ['task_name'],
            registry=self.registry
        )

class PerformanceMonitor:
    """Advanced performance monitoring system"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.metrics = CustomMetrics(self.registry)
        self.alert_rules: List[AlertRule] = []
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.system_monitor_task = None
        self.is_monitoring = False
        
        # Initialize application info
        self.metrics.app_info.info({
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        })
        
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """Setup default alert rules"""
        self.alert_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric="system_cpu_usage_percent",
                operator=">",
                threshold=80.0,
                duration=300,  # 5 minutes
                severity="warning",
                description="CPU usage is above 80%"
            ),
            AlertRule(
                name="high_memory_usage", 
                metric="system_memory_usage_bytes",
                operator=">",
                threshold=0.85,  # 85% of total memory
                duration=300,
                severity="warning",
                description="Memory usage is above 85%"
            ),
            AlertRule(
                name="high_error_rate",
                metric="http_requests_total",
                operator=">",
                threshold=0.1,  # 10% error rate
                duration=180,
                severity="critical",
                description="HTTP error rate is above 10%"
            ),
            AlertRule(
                name="database_connection_exhaustion",
                metric="database_connections_active",
                operator=">",
                threshold=45,  # 90% of 50 max connections
                duration=60,
                severity="critical",
                description="Database connection pool near exhaustion"
            )
        ]
    
    async def start_monitoring(self):
        """Start the monitoring system"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.system_monitor_task = asyncio.create_task(self._system_monitor_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_monitoring = False
        if self.system_monitor_task:
            self.system_monitor_task.cancel()
        logger.info("Performance monitoring stopped")
    
    async def _system_monitor_loop(self):
        """Main monitoring loop for system metrics"""
        while self.is_monitoring:
            try:
                await self._collect_system_metrics()
                await self._check_alert_rules()
                await asyncio.sleep(30)  # Collect metrics every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.system_cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics.system_memory_usage.set(memory.used)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics.system_disk_usage.labels(mount_point='/').set(disk_percent)
            
            # Store in history for trend analysis
            timestamp = time.time()
            self.metric_history['cpu_usage'].append((timestamp, cpu_percent))
            self.metric_history['memory_usage'].append((timestamp, memory.percent))
            self.metric_history['disk_usage'].append((timestamp, disk_percent))
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _check_alert_rules(self):
        """Check alert rules and trigger alerts"""
        for rule in self.alert_rules:
            try:
                await self._evaluate_alert_rule(rule)
            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule.name}: {e}")
    
    async def _evaluate_alert_rule(self, rule: AlertRule):
        """Evaluate a single alert rule"""
        # This is a simplified implementation
        # In a real system, you'd query the actual metric values from Prometheus
        
        current_value = await self._get_current_metric_value(rule.metric)
        
        if current_value is None:
            return
        
        # Simple threshold checking
        triggered = False
        
        if rule.operator == '>':
            triggered = current_value > rule.threshold
        elif rule.operator == '<':
            triggered = current_value < rule.threshold
        elif rule.operator == '>=':
            triggered = current_value >= rule.threshold
        elif rule.operator == '<=':
            triggered = current_value <= rule.threshold
        elif rule.operator == '==':
            triggered = current_value == rule.threshold
        elif rule.operator == '!=':
            triggered = current_value != rule.threshold
        
        if triggered:
            await self._trigger_alert(rule, current_value)
    
    async def _get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value for a metric"""
        if metric_name == 'system_cpu_usage_percent':
            if 'cpu_usage' in self.metric_history and self.metric_history['cpu_usage']:
                return self.metric_history['cpu_usage'][-1][1]
        elif metric_name == 'system_memory_usage_bytes':
            if 'memory_usage' in self.metric_history and self.metric_history['memory_usage']:
                return self.metric_history['memory_usage'][-1][1] / 100.0  # Convert to ratio
        
        return None
    
    async def _trigger_alert(self, rule: AlertRule, current_value: float):
        """Trigger an alert"""
        alert_data = {
            'rule_name': rule.name,
            'severity': rule.severity,
            'description': rule.description,
            'current_value': current_value,
            'threshold': rule.threshold,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.warning(f"ALERT TRIGGERED: {rule.name} - {rule.description} (current: {current_value}, threshold: {rule.threshold})")
        
        # Store alert in database or send to alerting system
        await self._store_alert(alert_data)
    
    async def _store_alert(self, alert_data: Dict[str, Any]):
        """Store alert in database or send to external system"""
        # This could integrate with:
        # - Database storage
        # - Slack notifications
        # - Email alerts
        # - PagerDuty
        # - Custom webhook
        
        # For now, just log it
        logger.info(f"Alert stored: {json.dumps(alert_data, default=str)}")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        self.metrics.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.metrics.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_database_operation(self, query_type: str, duration: float, success: bool = True):
        """Record database operation metrics"""
        self.metrics.db_query_duration.labels(query_type=query_type).observe(duration)
        
        if not success:
            self.metrics.db_errors_total.labels(error_type=query_type).inc()
    
    def record_cache_operation(self, operation: str, cache_type: str, hit: bool, duration: float):
        """Record cache operation metrics"""
        if hit:
            self.metrics.cache_hits_total.labels(cache_type=cache_type).inc()
        else:
            self.metrics.cache_misses_total.labels(cache_type=cache_type).inc()
        
        self.metrics.cache_operations_duration.labels(
            operation=operation,
            cache_type=cache_type
        ).observe(duration)
    
    def record_booking(self, status: str, theater: str, revenue: float = 0.0):
        """Record booking metrics"""
        self.metrics.bookings_total.labels(status=status, theater=theater).inc()
        
        if revenue > 0:
            self.metrics.revenue_total.labels(currency='USD').inc(revenue)
    
    def record_movie_view(self, movie_id: str):
        """Record movie view metrics"""
        self.metrics.movie_views_total.labels(movie_id=movie_id).inc()
    
    def update_active_users(self, count: int):
        """Update active users count"""
        self.metrics.users_active.set(count)
    
    def record_rate_limit_exceeded(self, client_type: str, endpoint: str):
        """Record rate limit exceeded event"""
        self.metrics.rate_limit_exceeded_total.labels(
            client_type=client_type,
            endpoint=endpoint
        ).inc()
    
    def record_background_task(self, task_name: str, status: str, duration: float = None):
        """Record background task metrics"""
        self.metrics.background_tasks_total.labels(
            task_name=task_name,
            status=status
        ).inc()
        
        if duration is not None:
            self.metrics.background_task_duration.labels(task_name=task_name).observe(duration)
    
    def get_metrics_report(self) -> Dict[str, Any]:
        """Generate comprehensive metrics report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': {},
            'application_metrics': {},
            'alert_summary': {
                'total_rules': len(self.alert_rules),
                'active_alerts': 0  # This would be calculated from stored alerts
            }
        }
        
        # Add system metrics if available
        if 'cpu_usage' in self.metric_history and self.metric_history['cpu_usage']:
            latest_cpu = self.metric_history['cpu_usage'][-1][1]
            report['system_metrics']['cpu_usage_percent'] = latest_cpu
        
        if 'memory_usage' in self.metric_history and self.metric_history['memory_usage']:
            latest_memory = self.metric_history['memory_usage'][-1][1]
            report['system_metrics']['memory_usage_percent'] = latest_memory
        
        return report
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest(self.registry)

class PerformanceMiddleware:
    """FastAPI middleware for performance monitoring"""
    
    def __init__(self, app: FastAPI, monitor: PerformanceMonitor):
        self.app = app
        self.monitor = monitor
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        method = scope["method"]
        path = scope["path"]
        
        # Normalize endpoint for metrics (remove IDs, etc.)
        normalized_endpoint = self._normalize_endpoint(path)
        
        # Create a custom send function to capture response status
        status_code = 500  # Default to error
        
        async def custom_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, custom_send)
        finally:
            # Record metrics
            duration = time.time() - start_time
            self.monitor.record_http_request(method, normalized_endpoint, status_code, duration)
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics"""
        # Replace IDs with placeholders
        import re
        
        # Replace UUIDs
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def init_monitoring():
    """Initialize the monitoring system"""
    # Set up multiprocess mode for Prometheus if running with multiple workers
    if os.environ.get('prometheus_multiproc_dir'):
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
    
    logger.info("Performance monitoring initialized")

async def start_monitoring():
    """Start the monitoring system"""
    await performance_monitor.start_monitoring()

async def stop_monitoring():
    """Stop the monitoring system"""
    await performance_monitor.stop_monitoring()

def get_metrics_endpoint():
    """Get FastAPI endpoint for metrics"""
    async def metrics():
        return PlainTextResponse(
            performance_monitor.export_metrics(),
            headers={"Content-Type": CONTENT_TYPE_LATEST}
        )
    return metrics

# Health check utilities
class HealthChecker:
    """Application health checking"""
    
    @staticmethod
    async def check_database_health() -> Dict[str, Any]:
        """Check database health"""
        try:
            # Simple database connectivity check
            start_time = time.time()
            
            # This would use your actual database connection
            # For now, just simulate
            await asyncio.sleep(0.01)  # Simulate DB query
            
            duration = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time': round(duration, 3),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    async def check_cache_health() -> Dict[str, Any]:
        """Check cache health"""
        try:
            # This would check Redis connectivity
            # For now, just simulate
            
            return {
                'status': 'healthy',
                'connection': 'active',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    async def get_comprehensive_health() -> Dict[str, Any]:
        """Get comprehensive health status"""
        health_checks = await asyncio.gather(
            HealthChecker.check_database_health(),
            HealthChecker.check_cache_health(),
            return_exceptions=True
        )
        
        database_health, cache_health = health_checks
        
        overall_status = 'healthy'
        if (isinstance(database_health, dict) and database_health.get('status') != 'healthy') or \
           (isinstance(cache_health, dict) and cache_health.get('status') != 'healthy'):
            overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': database_health if isinstance(database_health, dict) else {'status': 'error', 'error': str(database_health)},
                'cache': cache_health if isinstance(cache_health, dict) else {'status': 'error', 'error': str(cache_health)}
            }
        }