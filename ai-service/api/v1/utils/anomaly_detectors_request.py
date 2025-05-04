"""
TechSaaS Request Pattern Anomaly Detectors

This module provides anomaly detectors that focus on unusual API request patterns
and authentication-related anomalies.
"""

import os
import json
import time
import datetime
import logging
import statistics
import uuid
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from collections import defaultdict, Counter
import pickle

from api.v1.utils.anomaly_detection import (
    AnomalyDetector, 
    AnomalyEvent, 
    AnomalyType, 
    AnomalySeverity, 
    ResponseAction
)

logger = logging.getLogger("techsaas.security.anomaly.request_patterns")

class RequestFrequencyAnomalyDetector(AnomalyDetector):
    """
    Detects unusually high request frequency from users or IP addresses
    
    This detector builds profiles of normal request rates and flags significant deviations
    that might indicate DoS attempts, scraping, or compromised accounts.
    """
    
    def __init__(self):
        super().__init__("request_frequency_detector", AnomalyType.REQUEST_FREQUENCY)
        # Time windows to track (in seconds)
        self.time_windows = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hr
        # Thresholds for each time window (requests per window)
        self.default_thresholds = {
            60: 30,    # 30 requests per minute
            300: 100,  # 100 requests per 5 minutes
            900: 250,  # 250 requests per 15 minutes
            3600: 600  # 600 requests per hour
        }
        # User-specific thresholds
        self.user_thresholds = {}  # {user_id: {window: threshold}}
        # IP-specific thresholds
        self.ip_thresholds = {}    # {ip: {window: threshold}}
        # Active counters - these are updated as events come in
        self.user_counters = defaultdict(lambda: defaultdict(list))  # {user_id: {window: [(timestamp, count)]}}
        self.ip_counters = defaultdict(lambda: defaultdict(list))    # {ip: {window: [(timestamp, count)]}}
        
        self.min_training_events = 1000  # Minimum number of events to establish baseline
    
    def _clean_old_counters(self, counters, window):
        """Remove counter entries older than the window"""
        now = time.time()
        cutoff = now - window
        return [entry for entry in counters if entry[0] >= cutoff]
    
    def _count_events_in_window(self, counters, window):
        """Count total events in the window"""
        return sum(entry[1] for entry in counters)
    
    def train(self, training_data: List[Dict[str, Any]]) -> bool:
        """
        Train the detector with historical request data
        
        Args:
            training_data: List of request events with user_id, ip_address, and timestamp
            
        Returns:
            bool: True if training succeeded
        """
        if not training_data or len(training_data) < self.min_training_events:
            logger.warning(f"Insufficient training data: {len(training_data) if training_data else 0} events")
            return False
        
        # Group events by user and IP
        user_events = defaultdict(list)
        ip_events = defaultdict(list)
        
        for event in training_data:
            user_id = event.get("user_id")
            ip_address = event.get("ip_address")
            timestamp = event.get("timestamp")
            
            if not timestamp:
                continue
            
            try:
                # Convert timestamp to epoch seconds
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                ts = dt.timestamp()
                
                if user_id:
                    user_events[user_id].append(ts)
                
                if ip_address:
                    ip_events[ip_address].append(ts)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid timestamp in training data: {timestamp}")
                continue
        
        # Calculate thresholds for each user
        for user_id, timestamps in user_events.items():
            timestamps.sort()
            self.user_thresholds[user_id] = {}
            
            for window in self.time_windows:
                counts = []
                
                # Sliding window approach
                for i in range(len(timestamps)):
                    start_time = timestamps[i]
                    end_time = start_time + window
                    count = sum(1 for ts in timestamps[i:] if ts <= end_time)
                    counts.append(count)
                
                if counts:
                    # Set threshold as mean + 2 * std
                    mean = statistics.mean(counts)
                    stdev = statistics.stdev(counts) if len(counts) > 1 else mean / 2
                    threshold = int(mean + 2 * stdev)
                    self.user_thresholds[user_id][window] = max(threshold, self.default_thresholds[window])
        
        # Calculate thresholds for each IP
        for ip, timestamps in ip_events.items():
            timestamps.sort()
            self.ip_thresholds[ip] = {}
            
            for window in self.time_windows:
                counts = []
                
                # Sliding window approach
                for i in range(len(timestamps)):
                    start_time = timestamps[i]
                    end_time = start_time + window
                    count = sum(1 for ts in timestamps[i:] if ts <= end_time)
                    counts.append(count)
                
                if counts:
                    # Set threshold as mean + 2 * std
                    mean = statistics.mean(counts)
                    stdev = statistics.stdev(counts) if len(counts) > 1 else mean / 2
                    threshold = int(mean + 2 * stdev)
                    self.ip_thresholds[ip][window] = max(threshold, self.default_thresholds[window])
        
        self.baseline_established = True
        self.last_training_time = datetime.datetime.utcnow().isoformat()
        
        logger.info(f"Trained frequency detector with {len(user_events)} user profiles and {len(ip_events)} IP profiles")
        return True
    
    def detect(self, event_data: Dict[str, Any]) -> Optional[AnomalyEvent]:
        """
        Detect unusually high request frequency
        
        Args:
            event_data: Event data containing user_id, ip_address, and timestamp
            
        Returns:
            AnomalyEvent if an anomaly is detected, None otherwise
        """
        if not self.baseline_established:
            return None
        
        user_id = event_data.get("user_id")
        ip_address = event_data.get("ip_address")
        timestamp = event_data.get("timestamp")
        api_endpoint = event_data.get("endpoint")
        
        if not timestamp:
            return None
        
        try:
            # Convert timestamp to epoch seconds
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            ts = time.time()  # Use current time instead of event time for real-time monitoring
            
            anomalies = []
            
            # Check user thresholds
            if user_id:
                # Update user counters
                for window in self.time_windows:
                    # Clean old counters
                    self.user_counters[user_id][window] = self._clean_old_counters(
                        self.user_counters[user_id][window], window)
                    
                    # Add new counter or increment last counter if it's recent
                    if self.user_counters[user_id][window] and ts - self.user_counters[user_id][window][-1][0] < 1:
                        # Increment recent counter
                        last_ts, count = self.user_counters[user_id][window][-1]
                        self.user_counters[user_id][window][-1] = (last_ts, count + 1)
                    else:
                        # Add new counter
                        self.user_counters[user_id][window].append((ts, 1))
                    
                    # Check if threshold is exceeded
                    count = self._count_events_in_window(self.user_counters[user_id][window], window)
                    
                    # Get threshold for this user and window
                    threshold = self.default_thresholds[window]
                    if user_id in self.user_thresholds and window in self.user_thresholds[user_id]:
                        threshold = self.user_thresholds[user_id][window]
                    
                    if count > threshold:
                        # Calculate how much the threshold is exceeded
                        excess_ratio = count / threshold
                        
                        # Determine severity based on excess
                        severity = AnomalySeverity.LOW
                        if excess_ratio > 5:
                            severity = AnomalySeverity.CRITICAL
                        elif excess_ratio > 3:
                            severity = AnomalySeverity.HIGH
                        elif excess_ratio > 1.5:
                            severity = AnomalySeverity.MEDIUM
                        
                        # Determine response actions based on severity
                        response_actions = [ResponseAction.LOG_ONLY]
                        if severity == AnomalySeverity.LOW:
                            response_actions = [ResponseAction.LOG_ONLY]
                        elif severity == AnomalySeverity.MEDIUM:
                            response_actions = [ResponseAction.LOG_ONLY, ResponseAction.NOTIFY_ADMIN]
                        elif severity == AnomalySeverity.HIGH:
                            response_actions = [
                                ResponseAction.LOG_ONLY, 
                                ResponseAction.NOTIFY_ADMIN,
                                ResponseAction.RATE_LIMIT
                            ]
                        elif severity == AnomalySeverity.CRITICAL:
                            response_actions = [
                                ResponseAction.LOG_ONLY, 
                                ResponseAction.NOTIFY_ADMIN,
                                ResponseAction.RATE_LIMIT,
                                ResponseAction.REQUIRE_MFA
                            ]
                        
                        # Create anomaly event
                        anomalies.append(AnomalyEvent(
                            anomaly_id=str(uuid.uuid4()),
                            timestamp=timestamp,
                            anomaly_type=AnomalyType.REQUEST_FREQUENCY,
                            severity=severity,
                            source_ip=ip_address,
                            user_id=user_id,
                            api_endpoint=api_endpoint,
                            details={
                                "window_seconds": window,
                                "request_count": count,
                                "threshold": threshold,
                                "excess_ratio": round(excess_ratio, 2),
                                "detection_method": "user_frequency"
                            },
                            response_actions=response_actions
                        ))
            
            # Check IP thresholds
            if ip_address:
                # Update IP counters
                for window in self.time_windows:
                    # Clean old counters
                    self.ip_counters[ip_address][window] = self._clean_old_counters(
                        self.ip_counters[ip_address][window], window)
                    
                    # Add new counter or increment last counter if it's recent
                    if self.ip_counters[ip_address][window] and ts - self.ip_counters[ip_address][window][-1][0] < 1:
                        # Increment recent counter
                        last_ts, count = self.ip_counters[ip_address][window][-1]
                        self.ip_counters[ip_address][window][-1] = (last_ts, count + 1)
                    else:
                        # Add new counter
                        self.ip_counters[ip_address][window].append((ts, 1))
                    
                    # Check if threshold is exceeded
                    count = self._count_events_in_window(self.ip_counters[ip_address][window], window)
                    
                    # Get threshold for this IP and window
                    threshold = self.default_thresholds[window]
                    if ip_address in self.ip_thresholds and window in self.ip_thresholds[ip_address]:
                        threshold = self.ip_thresholds[ip_address][window]
                    
                    if count > threshold:
                        # Calculate how much the threshold is exceeded
                        excess_ratio = count / threshold
                        
                        # Determine severity based on excess
                        severity = AnomalySeverity.LOW
                        if excess_ratio > 5:
                            severity = AnomalySeverity.CRITICAL
                        elif excess_ratio > 3:
                            severity = AnomalySeverity.HIGH
                        elif excess_ratio > 1.5:
                            severity = AnomalySeverity.MEDIUM
                        
                        # Determine response actions based on severity
                        response_actions = [ResponseAction.LOG_ONLY]
                        if severity == AnomalySeverity.LOW:
                            response_actions = [ResponseAction.LOG_ONLY]
                        elif severity == AnomalySeverity.MEDIUM:
                            response_actions = [ResponseAction.LOG_ONLY, ResponseAction.NOTIFY_ADMIN]
                        elif severity == AnomalySeverity.HIGH:
                            response_actions = [
                                ResponseAction.LOG_ONLY, 
                                ResponseAction.NOTIFY_ADMIN,
                                ResponseAction.RATE_LIMIT
                            ]
                        elif severity == AnomalySeverity.CRITICAL:
                            response_actions = [
                                ResponseAction.LOG_ONLY, 
                                ResponseAction.NOTIFY_ADMIN,
                                ResponseAction.RATE_LIMIT,
                                ResponseAction.BLOCK_IP
                            ]
                        
                        # Create anomaly event
                        anomalies.append(AnomalyEvent(
                            anomaly_id=str(uuid.uuid4()),
                            timestamp=timestamp,
                            anomaly_type=AnomalyType.REQUEST_FREQUENCY,
                            severity=severity,
                            source_ip=ip_address,
                            user_id=user_id,
                            api_endpoint=api_endpoint,
                            details={
                                "window_seconds": window,
                                "request_count": count,
                                "threshold": threshold,
                                "excess_ratio": round(excess_ratio, 2),
                                "detection_method": "ip_frequency"
                            },
                            response_actions=response_actions
                        ))
            
            # Return the most severe anomaly
            if anomalies:
                return max(anomalies, key=lambda a: list(AnomalySeverity).index(a.severity))
        except Exception as e:
            logger.warning(f"Error processing event: {str(e)}")
        
        return None
    
    def save_model(self, path: str) -> bool:
        """Save the trained model to disk"""
        try:
            model_dir = os.path.join(path, "models")
            os.makedirs(model_dir, exist_ok=True)
            
            model_path = os.path.join(model_dir, f"{self.name}.pkl")
            
            with open(model_path, 'wb') as f:
                pickle.dump({
                    "user_thresholds": self.user_thresholds,
                    "ip_thresholds": self.ip_thresholds,
                    "last_training_time": self.last_training_time,
                    "baseline_established": self.baseline_established
                }, f)
            
            return True
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return False
    
    def load_model(self, path: str) -> bool:
        """Load the trained model from disk"""
        model_path = os.path.join(path, "models", f"{self.name}.pkl")
        
        if not os.path.exists(model_path):
            logger.warning(f"Model file does not exist: {model_path}")
            return False
        
        try:
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
            
            self.user_thresholds = data.get("user_thresholds", {})
            self.ip_thresholds = data.get("ip_thresholds", {})
            self.last_training_time = data.get("last_training_time")
            self.baseline_established = data.get("baseline_established", False)
            
            return True
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False


class AuthenticationAnomalyDetector(AnomalyDetector):
    """
    Detects unusual authentication patterns
    
    This detector identifies potential brute force attacks, password spraying,
    or other suspicious authentication activities.
    """
    
    def __init__(self):
        super().__init__("authentication_anomaly_detector", AnomalyType.AUTHENTICATION_FAILURE)
        # Time windows to track (in seconds)
        self.windows = [300, 900, 3600, 86400]  # 5min, 15min, 1hr, 24hr
        # Thresholds for each time window (failures per window)
        self.thresholds = {
            300: 5,     # 5 failures in 5 minutes
            900: 10,    # 10 failures in 15 minutes
            3600: 20,   # 20 failures in 1 hour
            86400: 50   # 50 failures in 24 hours
        }
        # Active counters - these are updated as events come in
        self.user_failures = defaultdict(list)      # {user_id: [(timestamp, ip)]}
        self.ip_failures = defaultdict(list)        # {ip: [(timestamp, user_id)]}
        self.endpoint_failures = defaultdict(list)  # {endpoint: [(timestamp, ip, user_id)]}
    
    def _clean_old_entries(self, entries, window):
        """Remove entries older than the window"""
        now = time.time()
        cutoff = now - window
        return [entry for entry in entries if entry[0] >= cutoff]
    
    def train(self, training_data: List[Dict[str, Any]]) -> bool:
        """
        Train the detector - not required for this detector
        
        Args:
            training_data: Not used
            
        Returns:
            bool: True if training succeeded
        """
        # This detector doesn't need training; it uses fixed thresholds
        self.baseline_established = True
        self.last_training_time = datetime.datetime.utcnow().isoformat()
        return True
    
    def detect(self, event_data: Dict[str, Any]) -> Optional[AnomalyEvent]:
        """
        Detect authentication anomalies
        
        Args:
            event_data: Event data containing user_id, ip_address, and timestamp
            
        Returns:
            AnomalyEvent if an anomaly is detected, None otherwise
        """
        user_id = event_data.get("user_id")
        ip_address = event_data.get("ip_address")
        timestamp = event_data.get("timestamp")
        api_endpoint = event_data.get("endpoint")
        auth_success = event_data.get("authentication_success", True)
        
        if not timestamp:
            return None
        
        try:
            # Convert timestamp to epoch seconds
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            ts = time.time()  # Use current time for real-time monitoring
            
            # Only track failed authentication attempts
            if auth_success:
                return None
            
            anomalies = []
            
            # Update counters
            if user_id:
                self.user_failures[user_id].append((ts, ip_address))
            
            if ip_address:
                self.ip_failures[ip_address].append((ts, user_id))
            
            if api_endpoint:
                self.endpoint_failures[api_endpoint].append((ts, ip_address, user_id))
            
            # Check for anomalies
            for window in self.windows:
                threshold = self.thresholds[window]
                
                # Check user failure rate
                if user_id:
                    # Clean old entries
                    self.user_failures[user_id] = self._clean_old_entries(self.user_failures[user_id], window)
                    
                    # Count failures in window
                    failures = len(self.user_failures[user_id])
                    
                    if failures >= threshold:
                        # Count unique IPs
                        unique_ips = len(set(ip for _, ip in self.user_failures[user_id] if ip))
                        
                        # Determine if this looks like a brute force (single IP) or distributed attack
                        is_distributed = unique_ips > 1
                        
                        # Determine severity based on excess and distribution
                        excess_ratio = failures / threshold
                        
                        severity = AnomalySeverity.MEDIUM
                        if excess_ratio > 3:
                            severity = AnomalySeverity.CRITICAL if is_distributed else AnomalySeverity.HIGH
                        elif excess_ratio > 1.5:
                            severity = AnomalySeverity.HIGH if is_distributed else AnomalySeverity.MEDIUM
                        
                        # Determine response actions based on severity
                        response_actions = [ResponseAction.LOG_ONLY, ResponseAction.NOTIFY_ADMIN]
                        if severity == AnomalySeverity.MEDIUM:
                            response_actions.append(ResponseAction.REQUIRE_MFA)
                        elif severity == AnomalySeverity.HIGH:
                            response_actions.extend([
                                ResponseAction.REQUIRE_MFA,
                                ResponseAction.LOCK_ACCOUNT
                            ])
                        elif severity == AnomalySeverity.CRITICAL:
                            response_actions.extend([
                                ResponseAction.REQUIRE_MFA,
                                ResponseAction.LOCK_ACCOUNT,
                                ResponseAction.BLOCK_IP
                            ])
                        
                        # Create anomaly event
                        anomalies.append(AnomalyEvent(
                            anomaly_id=str(uuid.uuid4()),
                            timestamp=timestamp,
                            anomaly_type=AnomalyType.AUTHENTICATION_FAILURE,
                            severity=severity,
                            source_ip=ip_address,
                            user_id=user_id,
                            api_endpoint=api_endpoint,
                            details={
                                "window_seconds": window,
                                "failure_count": failures,
                                "threshold": threshold,
                                "unique_ips": unique_ips,
                                "is_distributed": is_distributed,
                                "detection_method": "user_auth_failures"
                            },
                            response_actions=response_actions
                        ))
                
                # Check IP failure rate
                if ip_address:
                    # Clean old entries
                    self.ip_failures[ip_address] = self._clean_old_entries(self.ip_failures[ip_address], window)
                    
                    # Count failures in window
                    failures = len(self.ip_failures[ip_address])
                    
                    if failures >= threshold:
                        # Count unique users
                        unique_users = len(set(user for _, user in self.ip_failures[ip_address] if user))
                        
                        # Determine if this looks like a brute force (single user) or password spraying (multiple users)
                        is_password_spray = unique_users > 1
                        
                        # Determine severity based on excess and attack type
                        excess_ratio = failures / threshold
                        
                        severity = AnomalySeverity.MEDIUM
                        if excess_ratio > 3:
                            severity = AnomalySeverity.CRITICAL if is_password_spray else AnomalySeverity.HIGH
                        elif excess_ratio > 1.5:
                            severity = AnomalySeverity.HIGH if is_password_spray else AnomalySeverity.MEDIUM
                        
                        # Determine response actions based on severity
                        response_actions = [ResponseAction.LOG_ONLY, ResponseAction.NOTIFY_ADMIN]
                        if severity == AnomalySeverity.MEDIUM:
                            response_actions.append(ResponseAction.RATE_LIMIT)
                        elif severity == AnomalySeverity.HIGH:
                            response_actions.extend([
                                ResponseAction.RATE_LIMIT,
                                ResponseAction.REQUIRE_MFA
                            ])
                        elif severity == AnomalySeverity.CRITICAL:
                            response_actions.extend([
                                ResponseAction.RATE_LIMIT,
                                ResponseAction.REQUIRE_MFA,
                                ResponseAction.BLOCK_IP
                            ])
                        
                        # Create anomaly event
                        anomalies.append(AnomalyEvent(
                            anomaly_id=str(uuid.uuid4()),
                            timestamp=timestamp,
                            anomaly_type=AnomalyType.AUTHENTICATION_FAILURE,
                            severity=severity,
                            source_ip=ip_address,
                            user_id=user_id,
                            api_endpoint=api_endpoint,
                            details={
                                "window_seconds": window,
                                "failure_count": failures,
                                "threshold": threshold,
                                "unique_users": unique_users,
                                "is_password_spray": is_password_spray,
                                "detection_method": "ip_auth_failures"
                            },
                            response_actions=response_actions
                        ))
            
            # Return the most severe anomaly
            if anomalies:
                return max(anomalies, key=lambda a: list(AnomalySeverity).index(a.severity))
        except Exception as e:
            logger.warning(f"Error processing event: {str(e)}")
        
        return None
