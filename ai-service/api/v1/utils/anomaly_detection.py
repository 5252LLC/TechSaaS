"""
TechSaaS Anomaly Detection System

This module provides capabilities to detect anomalous behavior in API usage patterns
and system interactions. It analyzes various data sources to identify potential security
threats or unusual patterns that may indicate security issues.

Key features:
- Baseline behavior pattern establishment
- Detection of unusual access patterns (time, geographic location, request frequency)
- Automatic response mechanisms for potential threats
- Integration with logging and monitoring systems
- Support for different detection algorithms
"""

import os
import json
import time
import datetime
import logging
import statistics
import ipaddress
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from enum import Enum
from collections import defaultdict, Counter
import threading
import pickle
from dataclasses import dataclass, field

# Import existing systems for integration
try:
    from api.v1.utils.logging_service import LoggingService
    LOGGING_SERVICE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    LOGGING_SERVICE_AVAILABLE = False
    # Create a simple logging service for standalone testing
    class SimpleLoggingService:
        def __init__(self):
            self.logger = logging.getLogger("techsaas.security.anomaly")
            self.logger.setLevel(logging.INFO)
            # Add console handler if no handlers are configured
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                self.logger.addHandler(handler)
        
        def log_security_event(self, event_type, severity, user_id=None, description=None, metadata=None):
            self.logger.info(f"Security Event: {event_type}, Severity: {severity}, User: {user_id}, Desc: {description}")
    
    # Use SimpleLoggingService as a fallback
    LoggingService = SimpleLoggingService

logger = logging.getLogger("techsaas.security.anomaly")

class AnomalyType(Enum):
    """Types of anomalies that can be detected"""
    ACCESS_TIME = "unusual_access_time"
    GEOGRAPHIC_LOCATION = "unusual_geographic_location"
    REQUEST_FREQUENCY = "high_request_frequency"
    REQUEST_PATTERN = "unusual_request_pattern"
    AUTHENTICATION_FAILURE = "multiple_authentication_failures"
    AUTHORIZATION_BYPASS = "potential_authorization_bypass"
    DATA_ACCESS = "unusual_data_access_pattern"
    API_USAGE = "abnormal_api_usage"
    USER_BEHAVIOR = "abnormal_user_behavior"
    CUSTOM = "custom_anomaly"

class AnomalySeverity(Enum):
    """Severity levels for detected anomalies"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ResponseAction(Enum):
    """Automated response actions for detected anomalies"""
    BLOCK_IP = "block_ip_temporarily"
    REQUIRE_MFA = "require_additional_authentication"
    RATE_LIMIT = "apply_stricter_rate_limits"
    NOTIFY_ADMIN = "notify_administrators"
    LOG_ONLY = "log_only_no_action"
    REVOKE_SESSION = "revoke_user_session"
    LOCK_ACCOUNT = "lock_user_account"
    CUSTOM_ACTION = "custom_action"

@dataclass
class AnomalyEvent:
    """Represents a detected anomaly event"""
    anomaly_id: str
    timestamp: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    api_endpoint: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    response_actions: List[ResponseAction] = field(default_factory=list)
    status: str = "new"  # new, under_review, resolved, false_positive
    review_comments: Optional[str] = None
    reviewer_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "anomaly_id": self.anomaly_id,
            "timestamp": self.timestamp,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "api_endpoint": self.api_endpoint,
            "details": self.details,
            "response_actions": [action.value for action in self.response_actions],
            "status": self.status,
            "review_comments": self.review_comments,
            "reviewer_id": self.reviewer_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnomalyEvent':
        """Create event from dictionary"""
        response_actions = [ResponseAction(action) for action in data.get("response_actions", [])]
        
        return cls(
            anomaly_id=data["anomaly_id"],
            timestamp=data["timestamp"],
            anomaly_type=AnomalyType(data["anomaly_type"]),
            severity=AnomalySeverity(data["severity"]),
            source_ip=data.get("source_ip"),
            user_id=data.get("user_id"),
            api_endpoint=data.get("api_endpoint"),
            details=data.get("details", {}),
            response_actions=response_actions,
            status=data.get("status", "new"),
            review_comments=data.get("review_comments"),
            reviewer_id=data.get("reviewer_id")
        )

class AnomalyDetector:
    """Base class for anomaly detection algorithms"""
    
    def __init__(self, name: str, anomaly_type: AnomalyType):
        """
        Initialize an anomaly detector
        
        Args:
            name: Unique name for this detector
            anomaly_type: Type of anomaly this detector identifies
        """
        self.name = name
        self.anomaly_type = anomaly_type
        self.enabled = True
        self.last_training_time = None
        self.baseline_established = False
    
    def detect(self, event_data: Dict[str, Any]) -> Optional[AnomalyEvent]:
        """
        Detect anomalies in the provided event data
        
        Args:
            event_data: Data to analyze for anomalies
            
        Returns:
            AnomalyEvent if an anomaly is detected, None otherwise
        """
        if not self.enabled:
            return None
        
        if not self.baseline_established:
            logger.warning(f"Baseline not established for detector {self.name}")
            return None
        
        # This should be implemented by subclasses
        return None
    
    def train(self, training_data: List[Dict[str, Any]]) -> bool:
        """
        Train the detector with historical data to establish baseline
        
        Args:
            training_data: Historical data for training
            
        Returns:
            bool: True if training succeeded
        """
        # This should be implemented by subclasses
        self.last_training_time = datetime.datetime.utcnow().isoformat()
        return False
    
    def reset(self) -> None:
        """Reset the detector"""
        self.baseline_established = False
        self.last_training_time = None

class ResponseHandler:
    """Handles responses to detected anomalies"""
    
    def __init__(self, logging_service: Optional[Any] = None):
        """
        Initialize the response handler
        
        Args:
            logging_service: Logging service for recording actions
        """
        if logging_service:
            self.logging_service = logging_service
        else:
            # Try to create a LoggingService instance, or use the simple implementation
            if LOGGING_SERVICE_AVAILABLE:
                try:
                    self.logging_service = LoggingService("anomaly_detection")
                except TypeError:
                    # If LoggingService requires different parameters, use simple implementation
                    self.logging_service = SimpleLoggingService()
            else:
                self.logging_service = SimpleLoggingService()
        
        self.action_handlers = {
            ResponseAction.BLOCK_IP: self._handle_block_ip,
            ResponseAction.REQUIRE_MFA: self._handle_require_mfa,
            ResponseAction.RATE_LIMIT: self._handle_rate_limit,
            ResponseAction.NOTIFY_ADMIN: self._handle_notify_admin,
            ResponseAction.LOG_ONLY: self._handle_log_only,
            ResponseAction.REVOKE_SESSION: self._handle_revoke_session,
            ResponseAction.LOCK_ACCOUNT: self._handle_lock_account,
        }
    
    def handle_anomaly(self, anomaly_event: AnomalyEvent) -> bool:
        """
        Handle a detected anomaly by executing appropriate response actions
        
        Args:
            anomaly_event: The detected anomaly to respond to
            
        Returns:
            bool: True if handled successfully
        """
        # Log the anomaly
        self.logging_service.log_security_event(
            event_type="anomaly_detected",
            severity=anomaly_event.severity.value,
            user_id=anomaly_event.user_id,
            description=f"Anomaly detected: {anomaly_event.anomaly_type.value}",
            metadata=anomaly_event.to_dict()
        )
        
        # Execute response actions
        success = True
        for action in anomaly_event.response_actions:
            try:
                handler = self.action_handlers.get(action, self._handle_unknown)
                handler_success = handler(anomaly_event)
                success = success and handler_success
            except Exception as e:
                logger.error(f"Error executing response action {action.value}: {str(e)}")
                success = False
        
        return success
    
    def _handle_block_ip(self, anomaly_event: AnomalyEvent) -> bool:
        """Block the IP associated with the anomaly"""
        if not anomaly_event.source_ip:
            logger.warning("Cannot block IP: No source IP in anomaly event")
            return False
        
        try:
            # In a real implementation, this would call a firewall API or security tool
            logger.info(f"Blocking IP {anomaly_event.source_ip} temporarily")
            
            # Log the action
            self.logging_service.log_security_event(
                event_type="ip_blocked",
                severity="warning",
                user_id=anomaly_event.user_id,
                description=f"IP {anomaly_event.source_ip} blocked due to {anomaly_event.anomaly_type.value}",
                metadata={
                    "ip_address": anomaly_event.source_ip,
                    "anomaly_id": anomaly_event.anomaly_id,
                    "duration": "temporary"  # In a real implementation, specify the block duration
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to block IP {anomaly_event.source_ip}: {str(e)}")
            return False
    
    def _handle_require_mfa(self, anomaly_event: AnomalyEvent) -> bool:
        """Require additional authentication for the user"""
        if not anomaly_event.user_id:
            logger.warning("Cannot require MFA: No user ID in anomaly event")
            return False
        
        try:
            # In a real implementation, this would update the user's auth requirements
            logger.info(f"Requiring additional authentication for user {anomaly_event.user_id}")
            
            # Log the action
            self.logging_service.log_security_event(
                event_type="mfa_required",
                severity="info",
                user_id=anomaly_event.user_id,
                description=f"Additional authentication required for user {anomaly_event.user_id} due to {anomaly_event.anomaly_type.value}",
                metadata={
                    "anomaly_id": anomaly_event.anomaly_id
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to require MFA for user {anomaly_event.user_id}: {str(e)}")
            return False
    
    def _handle_rate_limit(self, anomaly_event: AnomalyEvent) -> bool:
        """Apply stricter rate limits"""
        try:
            target = anomaly_event.user_id or anomaly_event.source_ip
            if not target:
                logger.warning("Cannot apply rate limit: No user ID or source IP in anomaly event")
                return False
            
            # In a real implementation, this would update rate limit settings
            logger.info(f"Applying stricter rate limits for {target}")
            
            # Log the action
            self.logging_service.log_security_event(
                event_type="rate_limit_applied",
                severity="info",
                user_id=anomaly_event.user_id,
                description=f"Stricter rate limits applied for {target} due to {anomaly_event.anomaly_type.value}",
                metadata={
                    "target": target,
                    "anomaly_id": anomaly_event.anomaly_id,
                    "duration": "temporary"  # In a real implementation, specify the duration
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to apply rate limit: {str(e)}")
            return False
    
    def _handle_notify_admin(self, anomaly_event: AnomalyEvent) -> bool:
        """Notify administrators about the anomaly"""
        try:
            # In a real implementation, this would send notifications via email/Slack/etc.
            logger.info("Notifying administrators about detected anomaly")
            
            # Log the action
            self.logging_service.log_security_event(
                event_type="admin_notification_sent",
                severity="info",
                user_id=anomaly_event.user_id,
                description=f"Administrators notified about {anomaly_event.anomaly_type.value} anomaly",
                metadata={
                    "anomaly_id": anomaly_event.anomaly_id
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to notify administrators: {str(e)}")
            return False
    
    def _handle_log_only(self, anomaly_event: AnomalyEvent) -> bool:
        """Just log the anomaly without taking action"""
        # Already logged at the beginning of handle_anomaly
        return True
    
    def _handle_revoke_session(self, anomaly_event: AnomalyEvent) -> bool:
        """Revoke the user's session"""
        if not anomaly_event.user_id:
            logger.warning("Cannot revoke session: No user ID in anomaly event")
            return False
        
        try:
            # In a real implementation, this would invalidate the user's session
            logger.info(f"Revoking session for user {anomaly_event.user_id}")
            
            # Log the action
            self.logging_service.log_security_event(
                event_type="session_revoked",
                severity="warning",
                user_id=anomaly_event.user_id,
                description=f"Session revoked for user {anomaly_event.user_id} due to {anomaly_event.anomaly_type.value}",
                metadata={
                    "anomaly_id": anomaly_event.anomaly_id
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to revoke session for user {anomaly_event.user_id}: {str(e)}")
            return False
    
    def _handle_lock_account(self, anomaly_event: AnomalyEvent) -> bool:
        """Lock the user's account"""
        if not anomaly_event.user_id:
            logger.warning("Cannot lock account: No user ID in anomaly event")
            return False
        
        try:
            # In a real implementation, this would lock the user's account
            logger.info(f"Locking account for user {anomaly_event.user_id}")
            
            # Log the action
            self.logging_service.log_security_event(
                event_type="account_locked",
                severity="warning",
                user_id=anomaly_event.user_id,
                description=f"Account locked for user {anomaly_event.user_id} due to {anomaly_event.anomaly_type.value}",
                metadata={
                    "anomaly_id": anomaly_event.anomaly_id
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to lock account for user {anomaly_event.user_id}: {str(e)}")
            return False
    
    def _handle_unknown(self, anomaly_event: AnomalyEvent) -> bool:
        """Handle unknown action type"""
        logger.warning(f"Unknown response action for anomaly {anomaly_event.anomaly_id}")
        return False

class AnomalyManager:
    """
    Central manager for anomaly detection system
    
    This class coordinates the detection, storage, and response to anomalies.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the anomaly manager
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.detectors = {}
        self.response_handler = ResponseHandler()
        self.storage_path = os.environ.get("ANOMALY_STORAGE_PATH", "data/anomalies")
        self.config = self._load_config(config_path)
        
        # Initialize logging service
        if LOGGING_SERVICE_AVAILABLE:
            try:
                self.logging_service = LoggingService("anomaly_detection")
            except TypeError:
                # If LoggingService requires different parameters, use simple implementation
                self.logging_service = SimpleLoggingService()
        else:
            self.logging_service = SimpleLoggingService()
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load state if it exists
        self._load_state()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            "detection_threshold": 0.8,  # Confidence threshold for anomaly detection
            "training_interval_hours": 24,  # How often to retrain models
            "max_events_stored": 1000,  # Maximum number of events to keep
            "enable_responses": True,  # Whether to enable automated responses
            "notifications_enabled": True,  # Whether to send notifications
            "storage_retention_days": 30,  # How long to keep anomaly data
        }
        
        if not config_path or not os.path.exists(config_path):
            return default_config
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Merge with defaults for any missing keys
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            
            return config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return default_config
    
    def _load_state(self) -> None:
        """Load saved state if available"""
        state_path = os.path.join(self.storage_path, "manager_state.pkl")
        if os.path.exists(state_path):
            try:
                with open(state_path, 'rb') as f:
                    state = pickle.load(f)
                
                # Restore state variables
                if "detectors" in state:
                    self.detectors = state["detectors"]
                    
                logger.info(f"Loaded anomaly manager state with {len(self.detectors)} detectors")
            except Exception as e:
                logger.error(f"Error loading manager state: {str(e)}")
    
    def _save_state(self) -> None:
        """Save current state"""
        state_path = os.path.join(self.storage_path, "manager_state.pkl")
        try:
            # Prepare state
            state = {
                "detectors": self.detectors,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            # Save to file
            with open(state_path, 'wb') as f:
                pickle.dump(state, f)
                
            logger.debug("Saved anomaly manager state")
        except Exception as e:
            logger.error(f"Error saving manager state: {str(e)}")
    
    def register_detector(self, detector: AnomalyDetector) -> None:
        """
        Register a new anomaly detector
        
        Args:
            detector: Detector to register
        """
        self.detectors[detector.name] = detector
        logger.info(f"Registered anomaly detector: {detector.name}")
    
    def analyze_event(self, event_data: Dict[str, Any]) -> List[AnomalyEvent]:
        """
        Analyze an event for anomalies using all registered detectors
        
        Args:
            event_data: Event data to analyze
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        for detector_name, detector in self.detectors.items():
            try:
                if not detector.enabled:
                    continue
                
                anomaly = detector.detect(event_data)
                if anomaly:
                    anomalies.append(anomaly)
                    
                    # Handle the anomaly if responses are enabled
                    if self.config.get("enable_responses", True):
                        self.response_handler.handle_anomaly(anomaly)
                    
                    # Store the anomaly
                    self._store_anomaly(anomaly)
            except Exception as e:
                logger.error(f"Error in detector {detector_name}: {str(e)}")
        
        return anomalies
    
    def _store_anomaly(self, anomaly: AnomalyEvent) -> None:
        """Store an anomaly event"""
        try:
            # Create directory based on date for easier management
            date_str = anomaly.timestamp.split('T')[0]  # Extract YYYY-MM-DD
            anomaly_dir = os.path.join(self.storage_path, date_str)
            os.makedirs(anomaly_dir, exist_ok=True)
            
            # Store as JSON file
            file_path = os.path.join(anomaly_dir, f"{anomaly.anomaly_id}.json")
            with open(file_path, 'w') as f:
                json.dump(anomaly.to_dict(), f, indent=2)
                
            logger.debug(f"Stored anomaly {anomaly.anomaly_id}")
        except Exception as e:
            logger.error(f"Error storing anomaly {anomaly.anomaly_id}: {str(e)}")
    
    def get_anomaly(self, anomaly_id: str) -> Optional[AnomalyEvent]:
        """
        Retrieve a specific anomaly by ID
        
        Args:
            anomaly_id: ID of the anomaly to retrieve
            
        Returns:
            AnomalyEvent if found, None otherwise
        """
        # We don't know the date, so search in all date directories
        for root, dirs, files in os.walk(self.storage_path):
            for file in files:
                if file == f"{anomaly_id}.json":
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        return AnomalyEvent.from_dict(data)
                    except Exception as e:
                        logger.error(f"Error reading anomaly {anomaly_id}: {str(e)}")
                        return None
        
        return None
    
    def get_recent_anomalies(self, limit: int = 100, 
                            severity: Optional[List[AnomalySeverity]] = None, 
                            anomaly_type: Optional[List[AnomalyType]] = None) -> List[AnomalyEvent]:
        """
        Get recent anomaly events, optionally filtered
        
        Args:
            limit: Maximum number of anomalies to return
            severity: List of severities to filter by
            anomaly_type: List of anomaly types to filter by
            
        Returns:
            List of anomaly events
        """
        # Convert enum lists to values for comparison
        severity_values = [s.value for s in severity] if severity else None
        type_values = [t.value for t in anomaly_type] if anomaly_type else None
        
        anomalies = []
        
        # Find all anomaly files, newest date directories first
        date_dirs = [d for d in os.listdir(self.storage_path) 
                    if os.path.isdir(os.path.join(self.storage_path, d)) and d != "models"]
        date_dirs.sort(reverse=True)  # Most recent first
        
        for date_dir in date_dirs:
            dir_path = os.path.join(self.storage_path, date_dir)
            files = os.listdir(dir_path)
            
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(dir_path, file)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        # Apply filters if specified
                        if severity_values and data.get("severity") not in severity_values:
                            continue
                        
                        if type_values and data.get("anomaly_type") not in type_values:
                            continue
                        
                        anomalies.append(AnomalyEvent.from_dict(data))
                        
                        if len(anomalies) >= limit:
                            return anomalies
                    except Exception as e:
                        logger.error(f"Error reading anomaly {file}: {str(e)}")
        
        return anomalies
    
    def update_anomaly_status(self, anomaly_id: str, status: str, 
                            review_comments: Optional[str] = None,
                            reviewer_id: Optional[str] = None) -> bool:
        """
        Update the status of an anomaly
        
        Args:
            anomaly_id: ID of the anomaly to update
            status: New status (new, under_review, resolved, false_positive)
            review_comments: Comments from the reviewer (optional)
            reviewer_id: ID of the reviewer (optional)
            
        Returns:
            bool: True if update was successful
        """
        anomaly = self.get_anomaly(anomaly_id)
        if not anomaly:
            logger.warning(f"Cannot update status: Anomaly {anomaly_id} not found")
            return False
        
        # Update the anomaly
        anomaly.status = status
        if review_comments:
            anomaly.review_comments = review_comments
        if reviewer_id:
            anomaly.reviewer_id = reviewer_id
        
        # Find the file to update
        for root, dirs, files in os.walk(self.storage_path):
            for file in files:
                if file == f"{anomaly_id}.json":
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'w') as f:
                            json.dump(anomaly.to_dict(), f, indent=2)
                        
                        # Log the update
                        self.logging_service.log_security_event(
                            event_type="anomaly_status_updated",
                            severity="info",
                            user_id=reviewer_id,
                            description=f"Anomaly {anomaly_id} status updated to {status}",
                            metadata={
                                "anomaly_id": anomaly_id,
                                "previous_status": anomaly.status,
                                "new_status": status
                            }
                        )
                        
                        return True
                    except Exception as e:
                        logger.error(f"Error updating anomaly {anomaly_id}: {str(e)}")
                        return False
        
        return False
    
    def cleanup_old_anomalies(self) -> int:
        """
        Remove anomalies older than the configured retention period
        
        Returns:
            int: Number of anomalies removed
        """
        retention_days = self.config.get("storage_retention_days", 30)
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        removed_count = 0
        
        # Find all date directories
        date_dirs = [d for d in os.listdir(self.storage_path) 
                    if os.path.isdir(os.path.join(self.storage_path, d)) and d != "models"]
        
        # Remove directories older than cutoff
        for date_dir in date_dirs:
            try:
                # Skip non-date directories
                if not all(c.isdigit() or c == '-' for c in date_dir):
                    continue
                
                if date_dir < cutoff_str:
                    dir_path = os.path.join(self.storage_path, date_dir)
                    files = os.listdir(dir_path)
                    removed_count += len([f for f in files if f.endswith(".json")])
                    
                    # Remove all files in the directory
                    for file in files:
                        os.remove(os.path.join(dir_path, file))
                    
                    # Remove the directory
                    os.rmdir(dir_path)
                    logger.info(f"Removed old anomaly directory: {date_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up directory {date_dir}: {str(e)}")
        
        return removed_count
    
    def train_all_detectors(self, training_data: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Train all registered detectors with provided data
        
        Args:
            training_data: Historical data for training
            
        Returns:
            Dict mapping detector names to training success (True/False)
        """
        results = {}
        
        for name, detector in self.detectors.items():
            try:
                success = detector.train(training_data)
                results[name] = success
                logger.info(f"Trained detector {name}: {'Success' if success else 'Failed'}")
            except Exception as e:
                logger.error(f"Error training detector {name}: {str(e)}")
                results[name] = False
        
        # Save state after training
        self._save_state()
        
        return results
