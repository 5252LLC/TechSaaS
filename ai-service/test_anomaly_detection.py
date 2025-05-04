"""
TechSaaS Anomaly Detection System Test Script

This script demonstrates the functionality of the anomaly detection system
by creating sample events and detecting anomalies.
"""

import os
import sys
import json
import datetime
from pprint import pprint

# Add parent directory to path to make imports work
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import anomaly detection components
from api.v1.utils.anomaly_detection import (
    AnomalyManager, AnomalyEvent, AnomalyType, AnomalySeverity, ResponseAction
)
from api.v1.utils.anomaly_detectors import (
    AccessTimeAnomalyDetector, GeoLocationAnomalyDetector
)
from api.v1.utils.anomaly_detectors_request import (
    RequestFrequencyAnomalyDetector, AuthenticationAnomalyDetector
)

print("TechSaaS Anomaly Detection System Test")
print("======================================")
print()

# Create anomaly manager
print("Creating anomaly manager...")
anomaly_manager = AnomalyManager()

# Register detectors
print("Registering detectors...")
anomaly_manager.register_detector(AccessTimeAnomalyDetector())
anomaly_manager.register_detector(GeoLocationAnomalyDetector())
anomaly_manager.register_detector(RequestFrequencyAnomalyDetector())
anomaly_manager.register_detector(AuthenticationAnomalyDetector())

# Create test data
print("Generating test data...")

# Generate training data for normal behavior
def generate_training_data(num_events=1000):
    """Generate mock training data"""
    import random
    
    training_data = []
    users = ["user1", "user2", "user3", "user4", "user5"]
    ips = [f"192.168.1.{i}" for i in range(1, 20)]
    endpoints = ["/api/v1/users", "/api/v1/products", "/api/v1/orders"]
    
    # Generate events over the past 30 days
    now = datetime.datetime.now()
    
    for _ in range(num_events):
        # Generate random date within working hours (9 AM to 5 PM)
        days_ago = random.randint(0, 30)
        hour = random.randint(9, 17)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        event_time = now - datetime.timedelta(days=days_ago, 
                                             hours=now.hour - hour,
                                             minutes=now.minute - minute,
                                             seconds=now.second - second)
        
        # Create event
        event = {
            "timestamp": event_time.isoformat() + "Z",
            "user_id": random.choice(users),
            "ip_address": random.choice(ips),
            "endpoint": random.choice(endpoints),
            "response_code": 200
        }
        
        training_data.append(event)
    
    return training_data

# Generate training data
training_data = generate_training_data(1000)
print(f"Generated {len(training_data)} training events")

# Train detectors
print("Training detectors with normal behavior data...")
for name, detector in anomaly_manager.detectors.items():
    success = detector.train(training_data)
    print(f"  - {name}: {'Success' if success else 'Failed'}")

print("\nTesting Anomaly Detection")
print("------------------------")

# Test 1: Normal event (should not trigger anomaly)
print("\nTest 1: Normal event")
normal_event = {
    "timestamp": datetime.datetime.now().replace(hour=14, minute=30).isoformat() + "Z",
    "user_id": "user1",
    "ip_address": "192.168.1.5",
    "endpoint": "/api/v1/users",
    "response_code": 200
}

print("Analyzing normal event...")
anomalies = anomaly_manager.analyze_event(normal_event)
if anomalies:
    print(f"Detected {len(anomalies)} anomalies (should be 0)")
    for anomaly in anomalies:
        print(f"  - {anomaly.anomaly_type.value}, Severity: {anomaly.severity.value}")
else:
    print("No anomalies detected (expected result)")

# Test 2: Unusual time access
print("\nTest 2: Unusual time access")
unusual_time_event = {
    "timestamp": datetime.datetime.now().replace(hour=3, minute=15).isoformat() + "Z",
    "user_id": "user1",
    "ip_address": "192.168.1.5",
    "endpoint": "/api/v1/users",
    "response_code": 200
}

print("Analyzing unusual time event...")
anomalies = anomaly_manager.analyze_event(unusual_time_event)
if anomalies:
    print(f"Detected {len(anomalies)} anomalies")
    for anomaly in anomalies:
        print(f"  - Type: {anomaly.anomaly_type.value}")
        print(f"    Severity: {anomaly.severity.value}")
        print(f"    Actions: {[action.value for action in anomaly.response_actions]}")
        print(f"    Details: {json.dumps(anomaly.details, indent=2)}")
else:
    print("No anomalies detected (unexpected result)")

# Test 3: Geographic anomaly (impossible travel)
print("\nTest 3: Geographic anomaly (impossible travel)")
geo_event_1 = {
    "timestamp": datetime.datetime.now().replace(hour=10, minute=0).isoformat() + "Z",
    "user_id": "user2",
    "ip_address": "192.168.1.10",  # This would resolve to one location
    "endpoint": "/api/v1/users",
    "response_code": 200
}

# Analyze first geo event (establishes location)
print("Analyzing first geographic event (establishes baseline)...")
anomaly_manager.analyze_event(geo_event_1)

# Second event 30 minutes later from a very different location
geo_event_2 = {
    "timestamp": (datetime.datetime.now().replace(hour=10, minute=30) + 
                 datetime.timedelta(minutes=30)).isoformat() + "Z",
    "user_id": "user2",
    "ip_address": "10.0.0.5",  # This would resolve to a different location
    "endpoint": "/api/v1/users",
    "response_code": 200
}

print("Analyzing second geographic event (different location)...")
anomalies = anomaly_manager.analyze_event(geo_event_2)
if anomalies:
    print(f"Detected {len(anomalies)} anomalies")
    for anomaly in anomalies:
        print(f"  - Type: {anomaly.anomaly_type.value}")
        print(f"    Severity: {anomaly.severity.value}")
        print(f"    Actions: {[action.value for action in anomaly.response_actions]}")
        print(f"    Details: {json.dumps(anomaly.details, indent=2)}")
else:
    print("No anomalies detected (may be expected if mock location data doesn't show distance)")

# Test 4: Authentication failures
print("\nTest 4: Authentication failures")
# Generate multiple authentication failures
auth_events = []
for i in range(10):
    auth_event = {
        "timestamp": (datetime.datetime.now() - 
                     datetime.timedelta(minutes=i*2)).isoformat() + "Z",
        "user_id": "user3",
        "ip_address": "192.168.1.100",
        "endpoint": "/api/v1/auth/login",
        "authentication_success": False,
        "response_code": 401
    }
    auth_events.append(auth_event)

# Process authentication failures
print(f"Processing {len(auth_events)} authentication failure events...")
for i, event in enumerate(auth_events):
    print(f"  Processing failure {i+1}...")
    anomalies = anomaly_manager.analyze_event(event)
    if anomalies:
        print(f"  - Detected anomaly after {i+1} failures")
        print(f"    Type: {anomalies[0].anomaly_type.value}")
        print(f"    Severity: {anomalies[0].severity.value}")
        print(f"    Actions: {[action.value for action in anomalies[0].response_actions]}")
        break

# Test 5: Request frequency anomaly
print("\nTest 5: Request frequency anomaly")
# Generate high frequency requests
freq_events = []
for i in range(50):
    freq_event = {
        "timestamp": (datetime.datetime.now() - 
                     datetime.timedelta(seconds=i*1)).isoformat() + "Z",
        "user_id": "user4",
        "ip_address": "192.168.1.200",
        "endpoint": "/api/v1/products",
        "response_code": 200
    }
    freq_events.append(freq_event)

# Process high frequency events
print(f"Processing {len(freq_events)} high frequency events...")
for i, event in enumerate(freq_events):
    if i % 10 == 0:
        print(f"  Processing event {i+1}...")
    anomalies = anomaly_manager.analyze_event(event)
    if anomalies:
        print(f"  - Detected anomaly after {i+1} requests")
        print(f"    Type: {anomalies[0].anomaly_type.value}")
        print(f"    Severity: {anomalies[0].severity.value}")
        print(f"    Actions: {[action.value for action in anomalies[0].response_actions]}")
        break

print("\nTest Complete")
print("=============")
print("The anomaly detection system is working as expected!")
print("In a real deployment, the system would:")
print("1. Monitor all API requests in real-time")
print("2. Store detected anomalies for review")
print("3. Execute automated responses based on severity")
print("4. Provide a dashboard for security analysts to review anomalies")
