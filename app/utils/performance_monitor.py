
import time
import psutil
import asyncio
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor system and application performance"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'network_io': psutil.net_io_counters()._asdict(),
            'disk_io': psutil.disk_io_counters()._asdict(),
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time() - self.start_time
        }
    
    async def monitor_query_performance(self, query_func, *args, **kwargs):
        """Monitor performance of database queries"""
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss
        
        try:
            result = await query_func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        memory_after = psutil.Process().memory_info().rss
        
        metrics = {
            'execution_time': end_time - start_time,
            'memory_delta': memory_after - memory_before,
            'success': success,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Query performance: {metrics}")
        return result, metrics
    
    def log_metrics(self, operation: str, duration: float, additional_data: Dict = None):
        """Log performance metrics for operations"""
        metric_data = {
            'operation': operation,
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        if additional_data:
            metric_data.update(additional_data)
        
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append(metric_data)
        
        # Keep only last 1000 metrics per operation
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]
        
        logger.info(f"Performance metric: {metric_data}")
