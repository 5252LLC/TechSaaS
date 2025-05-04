"""
TechSaaS Anomaly Detection Middleware

This middleware intercepts API requests and forwards relevant data to the
anomaly detection system for analysis.
"""

import time
import logging
import uuid
from datetime import datetime
from functools import wraps
from flask import request, g, current_app
import threading

from api.v1.utils.anomaly_detection import AnomalyManager
from api.v1.utils.logging_service import LoggingService

logger = logging.getLogger("techsaas.middleware.anomaly_detection")
logging_service = LoggingService()

# Initialize anomaly manager when first needed
anomaly_manager = None

def get_anomaly_manager():
    """Get or initialize the anomaly manager"""
    global anomaly_manager
    
    if anomaly_manager is None:
        from api.v1.routes.anomaly_detection import init_anomaly_manager
        init_anomaly_manager()
        
        # Get the manager instance
        from api.v1.routes.anomaly_detection import anomaly_manager as manager
        anomaly_manager = manager
    
    return anomaly_manager

def analyze_event_async(event_data):
    """Analyze an event asynchronously"""
    try:
        manager = get_anomaly_manager()
        if not manager:
            logger.error("Anomaly manager not initialized")
            return
        
        # Analyze the event
        anomalies = manager.analyze_event(event_data)
        
        # Log detected anomalies
        if anomalies:
            for anomaly in anomalies:
                logger.warning(f"Detected anomaly: {anomaly.anomaly_type.value}, "
                              f"Severity: {anomaly.severity.value}, "
                              f"ID: {anomaly.anomaly_id}")
                
                # Log to audit trail
                logging_service.log_security_event(
                    event_type="anomaly_detected",
                    severity=anomaly.severity.value,
                    user_id=anomaly.user_id,
                    description=f"Anomaly detected: {anomaly.anomaly_type.value}",
                    metadata=anomaly.to_dict()
                )
    except Exception as e:
        logger.error(f"Error analyzing event: {str(e)}")

class AnomalyDetectionMiddleware:
    """
    Middleware for anomaly detection
    
    This middleware captures API request information and sends it to the
    anomaly detection system for analysis.
    """
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with a Flask app"""
        # Register before_request handler
        app.before_request(self.before_request)
        
        # Register after_request handler
        app.after_request(self.after_request)
        
        logger.info("Initialized anomaly detection middleware")
    
    def before_request(self):
        """Process request before it's handled by a route"""
        # Store start time for performance monitoring
        g.request_start_time = time.time()
        
        # Generate a unique ID for this request
        g.request_id = str(uuid.uuid4())
    
    def after_request(self, response):
        """Process request after it's been handled by a route"""
        # Skip anomaly detection for static files
        if request.path.startswith('/static/'):
            return response
        
        # Skip anomaly detection for anomaly detection API itself
        if request.path.startswith('/api/v1/security/anomalies'):
            return response
        
        try:
            # Calculate request duration
            duration = time.time() - getattr(g, 'request_start_time', time.time())
            
            # Get relevant request data
            event_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": getattr(g, 'request_id', str(uuid.uuid4())),
                "method": request.method,
                "endpoint": request.path,
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', ''),
                "response_code": response.status_code,
                "duration": duration
            }
            
            # Add user information if available
            if hasattr(g, 'user_id'):
                event_data["user_id"] = g.user_id
            
            # Special handling for authentication events
            if request.path.endswith('/login') or request.path.endswith('/auth'):
                event_data["authentication_success"] = response.status_code == 200
            
            # Run anomaly detection in a separate thread to not block response
            threading.Thread(
                target=analyze_event_async,
                args=(event_data,),
                daemon=True
            ).start()
        except Exception as e:
            logger.error(f"Error in anomaly detection middleware: {str(e)}")
        
        return response

def monitor_for_anomalies(func):
    """
    Decorator to monitor a function for anomalies
    
    This decorator can be used on individual functions to monitor
    them for anomalies, even outside the regular request cycle.
    
    Example:
        @monitor_for_anomalies
        def process_payment(user_id, amount):
            # Process payment
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Get user_id from kwargs or g
        user_id = kwargs.get('user_id') or getattr(g, 'user_id', None)
        
        # Extract function context
        context = {
            "function": func.__name__,
            "args": [str(arg) for arg in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()}
        }
        
        try:
            # Call the original function
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            # Capture exception information
            success = False
            error = str(e)
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Prepare event data
            event_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id,
                "user_id": user_id,
                "function": func.__name__,
                "success": success,
                "duration": duration,
                "context": context
            }
            
            if not success:
                event_data["error"] = error
            
            # Run anomaly detection asynchronously
            threading.Thread(
                target=analyze_event_async,
                args=(event_data,),
                daemon=True
            ).start()
    
    return wrapper
