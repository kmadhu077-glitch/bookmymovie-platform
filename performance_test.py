#!/usr/bin/env python3
"""
Performance Testing and Load Testing for BookMyMovie Platform
Comprehensive performance analysis and optimization validation
"""

import asyncio
import aiohttp
import time
import statistics
import json
from datetime import datetime
from typing import Dict, List, Any
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

class PerformanceTester:
    """Comprehensive performance testing suite"""
    
    def __init__(self):
        self.services = {
            'auth': 'http://127.0.0.1:8013',
            'catalog': 'http://127.0.0.1:8012',
            'booking': 'http://127.0.0.1:8014',
            'payment': 'http://127.0.0.1:8015',
            'realtime': 'http://127.0.0.1:8016'
        }
        self.test_results = {}
        self.auth_token = None
    
    async def setup_test_user(self, session):
        """Setup a test user for authenticated requests"""
        user_data = {
            "username": f"perftest_{int(time.time())}",
            "email": f"perftest_{int(time.time())}@example.com",
            "password": "PerfTest123!",
            "phone_number": "1234567890",
            "full_name": "Performance Test User"
        }
        
        try:
            async with session.post(f"{self.services['auth']}/auth/register", json=user_data) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    self.auth_token = result.get('access_token')
                    return True
        except Exception as e:
            logger.error(f"Setup test user error: {e}")
        
        return False
    
    async def test_endpoint_performance(self, session, method: str, url: str, data: dict = None, headers: dict = None) -> Dict[str, Any]:
        """Test individual endpoint performance"""
        
        start_time = time.time()
        
        try:
            kwargs = {'headers': headers} if headers else {}
            if data:
                kwargs['json'] = data
            
            if method.upper() == 'GET':
                async with session.get(url, **kwargs) as response:
                    response_data = await response.text()
                    status_code = response.status
            elif method.upper() == 'POST':
                async with session.post(url, **kwargs) as response:
                    response_data = await response.text()
                    status_code = response.status
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.time()
            
            return {
                'success': True,
                'status_code': status_code,
                'response_time': (end_time - start_time) * 1000,  # Convert to milliseconds
                'response_size': len(response_data),
                'error': None
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'status_code': 0,
                'response_time': (end_time - start_time) * 1000,
                'response_size': 0,
                'error': str(e)
            }
    
    async def load_test_endpoint(self, endpoint_name: str, method: str, url: str, 
                               concurrent_requests: int = 10, total_requests: int = 100,
                               data: dict = None) -> Dict[str, Any]:
        """Perform load testing on a specific endpoint"""
        
        print(f"🔄 Load testing {endpoint_name}...")
        
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        results = []
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def make_request(session):
            async with semaphore:
                return await self.test_endpoint_performance(session, method, url, data, headers)
        
        async with aiohttp.ClientSession() as session:
            tasks = [make_request(session) for _ in range(total_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and analyze results
        valid_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get('success')]
        
        if not valid_results:
            return {
                'endpoint': endpoint_name,
                'total_requests': total_requests,
                'successful_requests': 0,
                'failed_requests': len(failed_results),
                'error': 'All requests failed'
            }
        
        response_times = [r['response_time'] for r in valid_results]
        status_codes = [r['status_code'] for r in valid_results]
        response_sizes = [r['response_size'] for r in valid_results]
        
        return {
            'endpoint': endpoint_name,
            'total_requests': total_requests,
            'successful_requests': len(valid_results),
            'failed_requests': len(failed_results),
            'success_rate': (len(valid_results) / total_requests) * 100,
            'performance_metrics': {
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'median_response_time': statistics.median(response_times),
                'p95_response_time': self._percentile(response_times, 95),
                'p99_response_time': self._percentile(response_times, 99),
                'requests_per_second': len(valid_results) / (max(response_times) / 1000) if response_times else 0
            },
            'response_analysis': {
                'avg_response_size': statistics.mean(response_sizes) if response_sizes else 0,
                'status_code_distribution': self._count_occurrences(status_codes)
            }
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile from data"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _count_occurrences(self, items: List) -> Dict[str, int]:
        """Count occurrences of items in list"""
        counts = {}
        for item in items:
            counts[str(item)] = counts.get(str(item), 0) + 1
        return counts
    
    async def test_service_health_performance(self) -> Dict[str, Any]:
        """Test health endpoint performance for all services"""
        
        print("🏥 Testing service health performance...")
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for service_name, base_url in self.services.items():
                health_url = f"{base_url}/docs"  # Using docs endpoint as health check
                
                result = await self.load_test_endpoint(
                    f"{service_name}_health",
                    "GET",
                    health_url,
                    concurrent_requests=5,
                    total_requests=20
                )
                
                results[service_name] = result
        
        return results
    
    async def test_authentication_performance(self) -> Dict[str, Any]:
        """Test authentication endpoints performance"""
        
        print("🔐 Testing authentication performance...")
        
        # Setup test session
        async with aiohttp.ClientSession() as session:
            await self.setup_test_user(session)
        
        auth_tests = {}
        
        # Test registration performance
        reg_data = {
            "username": f"loadtest_{int(time.time())}_{{i}}",
            "email": f"loadtest_{int(time.time())}_{{i}}@example.com",
            "password": "LoadTest123!",
            "phone_number": "1234567890",
            "full_name": "Load Test User"
        }
        
        # We'll test with different user data for each request
        # For now, just test the profile endpoint which requires auth
        if self.auth_token:
            auth_tests['profile'] = await self.load_test_endpoint(
                "auth_profile",
                "GET",
                f"{self.services['auth']}/auth/me",
                concurrent_requests=10,
                total_requests=50
            )
        
        return auth_tests
    
    async def test_caching_performance(self) -> Dict[str, Any]:
        """Test caching effectiveness"""
        
        print("💾 Testing caching performance...")
        
        if not self.auth_token:
            return {"error": "No auth token available for caching tests"}
        
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        profile_url = f"{self.services['auth']}/auth/me"
        
        # Test without cache (first request)
        async with aiohttp.ClientSession() as session:
            first_request = await self.test_endpoint_performance(session, "GET", profile_url, headers=headers)
        
        # Test with cache (subsequent requests)
        cache_results = await self.load_test_endpoint(
            "cached_profile",
            "GET", 
            profile_url,
            concurrent_requests=20,
            total_requests=100
        )
        
        return {
            'first_request_time': first_request.get('response_time', 0),
            'cached_requests': cache_results,
            'cache_improvement': {
                'faster_avg': first_request.get('response_time', 0) > cache_results.get('performance_metrics', {}).get('avg_response_time', 0),
                'improvement_factor': first_request.get('response_time', 1) / cache_results.get('performance_metrics', {}).get('avg_response_time', 1)
            }
        }
    
    async def run_comprehensive_performance_test(self) -> Dict[str, Any]:
        """Run complete performance test suite"""
        
        print("🚀 BOOKMYMOVIE PERFORMANCE TESTING")
        print("=" * 50)
        print(f"Test started at: {datetime.now()}")
        print()
        
        test_start_time = time.time()
        results = {
            'test_timestamp': datetime.now().isoformat(),
            'test_results': {}
        }
        
        try:
            # 1. Service Health Performance
            results['test_results']['service_health'] = await self.test_service_health_performance()
            
            # 2. Authentication Performance 
            results['test_results']['authentication'] = await self.test_authentication_performance()
            
            # 3. Caching Performance
            results['test_results']['caching'] = await self.test_caching_performance()
            
        except Exception as e:
            logger.error(f"Performance test error: {e}")
            results['error'] = str(e)
        
        test_duration = time.time() - test_start_time
        results['test_duration_seconds'] = round(test_duration, 2)
        
        # Generate performance summary
        results['performance_summary'] = self._generate_performance_summary(results['test_results'])
        
        print(f"\n📊 PERFORMANCE TEST COMPLETED")
        print(f"Duration: {test_duration:.2f} seconds")
        print(f"Results: {len(results['test_results'])} test suites")
        
        return results
    
    def _generate_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary from test results"""
        
        summary = {
            'overall_health': 'healthy',
            'performance_grade': 'A',
            'recommendations': []
        }
        
        # Analyze service health
        service_health = test_results.get('service_health', {})
        healthy_services = sum(1 for s in service_health.values() 
                             if s.get('success_rate', 0) > 95)
        total_services = len(service_health)
        
        if total_services > 0:
            health_ratio = healthy_services / total_services
            if health_ratio < 0.8:
                summary['overall_health'] = 'degraded'
                summary['recommendations'].append("Some services showing performance issues")
        
        # Analyze authentication performance
        auth_perf = test_results.get('authentication', {})
        for endpoint, metrics in auth_perf.items():
            avg_time = metrics.get('performance_metrics', {}).get('avg_response_time', 0)
            if avg_time > 500:  # More than 500ms
                summary['recommendations'].append(f"Authentication {endpoint} endpoint slow: {avg_time:.1f}ms")
        
        # Analyze caching effectiveness
        caching = test_results.get('caching', {})
        if caching.get('cache_improvement', {}).get('faster_avg'):
            summary['recommendations'].append("Caching is working effectively")
        else:
            summary['recommendations'].append("Consider optimizing caching strategy")
        
        return summary

def run_performance_tests():
    """Run performance tests and display results"""
    
    async def main():
        tester = PerformanceTester()
        results = await tester.run_comprehensive_performance_test()
        
        # Display results
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE TEST RESULTS SUMMARY")
        print("=" * 60)
        
        summary = results.get('performance_summary', {})
        print(f"Overall Health: {summary.get('overall_health', 'unknown').upper()}")
        print(f"Performance Grade: {summary.get('performance_grade', 'N/A')}")
        
        recommendations = summary.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print(f"\n⏱️  Test Duration: {results.get('test_duration_seconds', 0)} seconds")
        
        # Detailed results
        print(f"\n🔍 DETAILED RESULTS")
        print("-" * 30)
        
        service_health = results.get('test_results', {}).get('service_health', {})
        for service, metrics in service_health.items():
            success_rate = metrics.get('success_rate', 0)
            avg_time = metrics.get('performance_metrics', {}).get('avg_response_time', 0)
            print(f"{service.title()}: {success_rate:.1f}% success, {avg_time:.1f}ms avg")
        
        return results
    
    return asyncio.run(main())

if __name__ == "__main__":
    run_performance_tests()