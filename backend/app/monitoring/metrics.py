"""
Application Metrics and Monitoring
"""

import time
from functools import wraps
from typing import Callable, Dict, Any
from datetime import datetime
import structlog

logger = structlog.get_logger()


class MetricsCollector:
    """Collect application metrics"""
    
    def __init__(self):
        self.metrics = {
            "document_uploads": 0,
            "document_extractions": 0,
            "tax_computations": 0,
            "form_generations": 0,
            "operator_reviews": 0,
            "chat_messages": 0,
            "api_requests": 0,
            "errors": 0
        }
        
        self.timing_metrics = {}
        self.error_counts = {}
    
    def increment_counter(self, metric_name: str, value: int = 1):
        """Increment a counter metric"""
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
        else:
            self.metrics[metric_name] = value
        
        logger.info("Metric incremented", metric=metric_name, value=value)
    
    def record_timing(self, operation: str, duration_ms: float):
        """Record operation timing"""
        if operation not in self.timing_metrics:
            self.timing_metrics[operation] = []
        
        self.timing_metrics[operation].append(duration_ms)
        
        # Keep only last 1000 measurements
        if len(self.timing_metrics[operation]) > 1000:
            self.timing_metrics[operation] = self.timing_metrics[operation][-1000:]
        
        logger.info("Timing recorded", operation=operation, duration_ms=duration_ms)
    
    def record_error(self, error_type: str, error_message: str):
        """Record error occurrence"""
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        
        self.error_counts[error_type] += 1
        self.metrics["errors"] += 1
        
        logger.error("Error recorded", 
                    error_type=error_type,
                    error_message=error_message,
                    count=self.error_counts[error_type])
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        timing_stats = {}
        
        for operation, timings in self.timing_metrics.items():
            if timings:
                timing_stats[operation] = {
                    "count": len(timings),
                    "avg_ms": sum(timings) / len(timings),
                    "min_ms": min(timings),
                    "max_ms": max(timings),
                    "p95_ms": sorted(timings)[int(len(timings) * 0.95)] if len(timings) > 1 else timings[0]
                }
        
        return {
            "counters": self.metrics,
            "timing_stats": timing_stats,
            "error_counts": self.error_counts,
            "collected_at": datetime.utcnow().isoformat()
        }


# Global metrics collector
metrics_collector = MetricsCollector()


def track_timing(operation_name: str):
    """Decorator to track operation timing"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.record_timing(operation_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.record_timing(f"{operation_name}_failed", duration_ms)
                metrics_collector.record_error(type(e).__name__, str(e))
                raise
        return wrapper
    return decorator


def track_counter(metric_name: str):
    """Decorator to track counter metrics"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                metrics_collector.increment_counter(metric_name)
                return result
            except Exception as e:
                metrics_collector.increment_counter(f"{metric_name}_failed")
                raise
        return wrapper
    return decorator
