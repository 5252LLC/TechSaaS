#!/usr/bin/env python3
"""
TechSaaS Platform - Port Finder Utility
Automatically finds available ports for services
"""
import socket
import os
from contextlib import closing

def find_free_port(start_port=5000, max_attempts=100):
    """
    Find a free port starting from start_port
    
    Args:
        start_port (int): The port to start checking from
        max_attempts (int): Maximum number of ports to check
        
    Returns:
        int: An available port number
    """
    for port in range(start_port, start_port + max_attempts):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            if result != 0:  # Port is available
                return port
    
    raise RuntimeError(f"Could not find free port after {max_attempts} attempts starting from {start_port}")

def get_service_ports():
    """
    Get or generate ports for all services and update .env file
    
    Returns:
        dict: Dictionary with service names and their ports
    """
    # Default port ranges
    default_ports = {
        'API_GATEWAY_PORT': 5000,
        'VIDEO_SCRAPER_PORT': 5500,
        'WEB_INTERFACE_PORT': 5252,
        'WEB_SCRAPER_PORT': 5501,
        'AI_SERVICE_PORT': 5550
    }
    
    # Find available ports
    assigned_ports = {}
    used_ports = set()
    
    for env_var, default_port in default_ports.items():
        # Try to get port from environment or find a free one
        port = int(os.environ.get(env_var, default_port))
        
        # Check if port is already used by another service
        if port in used_ports:
            # Find next available port
            port = find_free_port(default_port + 1)
        
        # Check if port is free on the system
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:  # Port is in use
                port = find_free_port(default_port + 1)
        
        assigned_ports[env_var] = port
        used_ports.add(port)
        
        # Print status for debugging
        print(f"Assigned {env_var} to port {port}")
    
    return assigned_ports

def update_env_file(port_dict):
    """
    Update .env file with the new ports
    
    Args:
        port_dict (dict): Dictionary with environment variables and their values
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    # Read existing .env file if it exists
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Parse existing variables
    existing_vars = {}
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            existing_vars[key.strip()] = value.strip()
    
    # Update with new port values
    for key, value in port_dict.items():
        existing_vars[key] = str(value)
    
    # Write back to .env file
    with open(env_path, 'w') as f:
        for key, value in existing_vars.items():
            f.write(f"{key}={value}\n")
    
    return env_path

if __name__ == "__main__":
    # If run directly, find and update ports
    print("Finding available ports for services...")
    ports = get_service_ports()
    
    env_path = update_env_file(ports)
    
    print("Service ports configured:")
    for service, port in ports.items():
        print(f"  {service}: {port}")
    print(f"Configuration saved to {env_path}")
