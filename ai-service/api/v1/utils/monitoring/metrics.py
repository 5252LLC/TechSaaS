"""
Metrics Collection for TechSaaS Monitoring

This module provides functionality for collecting, storing, and retrieving
metrics about API performance, security events, and system health.
"""

import time
import threading
import json
import os
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque
import statistics

from api.v1.utils.logging import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Metric types
METRIC_TYPE_REQUEST = "request"
METRIC_TYPE_ERROR = "error"
METRIC_TYPE_AUTH = "auth"
METRIC_TYPE_SYSTEM = "system"

# Time windows for metrics (in seconds)
TIME_WINDOW_1MIN = 60
TIME_WINDOW_5MIN = 300
TIME_WINDOW_15MIN = 900
TIME_WINDOW_1HOUR = 3600
TIME_WINDOW_1DAY = 86400

@dataclass
class Metric:
    """Base class for metrics."""
    type: str = ""
    name: str = ""
    value: Union[float, int, str] = 0.0
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Metric':
        """Create metric from dictionary."""
        return cls(**data)

@dataclass
class RequestMetric(Metric):
    """Metric for API requests."""
    endpoint: str = ""
    method: str = ""
    status_code: int = 200
    response_time: float = 0.0
    client_ip: str = ""
    user_id: str = ""
    type: str = METRIC_TYPE_REQUEST

@dataclass
class ErrorMetric(Metric):
    """Metric for errors."""
    error_type: str = ""
    message: str = ""
    endpoint: str = ""
    method: str = ""
    client_ip: str = ""
    user_id: str = ""
    type: str = METRIC_TYPE_ERROR

@dataclass
class AuthMetric(Metric):
    """Metric for authentication events."""
    auth_type: str = ""
    success: bool = True
    user_id: str = ""
    client_ip: str = ""
    type: str = METRIC_TYPE_AUTH
    
@dataclass
class SystemMetric(Metric):
    """Metric for system health."""
    component: str = ""
    host: str = ""
    type: str = METRIC_TYPE_SYSTEM

class MetricsManager:
    """Manager for metrics collection and retrieval."""
    
    def __init__(self):
        """Initialize metrics manager."""
        self._metrics = defaultdict(lambda: deque(maxlen=10000))  # Type -> deque of metrics
        self._aggregated_metrics = defaultdict(dict)  # Type -> Name -> Value
        self._lock = threading.RLock()
        self._last_aggregation = 0
        self._aggregation_interval = 10  # seconds
        self._retention_time = 24 * 60 * 60  # 24 hours in seconds
        self._metric_hooks = []  # Callbacks for new metrics
        self._storage_path = None
        self._persist_interval = 300  # 5 minutes
        self._last_persist = 0
        self._initialized = False
    
    def initialize(self, storage_path: Optional[str] = None, retention_time: int = 86400, 
                 persist_interval: int = 300) -> None:
        """
        Initialize the metrics manager.
        
        Args:
            storage_path: Directory to store metrics data
            retention_time: Time in seconds to retain metrics
            persist_interval: Interval in seconds to persist metrics
        """
        self._retention_time = retention_time
        self._persist_interval = persist_interval
        
        if storage_path:
            self._storage_path = storage_path
            os.makedirs(storage_path, exist_ok=True)
            
            # Load existing metrics
            self._load_metrics()
        
        self._initialized = True
        logger.info(f"Metrics manager initialized with storage_path={storage_path}, "
                   f"retention_time={retention_time}s, persist_interval={persist_interval}s")
    
    def add_metric(self, metric: Metric) -> None:
        """
        Add a metric to the collection.
        
        Args:
            metric: Metric to add
        """
        with self._lock:
            self._metrics[metric.type].append(metric)
            
            # Trigger metric hooks
            for hook in self._metric_hooks:
                try:
                    hook(metric)
                except Exception as e:
                    logger.error(f"Error in metric hook: {e}", exc_info=True)
            
            # Check if we need to aggregate
            now = time.time()
            if now - self._last_aggregation > self._aggregation_interval:
                self._aggregate_metrics()
                self._last_aggregation = now
            
            # Check if we need to persist
            if self._storage_path and now - self._last_persist > self._persist_interval:
                self._persist_metrics()
                self._last_persist = now
    
    def register_metric_hook(self, hook: Callable[[Metric], None]) -> None:
        """
        Register a hook to be called when a new metric is added.
        
        Args:
            hook: Function to call with the new metric
        """
        self._metric_hooks.append(hook)
    
    def get_metrics(self, metric_type: Optional[str] = None, 
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None,
                   limit: int = 1000,
                   filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get metrics matching the specified criteria.
        
        Args:
            metric_type: Type of metrics to retrieve
            start_time: Start time as timestamp
            end_time: End time as timestamp
            limit: Maximum number of metrics to return
            filters: Additional filters to apply
            
        Returns:
            List of metrics as dictionaries
        """
        with self._lock:
            # Get all metrics if type not specified
            if metric_type is None:
                all_metrics = []
                for metrics in self._metrics.values():
                    all_metrics.extend(metrics)
            else:
                all_metrics = list(self._metrics.get(metric_type, []))
            
            # Apply time filters
            if start_time is not None:
                all_metrics = [m for m in all_metrics if m.timestamp >= start_time]
            if end_time is not None:
                all_metrics = [m for m in all_metrics if m.timestamp <= end_time]
            
            # Apply additional filters
            if filters:
                filtered_metrics = []
                for metric in all_metrics:
                    match = True
                    for key, value in filters.items():
                        if not hasattr(metric, key) or getattr(metric, key) != value:
                            match = False
                            break
                    if match:
                        filtered_metrics.append(metric)
                all_metrics = filtered_metrics
            
            # Sort by timestamp descending
            all_metrics.sort(key=lambda m: m.timestamp, reverse=True)
            
            # Apply limit
            all_metrics = all_metrics[:limit]
            
            # Convert to dictionaries
            return [m.to_dict() for m in all_metrics]
    
    def get_aggregated_metrics(self, metric_type: Optional[str] = None, 
                              window: int = TIME_WINDOW_5MIN) -> Dict[str, Any]:
        """
        Get aggregated metrics for a specific type and time window.
        
        Args:
            metric_type: Type of metrics to retrieve
            window: Time window in seconds
            
        Returns:
            Dictionary of aggregated metrics
        """
        # Force aggregation to get latest data
        with self._lock:
            self._aggregate_metrics()
            
            if metric_type:
                return self._aggregated_metrics.get(metric_type, {}).copy()
            else:
                result = {}
                for k, v in self._aggregated_metrics.items():
                    result[k] = v.copy()
                return result
    
    def _aggregate_metrics(self) -> None:
        """Aggregate metrics for different time windows."""
        now = time.time()
        windows = [
            TIME_WINDOW_1MIN,
            TIME_WINDOW_5MIN,
            TIME_WINDOW_15MIN,
            TIME_WINDOW_1HOUR,
            TIME_WINDOW_1DAY
        ]
        
        with self._lock:
            # Clear previous aggregations
            self._aggregated_metrics = defaultdict(dict)
            
            # Process each metric type
            for metric_type, metrics in self._metrics.items():
                # Skip if no metrics
                if not metrics:
                    continue
                
                # Group metrics by name
                metrics_by_name = defaultdict(list)
                for metric in metrics:
                    # Skip old metrics
                    if now - metric.timestamp > self._retention_time:
                        continue
                    
                    metrics_by_name[metric.name].append(metric)
                
                # Aggregate for each name and window
                for name, name_metrics in metrics_by_name.items():
                    for window in windows:
                        window_metrics = [m for m in name_metrics if now - m.timestamp <= window]
                        
                        if not window_metrics:
                            continue
                        
                        # Get values for numeric metrics
                        values = []
                        for m in window_metrics:
                            if isinstance(m.value, (int, float)):
                                values.append(m.value)
                        
                        # Skip if no numeric values
                        if not values:
                            continue
                        
                        # Calculate aggregations
                        count = len(window_metrics)
                        agg_key = f"{name}_{window}s"
                        self._aggregated_metrics[metric_type][f"{agg_key}_count"] = count
                        
                        if values:
                            self._aggregated_metrics[metric_type][f"{agg_key}_avg"] = statistics.mean(values)
                            self._aggregated_metrics[metric_type][f"{agg_key}_min"] = min(values)
                            self._aggregated_metrics[metric_type][f"{agg_key}_max"] = max(values)
                            
                            if len(values) > 1:
                                self._aggregated_metrics[metric_type][f"{agg_key}_stddev"] = statistics.stdev(values)
                            
                        # Special handling for specific metric types
                        if metric_type == METRIC_TYPE_REQUEST:
                            # Calculate error rate
                            error_count = sum(1 for m in window_metrics 
                                           if hasattr(m, 'status_code') and m.status_code >= 400)
                            if count > 0:
                                error_rate = error_count / count
                                self._aggregated_metrics[metric_type][f"{agg_key}_error_rate"] = error_rate
                                
                            # Calculate response time percentiles for request metrics
                            resp_times = [m.response_time for m in window_metrics 
                                       if hasattr(m, 'response_time')]
                            if resp_times:
                                resp_times.sort()
                                self._aggregated_metrics[metric_type][f"{agg_key}_p50"] = self._percentile(resp_times, 50)
                                self._aggregated_metrics[metric_type][f"{agg_key}_p90"] = self._percentile(resp_times, 90)
                                self._aggregated_metrics[metric_type][f"{agg_key}_p95"] = self._percentile(resp_times, 95)
                                self._aggregated_metrics[metric_type][f"{agg_key}_p99"] = self._percentile(resp_times, 99)
                        
                        elif metric_type == METRIC_TYPE_AUTH:
                            # Calculate auth success rate
                            success_count = sum(1 for m in window_metrics 
                                             if hasattr(m, 'success') and m.success)
                            if count > 0:
                                success_rate = success_count / count
                                self._aggregated_metrics[metric_type][f"{agg_key}_success_rate"] = success_rate
    
    @staticmethod
    def _percentile(values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        k = (len(values) - 1) * percentile / 100
        f = int(k)
        c = int(k) + 1 if k > f else f
        
        if f >= len(values):
            return float(values[-1])
        elif c >= len(values):
            return float(values[-1])
        else:
            d0 = values[f] * (c - k)
            d1 = values[c] * (k - f)
            return d0 + d1
    
    def _clean_old_metrics(self) -> None:
        """Remove metrics older than retention time."""
        with self._lock:
            now = time.time()
            for metric_type in self._metrics:
                self._metrics[metric_type] = deque(
                    [m for m in self._metrics[metric_type] if now - m.timestamp <= self._retention_time],
                    maxlen=self._metrics[metric_type].maxlen
                )
    
    def _persist_metrics(self) -> None:
        """Persist metrics to disk."""
        if not self._storage_path:
            return
        
        with self._lock:
            # Clean old metrics first
            self._clean_old_metrics()
            
            # Create timestamp-based filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self._storage_path, f"metrics_{timestamp}.json")
            
            try:
                # Convert metrics to dictionaries
                data = {}
                for metric_type, metrics in self._metrics.items():
                    data[metric_type] = [m.to_dict() for m in metrics]
                
                # Write to file
                with open(filename, 'w') as f:
                    json.dump(data, f)
                
                logger.info(f"Persisted {sum(len(metrics) for metrics in self._metrics.values())} "
                           f"metrics to {filename}")
                
                # Clean up old files
                self._cleanup_old_files()
            except Exception as e:
                logger.error(f"Error persisting metrics: {e}", exc_info=True)
    
    def _load_metrics(self) -> None:
        """Load metrics from disk."""
        if not self._storage_path or not os.path.exists(self._storage_path):
            return
        
        with self._lock:
            # Find the most recent metrics file
            files = [f for f in os.listdir(self._storage_path) if f.startswith("metrics_") and f.endswith(".json")]
            if not files:
                return
            
            # Sort by timestamp (newest first)
            files.sort(reverse=True)
            latest_file = os.path.join(self._storage_path, files[0])
            
            try:
                # Read file
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                
                # Load metrics
                for metric_type, metrics_data in data.items():
                    for metric_data in metrics_data:
                        if metric_type == METRIC_TYPE_REQUEST:
                            metric = RequestMetric.from_dict(metric_data)
                        elif metric_type == METRIC_TYPE_ERROR:
                            metric = ErrorMetric.from_dict(metric_data)
                        elif metric_type == METRIC_TYPE_AUTH:
                            metric = AuthMetric.from_dict(metric_data)
                        elif metric_type == METRIC_TYPE_SYSTEM:
                            metric = SystemMetric.from_dict(metric_data)
                        else:
                            metric = Metric.from_dict(metric_data)
                        
                        self._metrics[metric_type].append(metric)
                
                logger.info(f"Loaded {sum(len(metrics) for metrics in self._metrics.values())} "
                           f"metrics from {latest_file}")
            except Exception as e:
                logger.error(f"Error loading metrics: {e}", exc_info=True)
    
    def _cleanup_old_files(self) -> None:
        """Clean up old metrics files."""
        if not self._storage_path:
            return
        
        try:
            files = [f for f in os.listdir(self._storage_path) if f.startswith("metrics_") and f.endswith(".json")]
            if len(files) <= 10:  # Keep at most 10 files
                return
            
            # Sort by timestamp (oldest first)
            files.sort()
            
            # Remove oldest files
            for file in files[:-10]:
                os.remove(os.path.join(self._storage_path, file))
                logger.info(f"Removed old metrics file: {file}")
        except Exception as e:
            logger.error(f"Error cleaning up old metrics files: {e}", exc_info=True)

# Global instance
_metrics_manager = MetricsManager()

def initialize_metrics(storage_path: Optional[str] = None, retention_time: int = 86400, 
                     persist_interval: int = 300) -> None:
    """
    Initialize the metrics system.
    
    Args:
        storage_path: Directory to store metrics data
        retention_time: Time in seconds to retain metrics
        persist_interval: Interval in seconds to persist metrics
    """
    _metrics_manager.initialize(storage_path, retention_time, persist_interval)

def record_request_metric(name: str, endpoint: str, method: str, status_code: int, 
                        response_time: float, client_ip: str = "", user_id: str = "",
                        tags: Optional[Dict[str, str]] = None) -> Metric:
    """
    Record a request metric.
    
    Args:
        name: Metric name
        endpoint: API endpoint
        method: HTTP method
        status_code: Response status code
        response_time: Response time in seconds
        client_ip: Client IP address
        user_id: User ID
        tags: Additional tags
    """
    metric = RequestMetric(
        name=name,
        value=response_time,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time=response_time,
        client_ip=client_ip,
        user_id=user_id
    )
    
    if tags:
        metric.tags.update(tags)
    
    _metrics_manager.add_metric(metric)
    return metric

def record_error_metric(name: str, error_type: str, message: str, endpoint: str = "", 
                      method: str = "", client_ip: str = "", user_id: str = "",
                      tags: Optional[Dict[str, str]] = None) -> Metric:
    """
    Record an error metric.
    
    Args:
        name: Metric name
        error_type: Type of error
        message: Error message
        endpoint: API endpoint
        method: HTTP method
        client_ip: Client IP address
        user_id: User ID
        tags: Additional tags
    """
    metric = ErrorMetric(
        name=name,
        value=1.0,  # Count of errors
        error_type=error_type,
        message=message,
        endpoint=endpoint,
        method=method,
        client_ip=client_ip,
        user_id=user_id
    )
    
    if tags:
        metric.tags.update(tags)
    
    _metrics_manager.add_metric(metric)
    return metric

def record_auth_metric(name: str, auth_type: str, success: bool, user_id: str = "",
                     client_ip: str = "", tags: Optional[Dict[str, str]] = None) -> Metric:
    """
    Record an authentication metric.
    
    Args:
        name: Metric name
        auth_type: Type of authentication
        success: Whether authentication was successful
        user_id: User ID
        client_ip: Client IP address
        tags: Additional tags
    """
    metric = AuthMetric(
        name=name,
        value=1.0 if success else 0.0,  # Success=1, Failure=0
        auth_type=auth_type,
        success=success,
        user_id=user_id,
        client_ip=client_ip
    )
    
    if tags:
        metric.tags.update(tags)
    
    _metrics_manager.add_metric(metric)
    return metric

def record_system_metric(name: str, value: Union[float, int], component: str = "",
                      host: str = "", tags: Optional[Dict[str, str]] = None) -> Metric:
    """
    Record a system metric.
    
    Args:
        name: Metric name
        value: Metric value
        component: System component
        host: Host name
        tags: Additional tags
    """
    metric = SystemMetric(
        name=name,
        value=value,
        component=component,
        host=host
    )
    
    if tags:
        metric.tags.update(tags)
    
    _metrics_manager.add_metric(metric)
    return metric

def get_metric_summary(metric_type: Optional[str] = None, 
                     window: int = TIME_WINDOW_5MIN) -> Dict[str, Any]:
    """
    Get a summary of metrics for a specific type and time window.
    
    Args:
        metric_type: Type of metrics to retrieve
        window: Time window in seconds
            
    Returns:
        Dictionary of aggregated metrics
    """
    return _metrics_manager.get_aggregated_metrics(metric_type, window)

def register_metric_hook(hook: Callable[[Metric], None]) -> None:
    """
    Register a hook to be called when a new metric is added.
    
    Args:
        hook: Function to call with the new metric
    """
    _metrics_manager.register_metric_hook(hook)

def get_metrics(metric_type: Optional[str] = None, 
               start_time: Optional[float] = None,
               end_time: Optional[float] = None,
               limit: int = 1000,
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get metrics matching the specified criteria.
    
    Args:
        metric_type: Type of metrics to retrieve
        start_time: Start time as timestamp
        end_time: End time as timestamp
        limit: Maximum number of metrics to return
        filters: Additional filters to apply
            
    Returns:
        List of metrics as dictionaries
    """
    return _metrics_manager.get_metrics(metric_type, start_time, end_time, limit, filters)
