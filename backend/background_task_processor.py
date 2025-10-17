"""
Background Task Processing with Celery
Distributed task queue for heavy processing and scheduled jobs
"""

import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import time
from celery import Celery, Task
from celery.signals import task_prerun, task_postrun, task_failure
from celery.exceptions import Retry
from kombu import Queue
import redis
import os

logger = logging.getLogger(__name__)

# Celery configuration
CELERY_CONFIG = {
    'broker_url': os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    'result_backend': os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 600,  # 10 minutes
    'task_soft_time_limit': 480,  # 8 minutes
    'worker_prefetch_multiplier': 1,
    'task_acks_late': True,
    'task_reject_on_worker_lost': True,
    'task_routes': {
        'bookmymovie.tasks.analytics.*': {'queue': 'analytics'},
        'bookmymovie.tasks.notifications.*': {'queue': 'notifications'},
        'bookmymovie.tasks.reports.*': {'queue': 'reports'},
        'bookmymovie.tasks.maintenance.*': {'queue': 'maintenance'},
        'bookmymovie.tasks.heavy.*': {'queue': 'heavy_processing'},
    },
    'task_default_queue': 'default',
    'task_queues': (
        Queue('default'),
        Queue('analytics', routing_key='analytics'),
        Queue('notifications', routing_key='notifications'),
        Queue('reports', routing_key='reports'),
        Queue('maintenance', routing_key='maintenance'),
        Queue('heavy_processing', routing_key='heavy_processing'),
    ),
    'beat_schedule': {
        'generate_daily_analytics': {
            'task': 'bookmymovie.tasks.analytics.generate_daily_report',
            'schedule': 3600.0,  # Every hour
        },
        'cleanup_expired_data': {
            'task': 'bookmymovie.tasks.maintenance.cleanup_expired_data',
            'schedule': 86400.0,  # Daily
        },
        'send_scheduled_notifications': {
            'task': 'bookmymovie.tasks.notifications.send_scheduled_notifications',
            'schedule': 300.0,  # Every 5 minutes
        },
        'update_movie_recommendations': {
            'task': 'bookmymovie.tasks.analytics.update_recommendations',
            'schedule': 1800.0,  # Every 30 minutes
        },
    }
}

@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    status: str
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    retries: int = 0

class BaseBookMyMovieTask(Task):
    """Base task class with enhanced error handling and monitoring"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 700
    retry_jitter = False
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success"""
        logger.info(f"Task {task_id} completed successfully")
        
        # Update task metrics
        if hasattr(self, '_start_time'):
            duration = time.time() - self._start_time
            task_monitor.record_success(self.name, duration)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure"""
        logger.error(f"Task {task_id} failed: {exc}")
        task_monitor.record_failure(self.name, str(exc))
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called on task retry"""
        logger.warning(f"Task {task_id} retrying: {exc}")
        task_monitor.record_retry(self.name)

# Initialize Celery app
celery_app = Celery('bookmymovie')
celery_app.config_from_object(CELERY_CONFIG)
celery_app.Task = BaseBookMyMovieTask

class TaskMonitor:
    """Task execution monitoring and metrics"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=3  # Separate DB for task metrics
        )
        self.metrics_key_prefix = 'bookmymovie:task_metrics'
    
    def record_success(self, task_name: str, duration: float):
        """Record successful task execution"""
        key = f"{self.metrics_key_prefix}:{task_name}:success"
        pipe = self.redis_client.pipeline()
        pipe.hincrby(key, 'count', 1)
        pipe.hincrbyfloat(key, 'total_duration', duration)
        pipe.hset(key, 'last_success', time.time())
        pipe.execute()
    
    def record_failure(self, task_name: str, error: str):
        """Record failed task execution"""
        key = f"{self.metrics_key_prefix}:{task_name}:failure"
        pipe = self.redis_client.pipeline()
        pipe.hincrby(key, 'count', 1)
        pipe.hset(key, 'last_error', error)
        pipe.hset(key, 'last_failure', time.time())
        pipe.execute()
    
    def record_retry(self, task_name: str):
        """Record task retry"""
        key = f"{self.metrics_key_prefix}:{task_name}:retry"
        self.redis_client.hincrby(key, 'count', 1)
    
    def get_task_stats(self, task_name: str) -> Dict[str, Any]:
        """Get statistics for a specific task"""
        success_key = f"{self.metrics_key_prefix}:{task_name}:success"
        failure_key = f"{self.metrics_key_prefix}:{task_name}:failure"
        retry_key = f"{self.metrics_key_prefix}:{task_name}:retry"
        
        success_data = self.redis_client.hgetall(success_key)
        failure_data = self.redis_client.hgetall(failure_key)
        retry_data = self.redis_client.hgetall(retry_key)
        
        success_count = int(success_data.get(b'count', 0))
        failure_count = int(failure_data.get(b'count', 0))
        retry_count = int(retry_data.get(b'count', 0))
        
        total_duration = float(success_data.get(b'total_duration', 0))
        avg_duration = (total_duration / success_count) if success_count > 0 else 0
        
        success_rate = (success_count / (success_count + failure_count)) * 100 if (success_count + failure_count) > 0 else 0
        
        return {
            'task_name': task_name,
            'success_count': success_count,
            'failure_count': failure_count,
            'retry_count': retry_count,
            'success_rate': round(success_rate, 2),
            'average_duration': round(avg_duration, 3),
            'last_success': success_data.get(b'last_success', b'').decode(),
            'last_failure': failure_data.get(b'last_failure', b'').decode(),
            'last_error': failure_data.get(b'last_error', b'').decode()
        }
    
    def get_all_task_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all tasks"""
        pattern = f"{self.metrics_key_prefix}:*:success"
        success_keys = self.redis_client.keys(pattern)
        
        task_names = set()
        for key in success_keys:
            key_str = key.decode()
            task_name = key_str.replace(f"{self.metrics_key_prefix}:", "").replace(":success", "")
            task_names.add(task_name)
        
        return [self.get_task_stats(task_name) for task_name in task_names]

# Global task monitor
task_monitor = TaskMonitor()

# Task signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Called before task execution"""
    task._start_time = time.time()
    logger.info(f"Starting task {task.name} with ID {task_id}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Called after task execution"""
    if hasattr(task, '_start_time'):
        duration = time.time() - task._start_time
        logger.info(f"Task {task.name} completed in {duration:.3f}s")

# Analytics Tasks
@celery_app.task(bind=True, name='bookmymovie.tasks.analytics.generate_daily_report')
def generate_daily_analytics_report(self):
    """Generate comprehensive daily analytics report"""
    try:
        logger.info("Starting daily analytics report generation")
        
        # This would integrate with the analytics service
        from analytics_service import AnalyticsService
        
        analytics = AnalyticsService()
        
        # Generate various analytics
        user_metrics = analytics.get_user_metrics()
        revenue_metrics = analytics.get_revenue_metrics()
        booking_metrics = analytics.get_booking_metrics()
        
        # Create report data
        report_data = {
            'date': datetime.now().date().isoformat(),
            'user_metrics': user_metrics,
            'revenue_metrics': revenue_metrics,
            'booking_metrics': booking_metrics,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store report (this could be saved to database or file system)
        report_key = f"daily_report:{datetime.now().date()}"
        task_monitor.redis_client.set(report_key, json.dumps(report_data), ex=86400*7)  # Keep for 7 days
        
        logger.info("Daily analytics report generated successfully")
        return report_data
        
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        raise self.retry(countdown=300)  # Retry in 5 minutes

@celery_app.task(bind=True, name='bookmymovie.tasks.analytics.update_recommendations')
def update_movie_recommendations(self):
    """Update movie recommendations for all users"""
    try:
        logger.info("Starting movie recommendations update")
        
        # This would integrate with the AI recommendation service
        from ai_recommendation_engine import AIRecommendationEngine
        
        ai_engine = AIRecommendationEngine()
        
        # Get all active users (this would come from database)
        active_users = []  # Placeholder
        
        updated_count = 0
        
        for user_id in active_users:
            try:
                recommendations = ai_engine.get_recommendations(user_id)
                
                # Cache recommendations
                cache_key = f"recommendations:{user_id}"
                task_monitor.redis_client.setex(cache_key, 3600, json.dumps(recommendations))
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update recommendations for user {user_id}: {e}")
        
        logger.info(f"Updated recommendations for {updated_count} users")
        return {'updated_count': updated_count, 'total_users': len(active_users)}
        
    except Exception as e:
        logger.error(f"Failed to update recommendations: {e}")
        raise self.retry(countdown=600)  # Retry in 10 minutes

# Notification Tasks
@celery_app.task(bind=True, name='bookmymovie.tasks.notifications.send_scheduled_notifications')
def send_scheduled_notifications(self):
    """Send all scheduled notifications"""
    try:
        logger.info("Processing scheduled notifications")
        
        # Get scheduled notifications from database/queue
        # This is a placeholder - would integrate with notification service
        notifications = []  # Placeholder
        
        sent_count = 0
        failed_count = 0
        
        for notification in notifications:
            try:
                # Send notification (email, SMS, push, etc.)
                # This would use the notification service
                success = True  # Placeholder
                
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                failed_count += 1
        
        logger.info(f"Sent {sent_count} notifications, {failed_count} failed")
        return {'sent': sent_count, 'failed': failed_count}
        
    except Exception as e:
        logger.error(f"Failed to process notifications: {e}")
        raise self.retry(countdown=120)  # Retry in 2 minutes

@celery_app.task(bind=True, name='bookmymovie.tasks.notifications.send_email_notification')
def send_email_notification(self, to_email: str, subject: str, body: str, html_body: str = None):
    """Send individual email notification"""
    try:
        logger.info(f"Sending email to {to_email}")
        
        # This would integrate with email service (SendGrid, AWS SES, etc.)
        # Placeholder implementation
        
        success = True  # Placeholder
        
        if success:
            logger.info(f"Email sent successfully to {to_email}")
            return {'status': 'sent', 'email': to_email}
        else:
            raise Exception("Failed to send email")
            
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise self.retry(countdown=60)

# Report Generation Tasks
@celery_app.task(bind=True, name='bookmymovie.tasks.reports.generate_executive_report')
def generate_executive_report(self, report_type: str = 'monthly'):
    """Generate executive business report"""
    try:
        logger.info(f"Generating {report_type} executive report")
        
        # This would integrate with executive BI service
        from executive_bi_service import ExecutiveBIService
        
        bi_service = ExecutiveBIService()
        
        # Generate report
        report_data = bi_service.generate_executive_report()
        
        # Save report as PDF
        report_filename = f"executive_report_{report_type}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # This would save to file system or cloud storage
        # Placeholder implementation
        
        logger.info(f"Executive report generated: {report_filename}")
        return {'report_file': report_filename, 'report_data': report_data}
        
    except Exception as e:
        logger.error(f"Failed to generate executive report: {e}")
        raise self.retry(countdown=300)

# Maintenance Tasks
@celery_app.task(bind=True, name='bookmymovie.tasks.maintenance.cleanup_expired_data')
def cleanup_expired_data(self):
    """Clean up expired data and optimize database"""
    try:
        logger.info("Starting expired data cleanup")
        
        cleanup_stats = {
            'expired_sessions': 0,
            'old_logs': 0,
            'temporary_files': 0,
            'cache_keys': 0
        }
        
        # Clean expired sessions
        # Placeholder implementation
        
        # Clean old log files
        # Placeholder implementation
        
        # Clean temporary files
        # Placeholder implementation
        
        # Clean expired cache keys
        redis_client = task_monitor.redis_client
        expired_keys = 0  # Would scan for expired keys
        cleanup_stats['cache_keys'] = expired_keys
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired data: {e}")
        raise self.retry(countdown=1800)  # Retry in 30 minutes

@celery_app.task(bind=True, name='bookmymovie.tasks.maintenance.database_optimization')
def optimize_database(self):
    """Perform database optimization tasks"""
    try:
        logger.info("Starting database optimization")
        
        # This would perform various database optimization tasks
        # - VACUUM for SQLite
        # - ANALYZE for statistics
        # - Index rebuilds if needed
        # - Partition maintenance for large tables
        
        optimization_results = {
            'tables_analyzed': 0,
            'indexes_rebuilt': 0,
            'space_reclaimed': 0
        }
        
        # Placeholder implementation
        
        logger.info(f"Database optimization completed: {optimization_results}")
        return optimization_results
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        raise self.retry(countdown=3600)  # Retry in 1 hour

# Heavy Processing Tasks
@celery_app.task(bind=True, name='bookmymovie.tasks.heavy.process_movie_analytics')
def process_movie_analytics(self, movie_id: str):
    """Heavy processing for movie analytics and recommendations"""
    try:
        logger.info(f"Processing analytics for movie {movie_id}")
        
        # This would perform heavy analytics processing
        # - User engagement analysis
        # - Revenue attribution
        # - Recommendation algorithm training
        # - Sentiment analysis of reviews
        
        processing_results = {
            'movie_id': movie_id,
            'engagement_score': 0.0,
            'revenue_impact': 0.0,
            'recommendation_weight': 0.0,
            'processed_at': datetime.now().isoformat()
        }
        
        # Placeholder heavy processing
        time.sleep(5)  # Simulate heavy processing
        
        logger.info(f"Movie analytics processing completed for {movie_id}")
        return processing_results
        
    except Exception as e:
        logger.error(f"Failed to process movie analytics for {movie_id}: {e}")
        raise self.retry(countdown=300)

# Task management utilities
class TaskManager:
    """Utility class for managing background tasks"""
    
    @staticmethod
    def schedule_daily_report():
        """Schedule daily report generation"""
        return generate_daily_analytics_report.delay()
    
    @staticmethod
    def schedule_email(to_email: str, subject: str, body: str, delay_seconds: int = 0):
        """Schedule email sending"""
        if delay_seconds > 0:
            eta = datetime.now() + timedelta(seconds=delay_seconds)
            return send_email_notification.apply_async(
                args=[to_email, subject, body],
                eta=eta
            )
        else:
            return send_email_notification.delay(to_email, subject, body)
    
    @staticmethod
    def schedule_executive_report(report_type: str = 'monthly'):
        """Schedule executive report generation"""
        return generate_executive_report.delay(report_type)
    
    @staticmethod
    def get_task_status(task_id: str) -> TaskResult:
        """Get status of a task"""
        result = celery_app.AsyncResult(task_id)
        
        return TaskResult(
            task_id=task_id,
            status=result.status,
            result=result.result if result.successful() else None,
            error=str(result.result) if result.failed() else None
        )
    
    @staticmethod
    def cancel_task(task_id: str) -> bool:
        """Cancel a running task"""
        celery_app.control.revoke(task_id, terminate=True)
        return True
    
    @staticmethod
    def get_active_tasks() -> List[Dict[str, Any]]:
        """Get list of active tasks"""
        inspect = celery_app.control.inspect()
        active = inspect.active()
        
        if not active:
            return []
        
        tasks = []
        for worker, task_list in active.items():
            for task in task_list:
                tasks.append({
                    'worker': worker,
                    'task_id': task['id'],
                    'task_name': task['name'],
                    'args': task['args'],
                    'kwargs': task['kwargs'],
                    'time_start': task['time_start']
                })
        
        return tasks
    
    @staticmethod
    def get_queue_stats() -> Dict[str, Any]:
        """Get queue statistics"""
        inspect = celery_app.control.inspect()
        
        return {
            'active': inspect.active(),
            'scheduled': inspect.scheduled(),
            'reserved': inspect.reserved(),
            'stats': inspect.stats()
        }

# Initialize task manager
task_manager = TaskManager()

# Startup function
def init_celery_app():
    """Initialize Celery application"""
    logger.info("Initializing Celery application...")
    
    # Test Redis connection
    try:
        task_monitor.redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
    
    logger.info("Celery application initialized")
    
    return celery_app