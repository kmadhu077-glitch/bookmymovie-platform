"""
Advanced Analytics Dashboard Service
Real-time metrics visualization, predictive analytics, and business intelligence
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import sqlite3
import numpy as np
import pandas as pd
from enum import Enum
import threading
import secrets

# For data visualization preparation
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"

class DashboardType(Enum):
    """Dashboard types"""
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    MARKETING = "marketing"
    FINANCIAL = "financial"
    TECHNICAL = "technical"

@dataclass
class Metric:
    """Metric data structure"""
    metric_id: str
    name: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None
    metadata: Dict[str, Any] = None

@dataclass
class Chart:
    """Chart configuration"""
    chart_id: str
    title: str
    chart_type: str  # line, bar, pie, heatmap, gauge, area
    data_source: str
    config: Dict[str, Any]
    filters: List[Dict[str, Any]] = None
    refresh_interval: int = 300  # seconds
    is_real_time: bool = False

@dataclass
class Dashboard:
    """Dashboard configuration"""
    dashboard_id: str
    title: str
    dashboard_type: DashboardType
    charts: List[Chart]
    layout: Dict[str, Any]
    access_permissions: List[str]
    created_by: str
    created_at: datetime
    last_updated: datetime

@dataclass
class AlertRule:
    """Analytics alert rule"""
    rule_id: str
    name: str
    metric_name: str
    condition: str  # >, <, ==, !=, >=, <=
    threshold: float
    time_window: int  # minutes
    severity: str  # low, medium, high, critical
    notification_channels: List[str]
    is_enabled: bool = True

class MetricsCollector:
    """Real-time metrics collection and aggregation"""
    
    def __init__(self):
        self.metrics_buffer = deque(maxlen=10000)
        self.aggregated_metrics = defaultdict(dict)
        self.metric_history = defaultdict(lambda: deque(maxlen=1000))
        
        # Real-time counters
        self.counters = defaultdict(float)
        self.gauges = defaultdict(float)
        self.rates = defaultdict(lambda: {'count': 0, 'window_start': time.time()})
        
        # Database for persistence
        self.db_path = "analytics.db"
        self._init_database()
        
        # Collection thread
        self._collection_active = False
        self._collection_thread = None
    
    def _init_database(self):
        """Initialize analytics database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                metric_id TEXT,
                name TEXT,
                metric_type TEXT,
                value REAL,
                unit TEXT,
                timestamp TEXT,
                tags TEXT,
                metadata TEXT
            )
        """)
        
        # Dashboards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashboards (
                dashboard_id TEXT PRIMARY KEY,
                title TEXT,
                dashboard_type TEXT,
                charts TEXT,
                layout TEXT,
                access_permissions TEXT,
                created_by TEXT,
                created_at TEXT,
                last_updated TEXT
            )
        """)
        
        # Alert rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT,
                metric_name TEXT,
                condition TEXT,
                threshold REAL,
                time_window INTEGER,
                severity TEXT,
                notification_channels TEXT,
                is_enabled INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def start_collection(self):
        """Start metrics collection"""
        
        if self._collection_active:
            return
        
        self._collection_active = True
        self._collection_thread = threading.Thread(target=self._collection_loop)
        self._collection_thread.daemon = True
        self._collection_thread.start()
        
        logger.info("Metrics collection started")
    
    def stop_collection(self):
        """Stop metrics collection"""
        
        self._collection_active = False
        if self._collection_thread:
            self._collection_thread.join()
        
        logger.info("Metrics collection stopped")
    
    def _collection_loop(self):
        """Main collection loop"""
        
        while self._collection_active:
            try:
                # Aggregate and store metrics
                self._aggregate_metrics()
                
                # Sleep for collection interval
                time.sleep(10)  # Collect every 10 seconds
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(10)
    
    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
                     unit: str = "", tags: Dict[str, str] = None):
        """Record a metric"""
        
        metric = Metric(
            metric_id=secrets.token_hex(8),
            name=name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        self.metrics_buffer.append(metric)
        
        # Update real-time counters
        if metric_type == MetricType.COUNTER:
            self.counters[name] += value
        elif metric_type == MetricType.GAUGE:
            self.gauges[name] = value
        elif metric_type == MetricType.RATE:
            self._update_rate(name, value)
    
    def _update_rate(self, name: str, value: float):
        """Update rate metric"""
        
        current_time = time.time()
        rate_data = self.rates[name]
        
        # Reset window if needed (1 minute windows)
        if current_time - rate_data['window_start'] > 60:
            rate_data['count'] = 0
            rate_data['window_start'] = current_time
        
        rate_data['count'] += value
    
    def _aggregate_metrics(self):
        """Aggregate metrics for dashboard queries"""
        
        current_time = datetime.now()
        
        # Process buffer
        while self.metrics_buffer:
            metric = self.metrics_buffer.popleft()
            
            # Store in history
            self.metric_history[metric.name].append(metric)
            
            # Store in database (batch insert for performance)
            self._store_metric(metric)
        
        # Calculate aggregated metrics
        for name, history in self.metric_history.items():
            if not history:
                continue
            
            # Recent metrics (last 5 minutes)
            recent_metrics = [
                m for m in history
                if (current_time - m.timestamp).total_seconds() < 300
            ]
            
            if recent_metrics:
                values = [m.value for m in recent_metrics]
                
                self.aggregated_metrics[name] = {
                    'current': values[-1],
                    'avg_5min': np.mean(values),
                    'min_5min': np.min(values),
                    'max_5min': np.max(values),
                    'count_5min': len(values),
                    'last_updated': current_time.isoformat()
                }
    
    def _store_metric(self, metric: Metric):
        """Store metric in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO metrics 
                (metric_id, name, metric_type, value, unit, timestamp, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.metric_id,
                metric.name,
                metric.metric_type.value,
                metric.value,
                metric.unit,
                metric.timestamp.isoformat(),
                json.dumps(metric.tags),
                json.dumps(metric.metadata) if metric.metadata else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store metric: {e}")
    
    def get_metric_history(self, metric_name: str, start_time: datetime, 
                          end_time: datetime) -> List[Metric]:
        """Get metric history for time range"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT metric_id, name, metric_type, value, unit, timestamp, tags, metadata
                FROM metrics 
                WHERE name = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """, (metric_name, start_time.isoformat(), end_time.isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
            
            metrics = []
            for row in rows:
                metric = Metric(
                    metric_id=row[0],
                    name=row[1],
                    metric_type=MetricType(row[2]),
                    value=row[3],
                    unit=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    tags=json.loads(row[6]),
                    metadata=json.loads(row[7]) if row[7] else None
                )
                metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metric history: {e}")
            return []
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics"""
        
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'rates': {
                name: data['count'] / 60  # per minute rate
                for name, data in self.rates.items()
            },
            'aggregated': dict(self.aggregated_metrics),
            'timestamp': datetime.now().isoformat()
        }

class ChartDataProcessor:
    """Process data for different chart types"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
    
    def generate_line_chart_data(self, metric_names: List[str], time_range: str = "1h") -> Dict[str, Any]:
        """Generate data for line chart"""
        
        end_time = datetime.now()
        
        if time_range == "1h":
            start_time = end_time - timedelta(hours=1)
            interval_minutes = 5
        elif time_range == "24h":
            start_time = end_time - timedelta(hours=24)
            interval_minutes = 60
        elif time_range == "7d":
            start_time = end_time - timedelta(days=7)
            interval_minutes = 360
        else:
            start_time = end_time - timedelta(hours=1)
            interval_minutes = 5
        
        # Get data for each metric
        series_data = []
        
        for metric_name in metric_names:
            metrics = self.metrics_collector.get_metric_history(metric_name, start_time, end_time)
            
            if not metrics:
                continue
            
            # Group by time intervals
            time_buckets = defaultdict(list)
            
            for metric in metrics:
                # Round to nearest interval
                bucket_time = self._round_time(metric.timestamp, interval_minutes)
                time_buckets[bucket_time].append(metric.value)
            
            # Create time series
            time_points = []
            values = []
            
            current_time = start_time
            while current_time <= end_time:
                bucket_time = self._round_time(current_time, interval_minutes)
                
                if bucket_time in time_buckets:
                    # Use average value for the bucket
                    avg_value = np.mean(time_buckets[bucket_time])
                    values.append(avg_value)
                else:
                    # Use last known value or 0
                    values.append(values[-1] if values else 0)
                
                time_points.append(current_time.isoformat())
                current_time += timedelta(minutes=interval_minutes)
            
            series_data.append({
                'name': metric_name,
                'data': values,
                'timestamps': time_points
            })
        
        return {
            'type': 'line',
            'series': series_data,
            'time_range': time_range,
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_bar_chart_data(self, metric_name: str, group_by: str = None) -> Dict[str, Any]:
        """Generate data for bar chart"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        metrics = self.metrics_collector.get_metric_history(metric_name, start_time, end_time)
        
        if group_by == "hour":
            # Group by hour
            hour_data = defaultdict(float)
            
            for metric in metrics:
                hour_key = metric.timestamp.strftime('%H:00')
                hour_data[hour_key] += metric.value
            
            categories = list(hour_data.keys())
            values = list(hour_data.values())
            
        elif group_by == "day_of_week":
            # Group by day of week
            dow_data = defaultdict(float)
            dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            for metric in metrics:
                dow_index = metric.timestamp.weekday()
                dow_data[dow_names[dow_index]] += metric.value
            
            categories = dow_names
            values = [dow_data[day] for day in dow_names]
            
        else:
            # Default: last 10 data points
            recent_metrics = metrics[-10:] if len(metrics) > 10 else metrics
            categories = [m.timestamp.strftime('%H:%M') for m in recent_metrics]
            values = [m.value for m in recent_metrics]
        
        return {
            'type': 'bar',
            'categories': categories,
            'values': values,
            'metric_name': metric_name,
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_pie_chart_data(self, metric_name: str, breakdown_field: str) -> Dict[str, Any]:
        """Generate data for pie chart"""
        
        # For demo, generate sample breakdown data
        # In production, this would analyze actual tag data
        
        sample_data = {
            'Action': 35,
            'Comedy': 25,
            'Drama': 20,
            'Horror': 12,
            'Romance': 8
        }
        
        if breakdown_field == "theater_type":
            sample_data = {
                'IMAX': 30,
                'Standard': 45,
                'Premium': 15,
                'Drive-in': 10
            }
        elif breakdown_field == "age_group":
            sample_data = {
                '18-25': 28,
                '26-35': 32,
                '36-45': 22,
                '46-55': 12,
                '55+': 6
            }
        
        return {
            'type': 'pie',
            'labels': list(sample_data.keys()),
            'values': list(sample_data.values()),
            'breakdown_field': breakdown_field,
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_heatmap_data(self, metric_name: str) -> Dict[str, Any]:
        """Generate data for heatmap (time-based activity)"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        metrics = self.metrics_collector.get_metric_history(metric_name, start_time, end_time)
        
        # Create 7x24 heatmap (days x hours)
        heatmap_data = np.zeros((7, 24))
        
        for metric in metrics:
            day_index = metric.timestamp.weekday()
            hour_index = metric.timestamp.hour
            heatmap_data[day_index][hour_index] += metric.value
        
        return {
            'type': 'heatmap',
            'data': heatmap_data.tolist(),
            'x_labels': [f"{i:02d}:00" for i in range(24)],  # Hours
            'y_labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],  # Days
            'metric_name': metric_name,
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_gauge_data(self, metric_name: str, min_value: float = 0, max_value: float = 100) -> Dict[str, Any]:
        """Generate data for gauge chart"""
        
        # Get current value
        real_time_metrics = self.metrics_collector.get_real_time_metrics()
        current_value = real_time_metrics['gauges'].get(metric_name, 0)
        
        # Calculate percentage
        percentage = ((current_value - min_value) / (max_value - min_value)) * 100
        percentage = max(0, min(100, percentage))
        
        return {
            'type': 'gauge',
            'current_value': current_value,
            'percentage': percentage,
            'min_value': min_value,
            'max_value': max_value,
            'metric_name': metric_name,
            'generated_at': datetime.now().isoformat()
        }
    
    def _round_time(self, dt: datetime, interval_minutes: int) -> datetime:
        """Round datetime to nearest interval"""
        
        total_minutes = dt.hour * 60 + dt.minute
        rounded_minutes = (total_minutes // interval_minutes) * interval_minutes
        
        return dt.replace(hour=rounded_minutes // 60, minute=rounded_minutes % 60, second=0, microsecond=0)

class DashboardManager:
    """Manage analytics dashboards"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.chart_processor = ChartDataProcessor(metrics_collector)
        self.dashboards = {}
        self.chart_cache = {}  # Cache for expensive chart queries
        
        # Initialize default dashboards
        self._create_default_dashboards()
    
    def _create_default_dashboards(self):
        """Create default dashboards"""
        
        # Executive Dashboard
        executive_charts = [
            Chart(
                chart_id="revenue_trend",
                title="Revenue Trend",
                chart_type="line",
                data_source="revenue_metrics",
                config={"time_range": "7d", "metrics": ["daily_revenue", "booking_count"]},
                is_real_time=True
            ),
            Chart(
                chart_id="user_growth",
                title="User Growth",
                chart_type="area",
                data_source="user_metrics",
                config={"time_range": "30d", "metrics": ["new_users", "active_users"]}
            ),
            Chart(
                chart_id="booking_breakdown",
                title="Bookings by Genre",
                chart_type="pie",
                data_source="booking_metrics",
                config={"breakdown_field": "genre"}
            ),
            Chart(
                chart_id="theater_occupancy",
                title="Theater Occupancy Rate",
                chart_type="gauge",
                data_source="occupancy_metrics",
                config={"metric": "avg_occupancy", "min": 0, "max": 100}
            )
        ]
        
        executive_dashboard = Dashboard(
            dashboard_id="executive",
            title="Executive Dashboard",
            dashboard_type=DashboardType.EXECUTIVE,
            charts=executive_charts,
            layout={
                "grid": [
                    ["revenue_trend", "user_growth"],
                    ["booking_breakdown", "theater_occupancy"]
                ]
            },
            access_permissions=["executive", "admin"],
            created_by="system",
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.dashboards["executive"] = executive_dashboard
        
        # Operational Dashboard
        operational_charts = [
            Chart(
                chart_id="booking_activity",
                title="Real-time Booking Activity",
                chart_type="line",
                data_source="booking_metrics",
                config={"time_range": "1h", "metrics": ["bookings_per_minute"]},
                is_real_time=True,
                refresh_interval=30
            ),
            Chart(
                chart_id="system_performance",
                title="System Performance",
                chart_type="line",
                data_source="system_metrics",
                config={"time_range": "1h", "metrics": ["response_time", "error_rate"]},
                is_real_time=True
            ),
            Chart(
                chart_id="user_activity_heatmap",
                title="User Activity Heatmap",
                chart_type="heatmap",
                data_source="user_metrics",
                config={"metric": "active_users"}
            ),
            Chart(
                chart_id="popular_movies",
                title="Most Popular Movies",
                chart_type="bar",
                data_source="movie_metrics",
                config={"metric": "booking_count", "group_by": "movie"}
            )
        ]
        
        operational_dashboard = Dashboard(
            dashboard_id="operational",
            title="Operational Dashboard",
            dashboard_type=DashboardType.OPERATIONAL,
            charts=operational_charts,
            layout={
                "grid": [
                    ["booking_activity", "system_performance"],
                    ["user_activity_heatmap", "popular_movies"]
                ]
            },
            access_permissions=["manager", "admin"],
            created_by="system",
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.dashboards["operational"] = operational_dashboard
        
        # Marketing Dashboard
        marketing_charts = [
            Chart(
                chart_id="user_acquisition",
                title="User Acquisition Channels",
                chart_type="pie",
                data_source="marketing_metrics",
                config={"breakdown_field": "acquisition_channel"}
            ),
            Chart(
                chart_id="campaign_performance",
                title="Campaign Performance",
                chart_type="bar",
                data_source="marketing_metrics",
                config={"metric": "conversion_rate", "group_by": "campaign"}
            ),
            Chart(
                chart_id="demographic_analysis",
                title="User Demographics",
                chart_type="pie",
                data_source="user_metrics",
                config={"breakdown_field": "age_group"}
            ),
            Chart(
                chart_id="retention_cohort",
                title="User Retention Cohort",
                chart_type="heatmap",
                data_source="retention_metrics",
                config={"metric": "retention_rate"}
            )
        ]
        
        marketing_dashboard = Dashboard(
            dashboard_id="marketing",
            title="Marketing Dashboard",
            dashboard_type=DashboardType.MARKETING,
            charts=marketing_charts,
            layout={
                "grid": [
                    ["user_acquisition", "campaign_performance"],
                    ["demographic_analysis", "retention_cohort"]
                ]
            },
            access_permissions=["marketing", "admin"],
            created_by="system",
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.dashboards["marketing"] = marketing_dashboard
    
    async def get_dashboard_data(self, dashboard_id: str, user_permissions: List[str]) -> Dict[str, Any]:
        """Get complete dashboard data"""
        
        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            return {"error": "Dashboard not found"}
        
        # Check permissions
        if not any(perm in dashboard.access_permissions for perm in user_permissions):
            return {"error": "Access denied"}
        
        # Generate chart data
        chart_data = {}
        
        for chart in dashboard.charts:
            try:
                data = await self._generate_chart_data(chart)
                chart_data[chart.chart_id] = data
            except Exception as e:
                logger.error(f"Failed to generate chart data for {chart.chart_id}: {e}")
                chart_data[chart.chart_id] = {"error": str(e)}
        
        return {
            "dashboard": asdict(dashboard),
            "chart_data": chart_data,
            "generated_at": datetime.now().isoformat()
        }
    
    async def _generate_chart_data(self, chart: Chart) -> Dict[str, Any]:
        """Generate data for a specific chart"""
        
        # Check cache for non-real-time charts
        cache_key = f"{chart.chart_id}_{hash(json.dumps(chart.config, sort_keys=True))}"
        
        if not chart.is_real_time and cache_key in self.chart_cache:
            cached_data, timestamp = self.chart_cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < chart.refresh_interval:
                return cached_data
        
        # Generate chart data based on type
        if chart.chart_type == "line":
            data = self.chart_processor.generate_line_chart_data(
                chart.config.get("metrics", []),
                chart.config.get("time_range", "1h")
            )
        elif chart.chart_type == "bar":
            data = self.chart_processor.generate_bar_chart_data(
                chart.config.get("metric", ""),
                chart.config.get("group_by")
            )
        elif chart.chart_type == "pie":
            data = self.chart_processor.generate_pie_chart_data(
                chart.config.get("metric", ""),
                chart.config.get("breakdown_field", "")
            )
        elif chart.chart_type == "heatmap":
            data = self.chart_processor.generate_heatmap_data(
                chart.config.get("metric", "")
            )
        elif chart.chart_type == "gauge":
            data = self.chart_processor.generate_gauge_data(
                chart.config.get("metric", ""),
                chart.config.get("min", 0),
                chart.config.get("max", 100)
            )
        elif chart.chart_type == "area":
            # Area chart is similar to line chart
            data = self.chart_processor.generate_line_chart_data(
                chart.config.get("metrics", []),
                chart.config.get("time_range", "1h")
            )
            data["type"] = "area"
        else:
            data = {"error": f"Unsupported chart type: {chart.chart_type}"}
        
        # Add chart metadata
        data["chart_id"] = chart.chart_id
        data["title"] = chart.title
        data["chart_type"] = chart.chart_type
        
        # Cache non-real-time charts
        if not chart.is_real_time:
            self.chart_cache[cache_key] = (data, datetime.now())
        
        return data
    
    def create_custom_dashboard(self, dashboard_id: str, title: str, dashboard_type: DashboardType,
                               charts: List[Chart], layout: Dict[str, Any], 
                               access_permissions: List[str], created_by: str) -> Dashboard:
        """Create custom dashboard"""
        
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            title=title,
            dashboard_type=dashboard_type,
            charts=charts,
            layout=layout,
            access_permissions=access_permissions,
            created_by=created_by,
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.dashboards[dashboard_id] = dashboard
        
        # Store in database
        self._store_dashboard(dashboard)
        
        return dashboard
    
    def _store_dashboard(self, dashboard: Dashboard):
        """Store dashboard in database"""
        
        try:
            conn = sqlite3.connect(self.metrics_collector.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO dashboards 
                (dashboard_id, title, dashboard_type, charts, layout, access_permissions,
                 created_by, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dashboard.dashboard_id,
                dashboard.title,
                dashboard.dashboard_type.value,
                json.dumps([asdict(chart) for chart in dashboard.charts], default=str),
                json.dumps(dashboard.layout),
                json.dumps(dashboard.access_permissions),
                dashboard.created_by,
                dashboard.created_at.isoformat(),
                dashboard.last_updated.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store dashboard: {e}")
    
    def get_available_dashboards(self, user_permissions: List[str]) -> List[Dict[str, Any]]:
        """Get list of dashboards user can access"""
        
        accessible_dashboards = []
        
        for dashboard in self.dashboards.values():
            if any(perm in dashboard.access_permissions for perm in user_permissions):
                accessible_dashboards.append({
                    "dashboard_id": dashboard.dashboard_id,
                    "title": dashboard.title,
                    "dashboard_type": dashboard.dashboard_type.value,
                    "last_updated": dashboard.last_updated.isoformat()
                })
        
        return accessible_dashboards

class AlertManager:
    """Manage analytics alerts and notifications"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        
        # Alert checking thread
        self._alert_checking_active = False
        self._alert_thread = None
    
    def create_alert_rule(self, rule_id: str, name: str, metric_name: str,
                         condition: str, threshold: float, time_window: int,
                         severity: str, notification_channels: List[str]) -> AlertRule:
        """Create new alert rule"""
        
        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            time_window=time_window,
            severity=severity,
            notification_channels=notification_channels
        )
        
        self.alert_rules[rule_id] = rule
        
        # Store in database
        self._store_alert_rule(rule)
        
        return rule
    
    def _store_alert_rule(self, rule: AlertRule):
        """Store alert rule in database"""
        
        try:
            conn = sqlite3.connect(self.metrics_collector.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO alert_rules 
                (rule_id, name, metric_name, condition, threshold, time_window,
                 severity, notification_channels, is_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.rule_id,
                rule.name,
                rule.metric_name,
                rule.condition,
                rule.threshold,
                rule.time_window,
                rule.severity,
                json.dumps(rule.notification_channels),
                int(rule.is_enabled)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store alert rule: {e}")
    
    def start_alert_monitoring(self):
        """Start alert monitoring"""
        
        if self._alert_checking_active:
            return
        
        self._alert_checking_active = True
        self._alert_thread = threading.Thread(target=self._alert_loop)
        self._alert_thread.daemon = True
        self._alert_thread.start()
        
        logger.info("Alert monitoring started")
    
    def stop_alert_monitoring(self):
        """Stop alert monitoring"""
        
        self._alert_checking_active = False
        if self._alert_thread:
            self._alert_thread.join()
        
        logger.info("Alert monitoring stopped")
    
    def _alert_loop(self):
        """Main alert checking loop"""
        
        while self._alert_checking_active:
            try:
                self._check_alert_rules()
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Alert checking error: {e}")
                time.sleep(30)
    
    def _check_alert_rules(self):
        """Check all alert rules"""
        
        current_time = datetime.now()
        
        for rule in self.alert_rules.values():
            if not rule.is_enabled:
                continue
            
            try:
                # Get recent metrics for the rule
                start_time = current_time - timedelta(minutes=rule.time_window)
                metrics = self.metrics_collector.get_metric_history(
                    rule.metric_name, start_time, current_time
                )
                
                if not metrics:
                    continue
                
                # Calculate aggregated value (average for the time window)
                values = [m.value for m in metrics]
                avg_value = np.mean(values)
                
                # Check condition
                alert_triggered = self._evaluate_condition(avg_value, rule.condition, rule.threshold)
                
                alert_key = f"{rule.rule_id}_{rule.metric_name}"
                
                if alert_triggered and alert_key not in self.active_alerts:
                    # Trigger new alert
                    self._trigger_alert(rule, avg_value)
                    
                elif not alert_triggered and alert_key in self.active_alerts:
                    # Resolve existing alert
                    self._resolve_alert(rule)
                
            except Exception as e:
                logger.error(f"Failed to check alert rule {rule.rule_id}: {e}")
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate alert condition"""
        
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return abs(value - threshold) < 0.001  # Float comparison
        elif condition == "!=":
            return abs(value - threshold) >= 0.001
        else:
            return False
    
    def _trigger_alert(self, rule: AlertRule, current_value: float):
        """Trigger new alert"""
        
        alert_key = f"{rule.rule_id}_{rule.metric_name}"
        
        alert_data = {
            'rule_id': rule.rule_id,
            'rule_name': rule.name,
            'metric_name': rule.metric_name,
            'current_value': current_value,
            'threshold': rule.threshold,
            'condition': rule.condition,
            'severity': rule.severity,
            'triggered_at': datetime.now().isoformat(),
            'notification_channels': rule.notification_channels
        }
        
        self.active_alerts[alert_key] = alert_data
        self.alert_history.append(alert_data)
        
        # Send notifications
        for channel in rule.notification_channels:
            self._send_notification(channel, alert_data)
        
        logger.warning(f"Alert triggered: {rule.name} - {rule.metric_name} = {current_value}")
    
    def _resolve_alert(self, rule: AlertRule):
        """Resolve existing alert"""
        
        alert_key = f"{rule.rule_id}_{rule.metric_name}"
        
        if alert_key in self.active_alerts:
            alert_data = self.active_alerts[alert_key]
            alert_data['resolved_at'] = datetime.now().isoformat()
            
            del self.active_alerts[alert_key]
            
            logger.info(f"Alert resolved: {rule.name}")
    
    def _send_notification(self, channel: str, alert_data: Dict[str, Any]):
        """Send alert notification"""
        
        # In production, integrate with actual notification services
        logger.info(f"Sending alert notification to {channel}: {alert_data['rule_name']}")

class AnalyticsDashboardService:
    """Main analytics dashboard service"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.dashboard_manager = DashboardManager(self.metrics_collector)
        self.alert_manager = AlertManager(self.metrics_collector)
        
        # Service status
        self.is_running = False
    
    async def start_service(self):
        """Start analytics dashboard service"""
        
        if self.is_running:
            return
        
        # Start metrics collection
        self.metrics_collector.start_collection()
        
        # Start alert monitoring
        self.alert_manager.start_alert_monitoring()
        
        # Initialize sample data
        await self._generate_sample_data()
        
        self.is_running = True
        logger.info("Analytics dashboard service started")
    
    async def stop_service(self):
        """Stop analytics dashboard service"""
        
        if not self.is_running:
            return
        
        # Stop collection and monitoring
        self.metrics_collector.stop_collection()
        self.alert_manager.stop_alert_monitoring()
        
        self.is_running = False
        logger.info("Analytics dashboard service stopped")
    
    async def _generate_sample_data(self):
        """Generate sample metrics data for demo"""
        
        # Generate sample booking metrics
        for i in range(100):
            self.metrics_collector.record_metric(
                "daily_revenue", 
                np.random.normal(50000, 10000), 
                MetricType.GAUGE,
                "USD"
            )
            
            self.metrics_collector.record_metric(
                "booking_count",
                np.random.poisson(200),
                MetricType.COUNTER
            )
            
            self.metrics_collector.record_metric(
                "active_users",
                np.random.poisson(500),
                MetricType.GAUGE
            )
            
            self.metrics_collector.record_metric(
                "avg_occupancy",
                np.random.uniform(60, 95),
                MetricType.GAUGE,
                "percent"
            )
            
            self.metrics_collector.record_metric(
                "response_time",
                np.random.lognormal(3, 0.5),
                MetricType.GAUGE,
                "ms"
            )
            
            # Simulate some time passing
            await asyncio.sleep(0.01)
    
    async def get_dashboard(self, dashboard_id: str, user_permissions: List[str]) -> Dict[str, Any]:
        """Get dashboard data"""
        return await self.dashboard_manager.get_dashboard_data(dashboard_id, user_permissions)
    
    def get_available_dashboards(self, user_permissions: List[str]) -> List[Dict[str, Any]]:
        """Get available dashboards for user"""
        return self.dashboard_manager.get_available_dashboards(user_permissions)
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics"""
        return self.metrics_collector.get_real_time_metrics()
    
    def record_business_metric(self, name: str, value: float, unit: str = "", 
                             tags: Dict[str, str] = None):
        """Record business metric"""
        self.metrics_collector.record_metric(name, value, MetricType.GAUGE, unit, tags)
    
    def create_alert(self, name: str, metric_name: str, condition: str, 
                    threshold: float, severity: str = "medium") -> str:
        """Create analytics alert"""
        
        rule_id = secrets.token_hex(8)
        
        self.alert_manager.create_alert_rule(
            rule_id, name, metric_name, condition, threshold, 5,
            severity, ["dashboard", "email"]
        )
        
        return rule_id
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        return list(self.alert_manager.active_alerts.values())

# Global analytics service
analytics_service = AnalyticsDashboardService()

# Utility functions
async def start_analytics_service():
    """Start analytics dashboard service"""
    await analytics_service.start_service()

async def stop_analytics_service():
    """Stop analytics dashboard service"""
    await analytics_service.stop_service()

async def get_executive_dashboard(user_permissions: List[str]) -> Dict[str, Any]:
    """Get executive dashboard"""
    return await analytics_service.get_dashboard("executive", user_permissions)

async def get_operational_dashboard(user_permissions: List[str]) -> Dict[str, Any]:
    """Get operational dashboard"""
    return await analytics_service.get_dashboard("operational", user_permissions)

def record_booking_metric(revenue: float, booking_count: int):
    """Record booking metrics"""
    analytics_service.record_business_metric("daily_revenue", revenue, "USD")
    analytics_service.record_business_metric("booking_count", booking_count)

def record_user_activity(active_users: int, new_users: int):
    """Record user activity metrics"""
    analytics_service.record_business_metric("active_users", active_users)
    analytics_service.record_business_metric("new_users", new_users)

def record_system_performance(response_time: float, error_rate: float):
    """Record system performance metrics"""
    analytics_service.record_business_metric("response_time", response_time, "ms")
    analytics_service.record_business_metric("error_rate", error_rate, "percent")