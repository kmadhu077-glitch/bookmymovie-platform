"""
ML Model Deployment and Monitoring Service
Automated ML model deployment, versioning, and performance monitoring
"""

import asyncio
import logging
import json
import hashlib
import pickle
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from pathlib import Path
import shutil
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import time

# ML model management
import joblib
import tensorflow as tf
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

# Model versioning and experiment tracking
import sqlite3
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class ModelVersion:
    """Model version information"""
    model_id: str
    version: str
    model_type: str  # 'sklearn', 'tensorflow', 'pytorch', 'custom'
    created_at: datetime
    created_by: str
    model_path: str
    metadata: Dict[str, Any]
    performance_metrics: Dict[str, float]
    is_active: bool = False
    deployment_config: Dict[str, Any] = None

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    model_id: str
    version: str
    metric_type: str
    metric_value: float
    computed_at: datetime
    data_split: str  # 'train', 'validation', 'test', 'production'
    sample_size: int

@dataclass
class ModelPerformanceAlert:
    """Model performance alert"""
    alert_id: str
    model_id: str
    version: str
    alert_type: str  # 'performance_degradation', 'data_drift', 'prediction_anomaly'
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    metrics: Dict[str, Any]
    triggered_at: datetime
    acknowledged: bool = False

@dataclass
class ABTestResult:
    """A/B testing result for model comparison"""
    test_id: str
    model_a_id: str
    model_b_id: str
    metric_name: str
    model_a_value: float
    model_b_value: float
    statistical_significance: float
    winner: str  # 'model_a', 'model_b', 'tie'
    confidence_level: float
    test_duration_days: int
    sample_size: int

class ModelRegistry:
    """Model registry for version control and metadata management"""
    
    def __init__(self, registry_path: str = "model_registry"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(exist_ok=True)
        
        # Initialize database
        self.db_path = self.registry_path / "registry.db"
        self._init_database()
        
        # Active models cache
        self.active_models = {}
        
    def _init_database(self):
        """Initialize SQLite database for model registry"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT,
                version TEXT,
                model_type TEXT,
                created_at TEXT,
                created_by TEXT,
                model_path TEXT,
                metadata TEXT,
                performance_metrics TEXT,
                is_active INTEGER,
                deployment_config TEXT,
                PRIMARY KEY (model_id, version)
            )
        """)
        
        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT,
                version TEXT,
                metric_type TEXT,
                metric_value REAL,
                computed_at TEXT,
                data_split TEXT,
                sample_size INTEGER
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_alerts (
                alert_id TEXT PRIMARY KEY,
                model_id TEXT,
                version TEXT,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                metrics TEXT,
                triggered_at TEXT,
                acknowledged INTEGER
            )
        """)
        
        # A/B tests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_tests (
                test_id TEXT PRIMARY KEY,
                model_a_id TEXT,
                model_b_id TEXT,
                metric_name TEXT,
                model_a_value REAL,
                model_b_value REAL,
                statistical_significance REAL,
                winner TEXT,
                confidence_level REAL,
                test_duration_days INTEGER,
                sample_size INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def register_model(self, model: Any, model_id: str, version: str, model_type: str,
                      metadata: Dict[str, Any] = None, performance_metrics: Dict[str, float] = None,
                      deployment_config: Dict[str, Any] = None) -> ModelVersion:
        """Register a new model version"""
        
        try:
            # Create model directory
            model_dir = self.registry_path / model_id / version
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Save model
            if model_type == 'sklearn':
                model_path = model_dir / "model.pkl"
                joblib.dump(model, model_path)
            elif model_type == 'tensorflow':
                model_path = model_dir / "model.h5"
                model.save(model_path)
            else:
                # Custom serialization
                model_path = model_dir / "model.pkl"
                with open(model_path, 'wb') as f:
                    pickle.dump(model, f)
            
            # Create model version object
            model_version = ModelVersion(
                model_id=model_id,
                version=version,
                model_type=model_type,
                created_at=datetime.now(),
                created_by="system",  # Would be actual user in production
                model_path=str(model_path),
                metadata=metadata or {},
                performance_metrics=performance_metrics or {},
                deployment_config=deployment_config or {}
            )
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO models 
                (model_id, version, model_type, created_at, created_by, model_path, 
                 metadata, performance_metrics, is_active, deployment_config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model_version.model_id,
                model_version.version,
                model_version.model_type,
                model_version.created_at.isoformat(),
                model_version.created_by,
                model_version.model_path,
                json.dumps(model_version.metadata),
                json.dumps(model_version.performance_metrics),
                0,  # Not active by default
                json.dumps(model_version.deployment_config)
            ))
            
            conn.commit()
            conn.close()
            
            # Save metadata
            metadata_path = model_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(asdict(model_version), f, indent=2, default=str)
            
            logger.info(f"Model {model_id} version {version} registered successfully")
            return model_version
            
        except Exception as e:
            logger.error(f"Failed to register model {model_id} version {version}: {e}")
            raise
    
    def load_model(self, model_id: str, version: str = None) -> Tuple[Any, ModelVersion]:
        """Load model from registry"""
        
        if version is None:
            # Load active version
            version = self.get_active_version(model_id)
            if not version:
                raise ValueError(f"No active version found for model {model_id}")
        
        try:
            # Get model info from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT model_type, model_path, metadata, performance_metrics, 
                       deployment_config, created_at, created_by, is_active
                FROM models 
                WHERE model_id = ? AND version = ?
            """, (model_id, version))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise ValueError(f"Model {model_id} version {version} not found")
            
            model_type, model_path, metadata, performance_metrics, deployment_config, created_at, created_by, is_active = row
            
            # Load model
            if model_type == 'sklearn':
                model = joblib.load(model_path)
            elif model_type == 'tensorflow':
                model = tf.keras.models.load_model(model_path)
            else:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
            
            # Create model version object
            model_version = ModelVersion(
                model_id=model_id,
                version=version,
                model_type=model_type,
                created_at=datetime.fromisoformat(created_at),
                created_by=created_by,
                model_path=model_path,
                metadata=json.loads(metadata),
                performance_metrics=json.loads(performance_metrics),
                is_active=bool(is_active),
                deployment_config=json.loads(deployment_config)
            )
            
            return model, model_version
            
        except Exception as e:
            logger.error(f"Failed to load model {model_id} version {version}: {e}")
            raise
    
    def activate_model(self, model_id: str, version: str) -> bool:
        """Activate a specific model version"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Deactivate all versions of this model
            cursor.execute("""
                UPDATE models 
                SET is_active = 0 
                WHERE model_id = ?
            """, (model_id,))
            
            # Activate the specified version
            cursor.execute("""
                UPDATE models 
                SET is_active = 1 
                WHERE model_id = ? AND version = ?
            """, (model_id, version))
            
            conn.commit()
            conn.close()
            
            # Update cache
            self.active_models[model_id] = version
            
            logger.info(f"Activated model {model_id} version {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate model {model_id} version {version}: {e}")
            return False
    
    def get_active_version(self, model_id: str) -> Optional[str]:
        """Get the active version of a model"""
        
        # Check cache first
        if model_id in self.active_models:
            return self.active_models[model_id]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT version 
                FROM models 
                WHERE model_id = ? AND is_active = 1
            """, (model_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                version = row[0]
                self.active_models[model_id] = version
                return version
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get active version for model {model_id}: {e}")
            return None
    
    def list_models(self) -> List[ModelVersion]:
        """List all models in registry"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT model_id, version, model_type, created_at, created_by, 
                       model_path, metadata, performance_metrics, is_active, deployment_config
                FROM models 
                ORDER BY model_id, version DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            models = []
            for row in rows:
                model_version = ModelVersion(
                    model_id=row[0],
                    version=row[1],
                    model_type=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    created_by=row[4],
                    model_path=row[5],
                    metadata=json.loads(row[6]),
                    performance_metrics=json.loads(row[7]),
                    is_active=bool(row[8]),
                    deployment_config=json.loads(row[9])
                )
                models.append(model_version)
            
            return models
            
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def delete_model(self, model_id: str, version: str) -> bool:
        """Delete a model version"""
        
        try:
            # Remove from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM models 
                WHERE model_id = ? AND version = ?
            """, (model_id, version))
            
            conn.commit()
            conn.close()
            
            # Remove files
            model_dir = self.registry_path / model_id / version
            if model_dir.exists():
                shutil.rmtree(model_dir)
            
            # Remove from cache if active
            if self.active_models.get(model_id) == version:
                del self.active_models[model_id]
            
            logger.info(f"Deleted model {model_id} version {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete model {model_id} version {version}: {e}")
            return False

class ModelMonitor:
    """Model performance monitoring and alerting"""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Performance thresholds
        self.performance_thresholds = {
            'accuracy_drop': 0.05,  # 5% drop triggers alert
            'prediction_latency': 1000,  # 1 second
            'error_rate': 0.01  # 1% error rate
        }
        
        # Monitoring data
        self.prediction_logs = []
        self.performance_history = defaultdict(list)
        
    def start_monitoring(self):
        """Start continuous model monitoring"""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("Model monitoring started")
    
    def stop_monitoring(self):
        """Stop model monitoring"""
        
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        logger.info("Model monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        
        while self.monitoring_active:
            try:
                # Check all active models
                active_models = self.registry.active_models
                
                for model_id in active_models:
                    self._check_model_performance(model_id)
                
                # Sleep for monitoring interval
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _check_model_performance(self, model_id: str):
        """Check performance of a specific model"""
        
        try:
            version = self.registry.get_active_version(model_id)
            if not version:
                return
            
            # Get recent metrics
            recent_metrics = self._get_recent_metrics(model_id, version)
            
            # Check for performance degradation
            baseline_metrics = self._get_baseline_metrics(model_id, version)
            
            alerts = []
            
            for metric_name in ['accuracy', 'precision', 'recall', 'f1_score']:
                if metric_name in recent_metrics and metric_name in baseline_metrics:
                    recent_value = recent_metrics[metric_name]
                    baseline_value = baseline_metrics[metric_name]
                    
                    # Check for significant drop
                    drop_threshold = self.performance_thresholds.get('accuracy_drop', 0.05)
                    if (baseline_value - recent_value) > drop_threshold:
                        alert = self._create_performance_alert(
                            model_id, version, 'performance_degradation',
                            f"{metric_name} dropped from {baseline_value:.3f} to {recent_value:.3f}",
                            {'baseline': baseline_value, 'current': recent_value, 'drop': baseline_value - recent_value}
                        )
                        alerts.append(alert)
            
            # Check prediction latency
            if 'prediction_latency' in recent_metrics:
                latency = recent_metrics['prediction_latency']
                threshold = self.performance_thresholds.get('prediction_latency', 1000)
                
                if latency > threshold:
                    alert = self._create_performance_alert(
                        model_id, version, 'prediction_anomaly',
                        f"High prediction latency: {latency:.2f}ms > {threshold}ms",
                        {'latency': latency, 'threshold': threshold}
                    )
                    alerts.append(alert)
            
            # Store alerts
            for alert in alerts:
                self._store_alert(alert)
            
        except Exception as e:
            logger.error(f"Performance check failed for model {model_id}: {e}")
    
    def _get_recent_metrics(self, model_id: str, version: str, hours: int = 24) -> Dict[str, float]:
        """Get recent performance metrics"""
        
        try:
            conn = sqlite3.connect(self.registry.db_path)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT metric_type, AVG(metric_value) as avg_value
                FROM model_metrics 
                WHERE model_id = ? AND version = ? AND computed_at > ?
                GROUP BY metric_type
            """, (model_id, version, cutoff_time.isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
            
            return {row[0]: row[1] for row in rows}
            
        except Exception as e:
            logger.error(f"Failed to get recent metrics: {e}")
            return {}
    
    def _get_baseline_metrics(self, model_id: str, version: str) -> Dict[str, float]:
        """Get baseline performance metrics"""
        
        try:
            # Load model version to get stored performance metrics
            _, model_version = self.registry.load_model(model_id, version)
            return model_version.performance_metrics
            
        except Exception as e:
            logger.error(f"Failed to get baseline metrics: {e}")
            return {}
    
    def _create_performance_alert(self, model_id: str, version: str, alert_type: str,
                                message: str, metrics: Dict[str, Any]) -> ModelPerformanceAlert:
        """Create a performance alert"""
        
        # Determine severity
        if alert_type == 'performance_degradation':
            severity = 'high' if metrics.get('drop', 0) > 0.1 else 'medium'
        else:
            severity = 'medium'
        
        alert = ModelPerformanceAlert(
            alert_id=hashlib.md5(f"{model_id}_{version}_{alert_type}_{datetime.now()}".encode()).hexdigest()[:12],
            model_id=model_id,
            version=version,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metrics=metrics,
            triggered_at=datetime.now()
        )
        
        return alert
    
    def _store_alert(self, alert: ModelPerformanceAlert):
        """Store alert in database"""
        
        try:
            conn = sqlite3.connect(self.registry.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO model_alerts 
                (alert_id, model_id, version, alert_type, severity, message, metrics, triggered_at, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.model_id,
                alert.version,
                alert.alert_type,
                alert.severity,
                alert.message,
                json.dumps(alert.metrics),
                alert.triggered_at.isoformat(),
                int(alert.acknowledged)
            ))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"Performance alert: {alert.message}")
            
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
    
    def log_prediction(self, model_id: str, version: str, input_data: Any, 
                      prediction: Any, latency_ms: float, success: bool = True):
        """Log a prediction for monitoring"""
        
        prediction_log = {
            'timestamp': datetime.now(),
            'model_id': model_id,
            'version': version,
            'input_hash': hashlib.md5(str(input_data).encode()).hexdigest(),
            'prediction': prediction,
            'latency_ms': latency_ms,
            'success': success
        }
        
        self.prediction_logs.append(prediction_log)
        
        # Keep only recent logs (last 10,000)
        if len(self.prediction_logs) > 10000:
            self.prediction_logs = self.prediction_logs[-10000:]
    
    def record_performance_metrics(self, model_id: str, version: str, 
                                 metrics: Dict[str, float], data_split: str = 'production',
                                 sample_size: int = 1):
        """Record performance metrics for a model"""
        
        try:
            conn = sqlite3.connect(self.registry.db_path)
            cursor = conn.cursor()
            
            for metric_name, metric_value in metrics.items():
                metric_record = ModelMetrics(
                    model_id=model_id,
                    version=version,
                    metric_type=metric_name,
                    metric_value=metric_value,
                    computed_at=datetime.now(),
                    data_split=data_split,
                    sample_size=sample_size
                )
                
                cursor.execute("""
                    INSERT INTO model_metrics 
                    (model_id, version, metric_type, metric_value, computed_at, data_split, sample_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric_record.model_id,
                    metric_record.version,
                    metric_record.metric_type,
                    metric_record.metric_value,
                    metric_record.computed_at.isoformat(),
                    metric_record.data_split,
                    metric_record.sample_size
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
    
    def get_alerts(self, model_id: str = None, acknowledged: bool = False) -> List[ModelPerformanceAlert]:
        """Get model alerts"""
        
        try:
            conn = sqlite3.connect(self.registry.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT alert_id, model_id, version, alert_type, severity, message, 
                       metrics, triggered_at, acknowledged
                FROM model_alerts 
                WHERE acknowledged = ?
            """
            params = [int(acknowledged)]
            
            if model_id:
                query += " AND model_id = ?"
                params.append(model_id)
            
            query += " ORDER BY triggered_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alert = ModelPerformanceAlert(
                    alert_id=row[0],
                    model_id=row[1],
                    version=row[2],
                    alert_type=row[3],
                    severity=row[4],
                    message=row[5],
                    metrics=json.loads(row[6]),
                    triggered_at=datetime.fromisoformat(row[7]),
                    acknowledged=bool(row[8])
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

class ABTestManager:
    """A/B testing for model comparison"""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.active_tests = {}
    
    def create_ab_test(self, test_id: str, model_a_id: str, model_b_id: str,
                      metric_name: str, traffic_split: float = 0.5,
                      duration_days: int = 7) -> bool:
        """Create a new A/B test"""
        
        try:
            # Validate models exist
            model_a_version = self.registry.get_active_version(model_a_id)
            model_b_version = self.registry.get_active_version(model_b_id)
            
            if not model_a_version or not model_b_version:
                logger.error("Both models must have active versions for A/B testing")
                return False
            
            test_config = {
                'test_id': test_id,
                'model_a_id': model_a_id,
                'model_a_version': model_a_version,
                'model_b_id': model_b_id,
                'model_b_version': model_b_version,
                'metric_name': metric_name,
                'traffic_split': traffic_split,
                'start_time': datetime.now(),
                'duration_days': duration_days,
                'model_a_results': [],
                'model_b_results': []
            }
            
            self.active_tests[test_id] = test_config
            
            logger.info(f"A/B test {test_id} created: {model_a_id} vs {model_b_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create A/B test {test_id}: {e}")
            return False
    
    def route_prediction(self, test_id: str, request_id: str) -> str:
        """Route prediction request to appropriate model in A/B test"""
        
        if test_id not in self.active_tests:
            logger.warning(f"A/B test {test_id} not found")
            return None
        
        test_config = self.active_tests[test_id]
        
        # Simple hash-based routing for consistent assignment
        hash_value = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        
        if (hash_value % 100) < (test_config['traffic_split'] * 100):
            return test_config['model_a_id']
        else:
            return test_config['model_b_id']
    
    def record_ab_result(self, test_id: str, model_id: str, metric_value: float):
        """Record A/B test result"""
        
        if test_id not in self.active_tests:
            return
        
        test_config = self.active_tests[test_id]
        
        if model_id == test_config['model_a_id']:
            test_config['model_a_results'].append(metric_value)
        elif model_id == test_config['model_b_id']:
            test_config['model_b_results'].append(metric_value)
    
    def analyze_ab_test(self, test_id: str) -> Optional[ABTestResult]:
        """Analyze A/B test results"""
        
        if test_id not in self.active_tests:
            return None
        
        test_config = self.active_tests[test_id]
        
        # Check if test has enough data
        if len(test_config['model_a_results']) < 30 or len(test_config['model_b_results']) < 30:
            logger.info(f"A/B test {test_id} needs more data for analysis")
            return None
        
        # Calculate means
        model_a_mean = np.mean(test_config['model_a_results'])
        model_b_mean = np.mean(test_config['model_b_results'])
        
        # Simple statistical significance test (t-test approximation)
        model_a_std = np.std(test_config['model_a_results'])
        model_b_std = np.std(test_config['model_b_results'])
        
        n_a = len(test_config['model_a_results'])
        n_b = len(test_config['model_b_results'])
        
        # Standard error
        se = np.sqrt((model_a_std**2 / n_a) + (model_b_std**2 / n_b))
        
        # T-statistic
        t_stat = abs(model_a_mean - model_b_mean) / se if se > 0 else 0
        
        # Approximate p-value (simplified)
        statistical_significance = max(0, 1 - (t_stat / 2))  # Simplified calculation
        
        # Determine winner
        if statistical_significance < 0.05:  # 95% confidence
            winner = 'model_a' if model_a_mean > model_b_mean else 'model_b'
            confidence = 0.95
        else:
            winner = 'tie'
            confidence = statistical_significance
        
        # Calculate test duration
        test_duration = (datetime.now() - test_config['start_time']).days
        
        result = ABTestResult(
            test_id=test_id,
            model_a_id=test_config['model_a_id'],
            model_b_id=test_config['model_b_id'],
            metric_name=test_config['metric_name'],
            model_a_value=model_a_mean,
            model_b_value=model_b_mean,
            statistical_significance=statistical_significance,
            winner=winner,
            confidence_level=confidence,
            test_duration_days=test_duration,
            sample_size=n_a + n_b
        )
        
        # Store result
        self._store_ab_result(result)
        
        return result
    
    def _store_ab_result(self, result: ABTestResult):
        """Store A/B test result"""
        
        try:
            conn = sqlite3.connect(self.registry.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO ab_tests 
                (test_id, model_a_id, model_b_id, metric_name, model_a_value, model_b_value,
                 statistical_significance, winner, confidence_level, test_duration_days, sample_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.test_id,
                result.model_a_id,
                result.model_b_id,
                result.metric_name,
                result.model_a_value,
                result.model_b_value,
                result.statistical_significance,
                result.winner,
                result.confidence_level,
                result.test_duration_days,
                result.sample_size
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store A/B test result: {e}")

class MLDeploymentService:
    """Main ML deployment and monitoring service"""
    
    def __init__(self, registry_path: str = "model_registry"):
        self.registry = ModelRegistry(registry_path)
        self.monitor = ModelMonitor(self.registry)
        self.ab_tester = ABTestManager(self.registry)
        
        # Deployment executor
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Model cache for fast serving
        self.model_cache = {}
    
    async def deploy_model(self, model: Any, model_id: str, version: str, model_type: str,
                          metadata: Dict[str, Any] = None, 
                          performance_metrics: Dict[str, float] = None,
                          auto_activate: bool = True) -> bool:
        """Deploy a new model version"""
        
        try:
            logger.info(f"Deploying model {model_id} version {version}...")
            
            # Register model
            model_version = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.registry.register_model,
                model, model_id, version, model_type, metadata, performance_metrics
            )
            
            # Activate if requested
            if auto_activate:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.registry.activate_model,
                    model_id, version
                )
            
            # Clear cache to force reload
            if model_id in self.model_cache:
                del self.model_cache[model_id]
            
            logger.info(f"Model {model_id} version {version} deployed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy model {model_id}: {e}")
            return False
    
    async def predict(self, model_id: str, input_data: Any, request_id: str = None) -> Tuple[Any, Dict[str, Any]]:
        """Make prediction using deployed model"""
        
        start_time = time.time()
        
        try:
            # Load model (with caching)
            if model_id not in self.model_cache:
                model, model_version = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.registry.load_model,
                    model_id
                )
                
                self.model_cache[model_id] = {
                    'model': model,
                    'version': model_version,
                    'loaded_at': datetime.now()
                }
            
            cached_model = self.model_cache[model_id]
            model = cached_model['model']
            version = cached_model['version'].version
            
            # Make prediction
            if hasattr(model, 'predict'):
                if isinstance(input_data, pd.DataFrame):
                    prediction = model.predict(input_data)
                elif isinstance(input_data, np.ndarray):
                    prediction = model.predict(input_data)
                else:
                    # Convert to numpy array if needed
                    input_array = np.array(input_data).reshape(1, -1)
                    prediction = model.predict(input_array)
            else:
                # Custom model interface
                prediction = model(input_data)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log prediction for monitoring
            self.monitor.log_prediction(
                model_id, version, input_data, prediction, latency_ms, True
            )
            
            # Metadata
            metadata = {
                'model_id': model_id,
                'version': version,
                'latency_ms': latency_ms,
                'timestamp': datetime.now().isoformat()
            }
            
            return prediction, metadata
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Log failed prediction
            version = self.registry.get_active_version(model_id)
            self.monitor.log_prediction(
                model_id, version or 'unknown', input_data, None, latency_ms, False
            )
            
            logger.error(f"Prediction failed for model {model_id}: {e}")
            raise
    
    def start_monitoring(self):
        """Start model monitoring"""
        self.monitor.start_monitoring()
    
    def stop_monitoring(self):
        """Stop model monitoring"""
        self.monitor.stop_monitoring()
    
    async def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """Get comprehensive model status"""
        
        try:
            # Get active version
            active_version = self.registry.get_active_version(model_id)
            
            if not active_version:
                return {'status': 'no_active_version'}
            
            # Get model info
            _, model_version = self.registry.load_model(model_id, active_version)
            
            # Get recent alerts
            alerts = self.monitor.get_alerts(model_id, acknowledged=False)
            
            # Get recent metrics
            recent_metrics = self.monitor._get_recent_metrics(model_id, active_version)
            
            status = {
                'model_id': model_id,
                'active_version': active_version,
                'status': 'healthy',
                'deployment_info': asdict(model_version),
                'recent_metrics': recent_metrics,
                'alerts': [asdict(alert) for alert in alerts[-5:]],  # Last 5 alerts
                'cache_status': 'cached' if model_id in self.model_cache else 'not_cached'
            }
            
            # Determine overall health status
            if alerts:
                critical_alerts = [a for a in alerts if a.severity == 'critical']
                high_alerts = [a for a in alerts if a.severity == 'high']
                
                if critical_alerts:
                    status['status'] = 'critical'
                elif high_alerts:
                    status['status'] = 'warning'
                else:
                    status['status'] = 'caution'
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get model status for {model_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def rollback_model(self, model_id: str, target_version: str = None) -> bool:
        """Rollback to previous model version"""
        
        try:
            if target_version is None:
                # Find previous version
                models = self.registry.list_models()
                model_versions = [m for m in models if m.model_id == model_id]
                model_versions.sort(key=lambda x: x.created_at, reverse=True)
                
                if len(model_versions) < 2:
                    logger.error(f"No previous version available for rollback of {model_id}")
                    return False
                
                target_version = model_versions[1].version  # Second most recent
            
            # Activate target version
            success = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.registry.activate_model,
                model_id, target_version
            )
            
            if success:
                # Clear cache to force reload
                if model_id in self.model_cache:
                    del self.model_cache[model_id]
                
                logger.info(f"Model {model_id} rolled back to version {target_version}")
            
            return success
            
        except Exception as e:
            logger.error(f"Rollback failed for model {model_id}: {e}")
            return False

# Global deployment service
ml_deployment_service = MLDeploymentService()

# Convenience functions
async def deploy_recommendation_model(model, performance_metrics: Dict[str, float]):
    """Deploy recommendation model"""
    return await ml_deployment_service.deploy_model(
        model, 'recommendation_engine', 'v1.0', 'sklearn',
        metadata={'description': 'Movie recommendation model'},
        performance_metrics=performance_metrics
    )

async def deploy_demand_prediction_model(model, performance_metrics: Dict[str, float]):
    """Deploy demand prediction model"""
    return await ml_deployment_service.deploy_model(
        model, 'demand_predictor', 'v1.0', 'sklearn',
        metadata={'description': 'Movie demand prediction model'},
        performance_metrics=performance_metrics
    )

async def get_recommendation_prediction(user_features: np.ndarray) -> Tuple[Any, Dict[str, Any]]:
    """Get recommendation prediction"""
    return await ml_deployment_service.predict('recommendation_engine', user_features)

async def get_demand_prediction(movie_features: np.ndarray) -> Tuple[Any, Dict[str, Any]]:
    """Get demand prediction"""
    return await ml_deployment_service.predict('demand_predictor', movie_features)

async def start_ab_test_recommendation_models(model_a_path: str, model_b_path: str):
    """Start A/B test for recommendation models"""
    
    # Load models
    model_a = joblib.load(model_a_path)
    model_b = joblib.load(model_b_path)
    
    # Deploy both models
    await ml_deployment_service.deploy_model(
        model_a, 'recommendation_a', 'v1.0', 'sklearn', auto_activate=True
    )
    await ml_deployment_service.deploy_model(
        model_b, 'recommendation_b', 'v1.0', 'sklearn', auto_activate=True
    )
    
    # Create A/B test
    ml_deployment_service.ab_tester.create_ab_test(
        'rec_model_test', 'recommendation_a', 'recommendation_b', 'accuracy'
    )
    
    logger.info("A/B test for recommendation models started")