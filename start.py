#!/usr/bin/env python3
"""
TechSaaS Platform - Startup Script
Centralized script to start all microservices
"""
import os
import sys
import subprocess
import argparse
import signal
import time
from dotenv import load_dotenv

# Add utils directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils'))
from port_finder import get_service_ports, update_env_file

def get_service_config():
    """Get service configuration with updated ports"""
    # Configure ports using automatic port finder
    service_ports = get_service_ports()
    update_env_file(service_ports)

    # Now load environment with updated ports
    load_dotenv(override=True)
    
    # Service configuration with updated ports
    return {
        'api-gateway': {
            'path': 'api-gateway',
            'command': 'python app.py',
            'port': os.getenv('API_GATEWAY_PORT', '5000'),
            'depends_on': []
        },
        'video-scraper': {
            'path': 'video-scraper/api',
            'command': 'python app.py',
            'port': os.getenv('VIDEO_SCRAPER_PORT', '5501'),
            'depends_on': ['api-gateway']
        },
        'web-interface': {
            'path': 'web-interface',
            'command': 'python app.py',
            'port': os.getenv('WEB_INTERFACE_PORT', '5252'),
            'depends_on': ['api-gateway']
        },
        'ai-service': {
            'path': 'ai-service',
            'command': 'python app.py',
            'port': os.getenv('AI_SERVICE_PORT', '5550'),
            'depends_on': []
        }
    }

# Process tracking
processes = {}

def start_service(service_name, SERVICES):
    """Start a specific service by name"""
    if service_name not in SERVICES:
        print(f"Error: Unknown service '{service_name}'")
        return False
        
    service = SERVICES[service_name]
    
    # Check dependencies
    for dependency in service['depends_on']:
        if dependency not in processes or not processes[dependency]:
            print(f"Starting dependency '{dependency}' for '{service_name}'...")
            if not start_service(dependency, SERVICES):
                print(f"Error: Failed to start dependency '{dependency}'")
                return False
    
    # Start the service
    try:
        print(f"Starting {service_name} on port {service['port']}...")
        # Modify command to include virtual environment activation
        activate_venv = "source venv/bin/activate && "
        full_command = activate_venv + service['command']
        
        process = subprocess.Popen(
            ["bash", "-c", full_command],  # Use bash to interpret the command string
            cwd=service['path'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        processes[service_name] = process
        print(f"Started {service_name} (PID: {process.pid})")
        return True
    except Exception as e:
        print(f"Error starting {service_name}: {str(e)}")
        return False

def stop_service(service_name, SERVICES=None):
    """Stop a specific service by name"""
    if service_name not in processes or not processes[service_name]:
        print(f"Service '{service_name}' is not running")
        return
        
    process = processes[service_name]
    try:
        print(f"Stopping {service_name} (PID: {process.pid})...")
        process.terminate()
        process.wait(timeout=5)
        processes[service_name] = None
    except subprocess.TimeoutExpired:
        print(f"Forcefully killing {service_name}...")
        process.kill()
        processes[service_name] = None

def stop_all_services():
    """Stop all running services"""
    for service_name in list(processes.keys()):
        if processes[service_name]:
            stop_service(service_name)

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully shut down services"""
    print("\nShutting down services...")
    stop_all_services()
    sys.exit(0)

def main():
    """Parse command line arguments and perform requested action"""
    parser = argparse.ArgumentParser(description='TechSaaS Platform Service Management')
    parser.add_argument('action', choices=['start', 'stop', 'restart'], help='Action to perform')
    parser.add_argument('--service', help='Specific service to manage')
    parser.add_argument('--all', action='store_true', help='Manage all services')
    
    args = parser.parse_args()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get the updated service configuration
    SERVICES = get_service_config()
    
    if args.action == 'start':
        if args.service:
            start_service(args.service, SERVICES)
        elif args.all:
            for service_name in SERVICES:
                start_service(service_name, SERVICES)
        else:
            parser.error("Either --service or --all must be specified")
            
        print("Services running. Press Ctrl+C to stop all services.")
        while True:
            time.sleep(1)
            
    elif args.action == 'restart':
        if args.service:
            stop_service(args.service)
            time.sleep(1)
            start_service(args.service, SERVICES)
        elif args.all:
            stop_all_services()
            time.sleep(1)
            for service_name in SERVICES:
                start_service(service_name, SERVICES)
        else:
            parser.error("Either --service or --all must be specified")
    
    elif args.action == 'stop':
        if args.service:
            stop_service(args.service)
        elif args.all:
            stop_all_services()
        else:
            parser.error("Either --service or --all must be specified")

if __name__ == '__main__':
    main()
