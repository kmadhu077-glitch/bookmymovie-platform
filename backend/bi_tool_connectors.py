"""
Business Intelligence Tool Connectors
Integration with Tableau, Power BI, Looker, and other BI platforms
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os
from enum import Enum
import base64
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlencode

logger = logging.getLogger(__name__)

class BIPlatform(Enum):
    """Supported BI platforms"""
    TABLEAU = "tableau"
    POWER_BI = "power_bi"
    LOOKER = "looker"
    GOOGLE_ANALYTICS = "google_analytics"
    METABASE = "metabase"
    GRAFANA = "grafana"

class DataSourceType(Enum):
    """Types of data sources"""
    SQL_DATABASE = "sql_database"
    REST_API = "rest_api"
    CSV_FILE = "csv_file"
    JSON_FILE = "json_file"
    REAL_TIME_STREAM = "real_time_stream"

@dataclass
class DataSource:
    """Data source configuration"""
    name: str
    source_type: DataSourceType
    connection_string: str = None
    api_endpoint: str = None
    file_path: str = None
    credentials: Dict[str, Any] = None
    refresh_schedule: str = None
    metadata: Dict[str, Any] = None

@dataclass
class Dashboard:
    """BI Dashboard structure"""
    id: str
    name: str
    description: str
    platform: BIPlatform
    url: str
    data_sources: List[DataSource]
    created_at: datetime = None
    updated_at: datetime = None
    permissions: Dict[str, List[str]] = None

@dataclass
class Report:
    """BI Report structure"""
    id: str
    name: str
    dashboard_id: str
    platform: BIPlatform
    report_url: str
    schedule: str = None
    format: str = "pdf"
    recipients: List[str] = None
    parameters: Dict[str, Any] = None

class TableauService:
    """Tableau Server/Cloud integration"""
    
    def __init__(self):
        self.server_url = os.getenv('TABLEAU_SERVER_URL')
        self.username = os.getenv('TABLEAU_USERNAME')
        self.password = os.getenv('TABLEAU_PASSWORD')
        self.site_id = os.getenv('TABLEAU_SITE_ID', 'default')
        self.api_version = '3.19'
        self.auth_token = None
        self.site_id_actual = None
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.auth_token:
            await self._sign_out()
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with Tableau Server"""
        try:
            auth_url = f"{self.server_url}/api/{self.api_version}/auth/signin"
            
            credentials = {
                'credentials': {
                    'name': self.username,
                    'password': self.password,
                    'site': {
                        'contentUrl': self.site_id
                    }
                }
            }
            
            async with self.session.post(auth_url, json=credentials) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    credentials_info = auth_data.get('credentials', {})
                    self.auth_token = credentials_info.get('token')
                    self.site_id_actual = credentials_info.get('site', {}).get('id')
                    
                    # Set auth header for future requests
                    self.session.headers.update({
                        'X-Tableau-Auth': self.auth_token
                    })
                else:
                    logger.error(f"Tableau authentication failed: {response.status}")
        
        except Exception as e:
            logger.error(f"Tableau authentication error: {e}")
    
    async def _sign_out(self):
        """Sign out from Tableau Server"""
        try:
            signout_url = f"{self.server_url}/api/{self.api_version}/auth/signout"
            await self.session.post(signout_url)
        except Exception as e:
            logger.error(f"Tableau signout error: {e}")
    
    async def create_data_source(self, data_source: DataSource) -> Dict[str, Any]:
        """Create/update data source in Tableau"""
        try:
            url = f"{self.server_url}/api/{self.api_version}/sites/{self.site_id_actual}/datasources"
            
            # This is a simplified example - actual implementation would vary based on data source type
            datasource_payload = {
                'datasource': {
                    'name': data_source.name,
                    'contentUrl': data_source.name.lower().replace(' ', '_'),
                    'connectionCredentials': data_source.credentials or {}
                }
            }
            
            async with self.session.post(url, json=datasource_payload) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create Tableau data source: {response.status} - {error_text}")
                    return {'error': f"Failed to create data source: {response.status}"}
        
        except Exception as e:
            logger.error(f"Tableau data source creation error: {e}")
            return {'error': str(e)}
    
    async def publish_workbook(self, workbook_path: str, project_id: str = None) -> Dict[str, Any]:
        """Publish workbook to Tableau Server"""
        try:
            url = f"{self.server_url}/api/{self.api_version}/sites/{self.site_id_actual}/workbooks"
            
            # This would involve file upload - simplified for example
            workbook_data = {
                'workbook': {
                    'name': os.path.basename(workbook_path).replace('.twbx', ''),
                    'showTabs': True
                }
            }
            
            if project_id:
                workbook_data['workbook']['project'] = {'id': project_id}
            
            # In actual implementation, you would use multipart form data to upload the file
            async with self.session.post(url, json=workbook_data) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to publish workbook: {response.status} - {error_text}")
                    return {'error': f"Failed to publish workbook: {response.status}"}
        
        except Exception as e:
            logger.error(f"Workbook publish error: {e}")
            return {'error': str(e)}
    
    async def get_dashboards(self) -> List[Dict[str, Any]]:
        """Get list of dashboards from Tableau Server"""
        try:
            url = f"{self.server_url}/api/{self.api_version}/sites/{self.site_id_actual}/views"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('views', {}).get('view', [])
                else:
                    logger.error(f"Failed to get Tableau dashboards: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Failed to get Tableau dashboards: {e}")
            return []
    
    async def refresh_data_source(self, datasource_id: str) -> Dict[str, Any]:
        """Trigger data source refresh"""
        try:
            url = f"{self.server_url}/api/{self.api_version}/sites/{self.site_id_actual}/datasources/{datasource_id}/refresh"
            
            async with self.session.post(url) as response:
                if response.status in [200, 202]:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {'error': f"Refresh failed: {response.status}"}
        
        except Exception as e:
            logger.error(f"Data source refresh error: {e}")
            return {'error': str(e)}

class PowerBIService:
    """Microsoft Power BI integration"""
    
    def __init__(self):
        self.tenant_id = os.getenv('POWERBI_TENANT_ID')
        self.client_id = os.getenv('POWERBI_CLIENT_ID')
        self.client_secret = os.getenv('POWERBI_CLIENT_SECRET')
        self.username = os.getenv('POWERBI_USERNAME')
        self.password = os.getenv('POWERBI_PASSWORD')
        self.access_token = None
        self.base_url = "https://api.powerbi.com/v1.0/myorg"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with Power BI using OAuth 2.0"""
        try:
            auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            
            auth_data = {
                'grant_type': 'password',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'username': self.username,
                'password': self.password,
                'scope': 'https://analysis.windows.net/powerbi/api/.default'
            }
            
            async with self.session.post(auth_url, data=auth_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data.get('access_token')
                    
                    # Set auth header for future requests
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}',
                        'Content-Type': 'application/json'
                    })
                else:
                    logger.error(f"Power BI authentication failed: {response.status}")
        
        except Exception as e:
            logger.error(f"Power BI authentication error: {e}")
    
    async def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get list of Power BI workspaces"""
        try:
            url = f"{self.base_url}/groups"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('value', [])
                else:
                    logger.error(f"Failed to get Power BI workspaces: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Failed to get Power BI workspaces: {e}")
            return []
    
    async def get_reports(self, workspace_id: str = None) -> List[Dict[str, Any]]:
        """Get list of Power BI reports"""
        try:
            if workspace_id:
                url = f"{self.base_url}/groups/{workspace_id}/reports"
            else:
                url = f"{self.base_url}/reports"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('value', [])
                else:
                    logger.error(f"Failed to get Power BI reports: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Failed to get Power BI reports: {e}")
            return []
    
    async def create_dataset(self, dataset_config: Dict[str, Any], workspace_id: str = None) -> Dict[str, Any]:
        """Create Power BI dataset"""
        try:
            if workspace_id:
                url = f"{self.base_url}/groups/{workspace_id}/datasets"
            else:
                url = f"{self.base_url}/datasets"
            
            async with self.session.post(url, json=dataset_config) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create Power BI dataset: {response.status} - {error_text}")
                    return {'error': f"Failed to create dataset: {response.status}"}
        
        except Exception as e:
            logger.error(f"Power BI dataset creation error: {e}")
            return {'error': str(e)}
    
    async def push_data_to_dataset(self, dataset_id: str, table_name: str, data: List[Dict[str, Any]], workspace_id: str = None) -> Dict[str, Any]:
        """Push data to Power BI dataset"""
        try:
            if workspace_id:
                url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}/tables/{table_name}/rows"
            else:
                url = f"{self.base_url}/datasets/{dataset_id}/tables/{table_name}/rows"
            
            payload = {'rows': data}
            
            async with self.session.post(url, json=payload) as response:
                if response.status in [200, 202]:
                    return {'success': True, 'rows_added': len(data)}
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to push data to Power BI: {response.status} - {error_text}")
                    return {'error': f"Failed to push data: {response.status}"}
        
        except Exception as e:
            logger.error(f"Power BI data push error: {e}")
            return {'error': str(e)}
    
    async def refresh_dataset(self, dataset_id: str, workspace_id: str = None) -> Dict[str, Any]:
        """Trigger dataset refresh in Power BI"""
        try:
            if workspace_id:
                url = f"{self.base_url}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
            else:
                url = f"{self.base_url}/datasets/{dataset_id}/refreshes"
            
            async with self.session.post(url) as response:
                if response.status in [200, 202]:
                    return {'success': True, 'message': 'Refresh triggered'}
                else:
                    error_text = await response.text()
                    return {'error': f"Refresh failed: {response.status}"}
        
        except Exception as e:
            logger.error(f"Power BI dataset refresh error: {e}")
            return {'error': str(e)}

class LookerService:
    """Looker integration"""
    
    def __init__(self):
        self.base_url = os.getenv('LOOKER_BASE_URL')
        self.client_id = os.getenv('LOOKER_CLIENT_ID')
        self.client_secret = os.getenv('LOOKER_CLIENT_SECRET')
        self.access_token = None
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with Looker API"""
        try:
            auth_url = f"{self.base_url}/api/4.0/login"
            
            auth_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            async with self.session.post(auth_url, json=auth_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data.get('access_token')
                    
                    # Set auth header for future requests
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}',
                        'Content-Type': 'application/json'
                    })
                else:
                    logger.error(f"Looker authentication failed: {response.status}")
        
        except Exception as e:
            logger.error(f"Looker authentication error: {e}")
    
    async def get_dashboards(self) -> List[Dict[str, Any]]:
        """Get list of Looker dashboards"""
        try:
            url = f"{self.base_url}/api/4.0/dashboards"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get Looker dashboards: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Failed to get Looker dashboards: {e}")
            return []
    
    async def run_look(self, look_id: str, result_format: str = 'json') -> Dict[str, Any]:
        """Run a Looker Look and get results"""
        try:
            url = f"{self.base_url}/api/4.0/looks/{look_id}/run/{result_format}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to run Looker look: {response.status}")
                    return {}
        
        except Exception as e:
            logger.error(f"Failed to run Looker look: {e}")
            return {}

class GoogleAnalyticsService:
    """Google Analytics Reporting API integration"""
    
    def __init__(self):
        self.credentials_file = os.getenv('GOOGLE_ANALYTICS_CREDENTIALS_FILE')
        self.view_id = os.getenv('GOOGLE_ANALYTICS_VIEW_ID')
        self.access_token = None
        self.base_url = "https://analyticsreporting.googleapis.com/v4"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with Google Analytics API"""
        # This is a simplified version - would typically use service account credentials
        try:
            self.access_token = os.getenv('GOOGLE_ANALYTICS_ACCESS_TOKEN')
            
            if self.access_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                })
        
        except Exception as e:
            logger.error(f"Google Analytics authentication error: {e}")
    
    async def get_analytics_report(self, start_date: str, end_date: str, metrics: List[str], dimensions: List[str] = None) -> Dict[str, Any]:
        """Get Google Analytics report"""
        try:
            url = f"{self.base_url}/reports:batchGet"
            
            report_request = {
                'reportRequests': [{
                    'viewId': self.view_id,
                    'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                    'metrics': [{'expression': metric} for metric in metrics],
                    'dimensions': [{'name': dim} for dim in (dimensions or [])]
                }]
            }
            
            async with self.session.post(url, json=report_request) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get Google Analytics report: {response.status}")
                    return {}
        
        except Exception as e:
            logger.error(f"Failed to get Google Analytics report: {e}")
            return {}

class BIIntegrationService:
    """Unified BI integration service"""
    
    def __init__(self):
        self.tableau_service = TableauService()
        self.powerbi_service = PowerBIService()
        self.looker_service = LookerService()
        self.ga_service = GoogleAnalyticsService()
        
        # Standard data schemas for BookMyMovie platform
        self.data_schemas = {
            'bookings': {
                'table_name': 'movie_bookings',
                'columns': [
                    {'name': 'booking_id', 'type': 'string'},
                    {'name': 'user_id', 'type': 'string'},
                    {'name': 'movie_id', 'type': 'string'},
                    {'name': 'cinema_id', 'type': 'string'},
                    {'name': 'show_time', 'type': 'datetime'},
                    {'name': 'seats_booked', 'type': 'integer'},
                    {'name': 'total_amount', 'type': 'decimal'},
                    {'name': 'booking_date', 'type': 'datetime'},
                    {'name': 'payment_status', 'type': 'string'},
                    {'name': 'booking_status', 'type': 'string'}
                ]
            },
            'users': {
                'table_name': 'user_analytics',
                'columns': [
                    {'name': 'user_id', 'type': 'string'},
                    {'name': 'age_group', 'type': 'string'},
                    {'name': 'gender', 'type': 'string'},
                    {'name': 'location', 'type': 'string'},
                    {'name': 'registration_date', 'type': 'datetime'},
                    {'name': 'total_bookings', 'type': 'integer'},
                    {'name': 'total_spent', 'type': 'decimal'},
                    {'name': 'last_booking_date', 'type': 'datetime'},
                    {'name': 'preferred_genres', 'type': 'string'},
                    {'name': 'loyalty_tier', 'type': 'string'}
                ]
            },
            'movies': {
                'table_name': 'movie_performance',
                'columns': [
                    {'name': 'movie_id', 'type': 'string'},
                    {'name': 'title', 'type': 'string'},
                    {'name': 'genre', 'type': 'string'},
                    {'name': 'release_date', 'type': 'datetime'},
                    {'name': 'total_bookings', 'type': 'integer'},
                    {'name': 'total_revenue', 'type': 'decimal'},
                    {'name': 'average_rating', 'type': 'decimal'},
                    {'name': 'occupancy_rate', 'type': 'decimal'},
                    {'name': 'show_count', 'type': 'integer'},
                    {'name': 'runtime_minutes', 'type': 'integer'}
                ]
            }
        }
    
    async def setup_bi_dashboards(self, platform: BIPlatform, workspace_id: str = None) -> Dict[str, Any]:
        """Set up standard BookMyMovie dashboards in BI platform"""
        
        results = {
            'platform': platform.value,
            'dashboards_created': [],
            'data_sources_created': [],
            'errors': []
        }
        
        try:
            if platform == BIPlatform.TABLEAU:
                async with self.tableau_service as service:
                    # Create data sources
                    for schema_name, schema_config in self.data_schemas.items():
                        data_source = DataSource(
                            name=f"BookMyMovie_{schema_name}",
                            source_type=DataSourceType.SQL_DATABASE,
                            connection_string=os.getenv('DATABASE_URL'),
                            metadata=schema_config
                        )
                        
                        result = await service.create_data_source(data_source)
                        results['data_sources_created'].append(result)
            
            elif platform == BIPlatform.POWER_BI:
                async with self.powerbi_service as service:
                    # Create datasets
                    for schema_name, schema_config in self.data_schemas.items():
                        dataset_config = {
                            'name': f"BookMyMovie_{schema_name}",
                            'tables': [{
                                'name': schema_config['table_name'],
                                'columns': schema_config['columns']
                            }]
                        }
                        
                        result = await service.create_dataset(dataset_config, workspace_id)
                        results['data_sources_created'].append(result)
            
            elif platform == BIPlatform.LOOKER:
                async with self.looker_service as service:
                    dashboards = await service.get_dashboards()
                    results['existing_dashboards'] = len(dashboards)
        
        except Exception as e:
            logger.error(f"BI dashboard setup failed for {platform}: {e}")
            results['errors'].append(str(e))
        
        return results
    
    async def sync_data_to_bi_platform(self, platform: BIPlatform, data_type: str, data: List[Dict[str, Any]], workspace_id: str = None) -> Dict[str, Any]:
        """Sync BookMyMovie data to BI platform"""
        
        try:
            if platform == BIPlatform.POWER_BI and data_type in self.data_schemas:
                async with self.powerbi_service as service:
                    schema = self.data_schemas[data_type]
                    dataset_name = f"BookMyMovie_{data_type}"
                    
                    # In a real implementation, you would first find the dataset ID
                    dataset_id = "placeholder_dataset_id"
                    
                    return await service.push_data_to_dataset(
                        dataset_id=dataset_id,
                        table_name=schema['table_name'],
                        data=data,
                        workspace_id=workspace_id
                    )
            
            else:
                return {
                    'success': False,
                    'message': f"Data sync not implemented for {platform.value} with {data_type}"
                }
        
        except Exception as e:
            logger.error(f"Data sync failed for {platform}: {e}")
            return {'error': str(e)}
    
    async def generate_executive_report(self, report_type: str, date_range: Dict[str, str]) -> Dict[str, Any]:
        """Generate executive report using multiple BI platforms"""
        
        report_data = {
            'report_type': report_type,
            'generated_at': datetime.now().isoformat(),
            'date_range': date_range,
            'metrics': {},
            'insights': [],
            'visualizations': []
        }
        
        try:
            # Get data from Google Analytics
            async with self.ga_service as service:
                ga_report = await service.get_analytics_report(
                    start_date=date_range['start_date'],
                    end_date=date_range['end_date'],
                    metrics=['ga:users', 'ga:sessions', 'ga:pageviews', 'ga:bounceRate'],
                    dimensions=['ga:date', 'ga:deviceCategory']
                )
                
                if ga_report:
                    report_data['metrics']['web_analytics'] = ga_report
            
            # Add business metrics (would come from your database)
            report_data['metrics']['business_kpis'] = await self._get_business_kpis(date_range)
            
            # Generate insights based on data
            report_data['insights'] = await self._generate_insights(report_data['metrics'])
            
            # Create visualizations (URLs to BI dashboards)
            report_data['visualizations'] = await self._get_dashboard_urls()
        
        except Exception as e:
            logger.error(f"Executive report generation failed: {e}")
            report_data['error'] = str(e)
        
        return report_data
    
    async def _get_business_kpis(self, date_range: Dict[str, str]) -> Dict[str, Any]:
        """Get business KPIs from database (placeholder implementation)"""
        # This would query your actual database
        return {
            'total_bookings': 1250,
            'total_revenue': 45600.00,
            'average_booking_value': 36.48,
            'new_users': 89,
            'returning_users': 456,
            'top_movies': [
                {'title': 'Movie A', 'bookings': 234, 'revenue': 8424.00},
                {'title': 'Movie B', 'bookings': 187, 'revenue': 6732.00},
                {'title': 'Movie C', 'bookings': 156, 'revenue': 5616.00}
            ],
            'cinema_performance': [
                {'cinema': 'Cinema Downtown', 'occupancy': 78.5, 'revenue': 15620.00},
                {'cinema': 'Cinema Mall', 'occupancy': 65.2, 'revenue': 12340.00},
                {'cinema': 'Cinema Plaza', 'occupancy': 58.7, 'revenue': 9870.00}
            ]
        }
    
    async def _generate_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate business insights from metrics"""
        insights = []
        
        business_kpis = metrics.get('business_kpis', {})
        
        # Revenue insights
        total_revenue = business_kpis.get('total_revenue', 0)
        if total_revenue > 40000:
            insights.append("Strong revenue performance this period, exceeding $40k target")
        
        # Booking insights
        avg_booking_value = business_kpis.get('average_booking_value', 0)
        if avg_booking_value > 35:
            insights.append("Above-average booking value indicates successful premium offerings")
        
        # Movie performance insights
        top_movies = business_kpis.get('top_movies', [])
        if top_movies:
            top_movie = top_movies[0]
            insights.append(f"'{top_movie['title']}' is the top performer with {top_movie['bookings']} bookings")
        
        # Cinema performance insights
        cinema_performance = business_kpis.get('cinema_performance', [])
        if cinema_performance:
            best_cinema = max(cinema_performance, key=lambda x: x.get('occupancy', 0))
            insights.append(f"{best_cinema['cinema']} leads in occupancy rate at {best_cinema['occupancy']}%")
        
        return insights
    
    async def _get_dashboard_urls(self) -> List[Dict[str, str]]:
        """Get URLs to various BI dashboards"""
        return [
            {
                'name': 'Executive Summary',
                'platform': 'tableau',
                'url': f"{os.getenv('TABLEAU_SERVER_URL')}/views/BookMyMovieExecutive/Dashboard"
            },
            {
                'name': 'Revenue Analytics',
                'platform': 'power_bi',
                'url': 'https://app.powerbi.com/groups/workspace-id/dashboards/revenue-dashboard-id'
            },
            {
                'name': 'Customer Insights',
                'platform': 'looker',
                'url': f"{os.getenv('LOOKER_BASE_URL')}/dashboards/customer-insights"
            },
            {
                'name': 'Web Analytics',
                'platform': 'google_analytics',
                'url': f"https://analytics.google.com/analytics/web/#/report/visitors-overview/a{os.getenv('GA_ACCOUNT_ID')}w{os.getenv('GA_PROPERTY_ID')}p{os.getenv('GOOGLE_ANALYTICS_VIEW_ID')}/"
            }
        ]
    
    async def schedule_data_refresh(self, platforms: List[BIPlatform]) -> Dict[str, Any]:
        """Schedule data refresh across multiple BI platforms"""
        
        refresh_results = {}
        
        for platform in platforms:
            try:
                if platform == BIPlatform.TABLEAU:
                    async with self.tableau_service as service:
                        # Would refresh all BookMyMovie data sources
                        refresh_results[platform.value] = {'message': 'Tableau refresh scheduled'}
                
                elif platform == BIPlatform.POWER_BI:
                    async with self.powerbi_service as service:
                        # Would refresh all datasets
                        refresh_results[platform.value] = {'message': 'Power BI refresh scheduled'}
                
                else:
                    refresh_results[platform.value] = {'message': f'{platform.value} refresh not implemented'}
            
            except Exception as e:
                refresh_results[platform.value] = {'error': str(e)}
        
        return refresh_results

# Global BI integration service
bi_integration_service = BIIntegrationService()

# Utility functions for common BI operations
async def setup_complete_bi_stack():
    """Set up BI integrations across all platforms"""
    platforms = [BIPlatform.TABLEAU, BIPlatform.POWER_BI, BIPlatform.LOOKER]
    results = {}
    
    for platform in platforms:
        results[platform.value] = await bi_integration_service.setup_bi_dashboards(platform)
    
    return results

async def sync_daily_data():
    """Daily data sync to all BI platforms"""
    # This would be called by a scheduled job
    
    sync_results = {}
    
    # Sample data sync (would come from your database)
    booking_data = [
        {
            'booking_id': 'B001',
            'user_id': 'U123',
            'movie_id': 'M456',
            'total_amount': 45.50,
            'booking_date': datetime.now().isoformat()
        }
    ]
    
    # Sync to Power BI
    sync_results['power_bi'] = await bi_integration_service.sync_data_to_bi_platform(
        BIPlatform.POWER_BI,
        'bookings',
        booking_data
    )
    
    return sync_results

async def generate_weekly_executive_report():
    """Generate weekly executive report"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    date_range = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }
    
    return await bi_integration_service.generate_executive_report('weekly', date_range)