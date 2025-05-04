"""
TechSaaS Anomaly Detector Implementations

This module provides specific implementations of anomaly detectors for
different types of unusual behaviors and potential security threats.
"""

import os
import json
import time
import datetime
import logging
import statistics
import ipaddress
import uuid
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from collections import defaultdict, Counter
import pickle
import geoip2.database
from scipy.stats import zscore

from api.v1.utils.anomaly_detection import (
    AnomalyDetector, 
    AnomalyEvent, 
    AnomalyType, 
    AnomalySeverity, 
    ResponseAction
)

logger = logging.getLogger("techsaas.security.anomaly.detectors")

class AccessTimeAnomalyDetector(AnomalyDetector):
    """
    Detects unusual access times for users
    
    This detector builds a profile of normal access hours for each user and
    flags accesses that occur outside the user's typical pattern.
    """
    
    def __init__(self):
        super().__init__("access_time_detector", AnomalyType.ACCESS_TIME)
        self.user_profiles = {}  # {user_id: {hour: frequency}}
        self.min_data_points = 20  # Minimum data points to establish a baseline
        self.z_score_threshold = 3.0  # Z-score threshold for anomaly detection
    
    def train(self, training_data: List[Dict[str, Any]]) -> bool:
        """
        Train the detector with historical access data
        
        Args:
            training_data: List of access events with timestamp and user_id
            
        Returns:
            bool: True if training succeeded
        """
        if not training_data:
            logger.warning("No training data provided")
            return False
        
        # Reset user profiles
        self.user_profiles = defaultdict(lambda: defaultdict(int))
        
        # Process training data
        for event in training_data:
            user_id = event.get("user_id")
            timestamp = event.get("timestamp")
            
            if not user_id or not timestamp:
                continue
            
            try:
                # Parse timestamp and extract hour
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour = dt.hour
                
                # Update profile
                self.user_profiles[user_id][hour] += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid timestamp in training data: {timestamp}")
                continue
        
        # Convert defaultdicts to regular dicts for pickling
        self.user_profiles = {k: dict(v) for k, v in self.user_profiles.items()}
        
        # Check if we have enough data
        valid_users = [user_id for user_id, hours in self.user_profiles.items() 
                      if sum(hours.values()) >= self.min_data_points]
        
        self.baseline_established = len(valid_users) > 0
        self.last_training_time = datetime.datetime.utcnow().isoformat()
        
        logger.info(f"Trained access time detector with {len(valid_users)} valid user profiles")
        return self.baseline_established
    
    def detect(self, event_data: Dict[str, Any]) -> Optional[AnomalyEvent]:
        """
        Detect anomalous access times
        
        Args:
            event_data: Event data containing user_id and timestamp
            
        Returns:
            AnomalyEvent if an anomaly is detected, None otherwise
        """
        if not self.baseline_established:
            return None
        
        user_id = event_data.get("user_id")
        timestamp = event_data.get("timestamp")
        source_ip = event_data.get("ip_address")
        api_endpoint = event_data.get("endpoint")
        
        if not user_id or not timestamp:
            return None
        
        # If we don't have a profile for this user, we can't detect anomalies
        if user_id not in self.user_profiles:
            return None
        
        try:
            # Parse timestamp and extract hour
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            hour = dt.hour
            
            user_profile = self.user_profiles[user_id]
            
            # If the user has never accessed during this hour
            if hour not in user_profile or user_profile[hour] == 0:
                # Check if we have enough data points for this user
                if sum(user_profile.values()) >= self.min_data_points:
                    # Calculate how unusual this is
                    hours_frequency = [user_profile.get(h, 0) for h in range(24)]
                    mean_freq = statistics.mean(hours_frequency)
                    
                    # If most hours have zero access, this approach doesn't work well
                    # So check how many non-zero hours we have
                    non_zero_hours = sum(1 for f in hours_frequency if f > 0)
                    
                    if non_zero_hours >= 6:  # At least 6 active hours to establish a pattern
                        # Create anomaly event
                        severity = AnomalySeverity.MEDIUM
                        # Make the severity higher during night hours (11 PM to 5 AM)
                        if hour >= 23 or hour <= 5:
                            severity = AnomalySeverity.HIGH
                        
                        anomaly_id = str(uuid.uuid4())
                        
                        return AnomalyEvent(
                            anomaly_id=anomaly_id,
                            timestamp=timestamp,
                            anomaly_type=self.anomaly_type,
                            severity=severity,
                            source_ip=source_ip,
                            user_id=user_id,
                            api_endpoint=api_endpoint,
                            details={
                                "unusual_hour": hour,
                                "user_typical_hours": [h for h, f in user_profile.items() if f > 0],
                                "detection_method": "unusual_access_hour"
                            },
                            response_actions=[
                                ResponseAction.LOG_ONLY,
                                ResponseAction.NOTIFY_ADMIN
                            ]
                        )
            # If the user has accessed during this hour, but it's rare
            elif user_profile[hour] < max(user_profile.values()) * 0.1:  # Less than 10% of the most common hour
                # This is unusual but not as suspicious
                return AnomalyEvent(
                    anomaly_id=str(uuid.uuid4()),
                    timestamp=timestamp,
                    anomaly_type=self.anomaly_type,
                    severity=AnomalySeverity.LOW,
                    source_ip=source_ip,
                    user_id=user_id,
                    api_endpoint=api_endpoint,
                    details={
                        "unusual_hour": hour,
                        "frequency_at_hour": user_profile[hour],
                        "max_frequency": max(user_profile.values()),
                        "user_typical_hours": [h for h, f in user_profile.items() if f > max(user_profile.values()) * 0.5],
                        "detection_method": "rare_access_hour"
                    },
                    response_actions=[ResponseAction.LOG_ONLY]
                )
        except (ValueError, TypeError) as e:
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
                    "user_profiles": self.user_profiles,
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
            
            self.user_profiles = data.get("user_profiles", {})
            self.last_training_time = data.get("last_training_time")
            self.baseline_established = data.get("baseline_established", False)
            
            return True
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False


class GeoLocationAnomalyDetector(AnomalyDetector):
    """
    Detects unusual geographic locations for user accesses
    
    This detector builds a profile of normal locations for each user and
    flags accesses that occur from unusual locations or indicate impossible travel.
    """
    
    def __init__(self, geoip_db_path: Optional[str] = None):
        super().__init__("geo_location_detector", AnomalyType.GEOGRAPHIC_LOCATION)
        self.user_locations = {}  # {user_id: {country_code: frequency}}
        self.user_last_access = {}  # {user_id: (timestamp, country, city, lat, lon)}
        self.min_data_points = 10  # Minimum data points to establish a baseline
        
        # Initialize GeoIP database if available
        self.geoip_reader = None
        if geoip_db_path and os.path.exists(geoip_db_path):
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
            except Exception as e:
                logger.error(f"Error initializing GeoIP database: {str(e)}")
        else:
            logger.warning("GeoIP database not available, using mock location data for demo")
    
    def _get_location_from_ip(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get location information from IP address"""
        if not ip_address:
            return None
        
        try:
            if self.geoip_reader:
                # Use real GeoIP database
                response = self.geoip_reader.city(ip_address)
                return {
                    "country_code": response.country.iso_code,
                    "country_name": response.country.name,
                    "city": response.city.name,
                    "latitude": response.location.latitude,
                    "longitude": response.location.longitude
                }
            else:
                # Use mock data for demonstration
                # In a real implementation, you'd use a proper GeoIP database
                mock_data = {
                    "192.168.1.1": {"country_code": "US", "country_name": "United States", "city": "New York", "latitude": 40.7128, "longitude": -74.0060},
                    "10.0.0.1": {"country_code": "GB", "country_name": "United Kingdom", "city": "London", "latitude": 51.5074, "longitude": -0.1278},
                    "172.16.0.1": {"country_code": "AU", "country_name": "Australia", "city": "Sydney", "latitude": -33.8688, "longitude": 151.2093},
                    "127.0.0.1": {"country_code": "US", "country_name": "United States", "city": "Los Angeles", "latitude": 34.0522, "longitude": -118.2437}
                }
                
                # Generate a consistent result for IPs not in our mock data
                if ip_address not in mock_data:
                    import hashlib
                    # Use hash of IP to get a consistent country
                    hash_value = int(hashlib.md5(ip_address.encode()).hexdigest(), 16)
                    countries = list(mock_data.values())
                    return countries[hash_value % len(countries)]
                
                return mock_data.get(ip_address)
        except Exception as e:
            logger.error(f"Error getting location for IP {ip_address}: {str(e)}")
            return None
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in kilometers using the haversine formula
        """
        # Convert latitude and longitude from degrees to radians
        lat1_rad = np.radians(lat1)
        lon1_rad = np.radians(lon1)
        lat2_rad = np.radians(lat2)
        lon2_rad = np.radians(lon2)
        
        # Haversine formula
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        r = 6371  # Radius of earth in kilometers
        
        return c * r
    
    def _calculate_travel_speed(self, distance_km: float, time_diff_hours: float) -> float:
        """Calculate travel speed in km/h"""
        if time_diff_hours <= 0:
            return float('inf')  # Avoid division by zero
        
        return distance_km / time_diff_hours
    
    def train(self, training_data: List[Dict[str, Any]]) -> bool:
        """
        Train the detector with historical location data
        
        Args:
            training_data: List of access events with user_id and ip_address
            
        Returns:
            bool: True if training succeeded
        """
        if not training_data:
            logger.warning("No training data provided")
            return False
        
        # Reset user locations
        self.user_locations = defaultdict(lambda: defaultdict(int))
        
        # Process training data
        for event in training_data:
            user_id = event.get("user_id")
            ip_address = event.get("ip_address")
            
            if not user_id or not ip_address:
                continue
            
            try:
                # Get location from IP
                location = self._get_location_from_ip(ip_address)
                if not location or "country_code" not in location:
                    continue
                
                # Update profile
                country_code = location["country_code"]
                self.user_locations[user_id][country_code] += 1
            except Exception as e:
                logger.warning(f"Error processing training event: {str(e)}")
                continue
        
        # Convert defaultdicts to regular dicts for pickling
        self.user_locations = {k: dict(v) for k, v in self.user_locations.items()}
        
        # Check if we have enough data
        valid_users = [user_id for user_id, countries in self.user_locations.items() 
                      if sum(countries.values()) >= self.min_data_points]
        
        self.baseline_established = len(valid_users) > 0
        self.last_training_time = datetime.datetime.utcnow().isoformat()
        
        logger.info(f"Trained geo location detector with {len(valid_users)} valid user profiles")
        return self.baseline_established
    
    def detect(self, event_data: Dict[str, Any]) -> Optional[AnomalyEvent]:
        """
        Detect anomalous geographic locations
        
        Args:
            event_data: Event data containing user_id and ip_address
            
        Returns:
            AnomalyEvent if an anomaly is detected, None otherwise
        """
        if not self.baseline_established:
            return None
        
        user_id = event_data.get("user_id")
        ip_address = event_data.get("ip_address")
        timestamp = event_data.get("timestamp")
        api_endpoint = event_data.get("endpoint")
        
        if not user_id or not ip_address or not timestamp:
            return None
        
        try:
            # Parse timestamp
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Get location from IP
            location = self._get_location_from_ip(ip_address)
            if not location or "country_code" not in location:
                return None
            
            country_code = location["country_code"]
            city = location.get("city", "Unknown")
            latitude = location.get("latitude")
            longitude = location.get("longitude")
            
            # Check for anomalies
            anomaly_detected = False
            anomaly_details = {}
            severity = AnomalySeverity.MEDIUM
            response_actions = [ResponseAction.LOG_ONLY, ResponseAction.NOTIFY_ADMIN]
            
            # 1. Check if user has a profile
            if user_id not in self.user_locations:
                return None
            
            user_profile = self.user_locations[user_id]
            
            # 2. Check if this is a new country for the user
            if country_code not in user_profile or user_profile[country_code] == 0:
                anomaly_detected = True
                anomaly_details["detection_method"] = "new_country"
                anomaly_details["country"] = country_code
                anomaly_details["known_countries"] = list(user_profile.keys())
                
                # If the user mostly accesses from a single country, this is more suspicious
                dominant_country = max(user_profile.items(), key=lambda x: x[1])[0]
                dominant_ratio = user_profile[dominant_country] / sum(user_profile.values())
                
                if dominant_ratio > 0.9:  # User accesses from one country >90% of the time
                    severity = AnomalySeverity.HIGH
                    response_actions.append(ResponseAction.REQUIRE_MFA)
            
            # 3. Check for impossible travel
            if user_id in self.user_last_access and latitude is not None and longitude is not None:
                last_timestamp, last_country, last_city, last_lat, last_lon = self.user_last_access[user_id]
                
                try:
                    # Calculate time difference in hours
                    last_dt = datetime.datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                    time_diff = dt - last_dt
                    time_diff_hours = time_diff.total_seconds() / 3600
                    
                    # Only check if the time difference is positive and less than 24 hours
                    if 0 < time_diff_hours < 24:
                        # Calculate distance and speed
                        distance = self._calculate_distance(last_lat, last_lon, latitude, longitude)
                        
                        # If distance is significant
                        if distance > 100:  # More than 100km
                            speed = self._calculate_travel_speed(distance, time_diff_hours)
                            
                            # Check if travel speed is unrealistic (>800 km/h)
                            if speed > 800:
                                anomaly_detected = True
                                anomaly_details["detection_method"] = "impossible_travel"
                                anomaly_details["distance_km"] = round(distance, 2)
                                anomaly_details["time_diff_hours"] = round(time_diff_hours, 2)
                                anomaly_details["speed_kmh"] = round(speed, 2)
                                anomaly_details["previous_location"] = {
                                    "country": last_country,
                                    "city": last_city,
                                    "timestamp": last_timestamp
                                }
                                anomaly_details["current_location"] = {
                                    "country": country_code,
                                    "city": city,
                                    "timestamp": timestamp
                                }
                                
                                severity = AnomalySeverity.CRITICAL
                                response_actions = [
                                    ResponseAction.LOG_ONLY,
                                    ResponseAction.NOTIFY_ADMIN,
                                    ResponseAction.REQUIRE_MFA,
                                    ResponseAction.REVOKE_SESSION
                                ]
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error calculating travel metrics: {str(e)}")
            
            # Update last access information
            if latitude is not None and longitude is not None:
                self.user_last_access[user_id] = (timestamp, country_code, city, latitude, longitude)
            
            # Return anomaly if detected
            if anomaly_detected:
                return AnomalyEvent(
                    anomaly_id=str(uuid.uuid4()),
                    timestamp=timestamp,
                    anomaly_type=self.anomaly_type,
                    severity=severity,
                    source_ip=ip_address,
                    user_id=user_id,
                    api_endpoint=api_endpoint,
                    details=anomaly_details,
                    response_actions=response_actions
                )
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
                    "user_locations": self.user_locations,
                    "user_last_access": self.user_last_access,
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
            
            self.user_locations = data.get("user_locations", {})
            self.user_last_access = data.get("user_last_access", {})
            self.last_training_time = data.get("last_training_time")
            self.baseline_established = data.get("baseline_established", False)
            
            return True
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
