"""
Network Utilities

This module provides utility functions for network operations,
including validation and security checks.
"""

import re
import socket
import ipaddress
from urllib.parse import urlparse
from flask import current_app

def is_authorized_target(target):
    """
    Check if a target (IP, hostname, or URL) is authorized for scanning.
    Only allows scanning of specific allowed networks and domains.
    
    Args:
        target: String containing IP, hostname, or URL
        
    Returns:
        Boolean indicating if target is allowed
    """
    # Parse target if it's a URL
    if target.startswith(('http://', 'https://')):
        parsed = urlparse(target)
        target = parsed.netloc
    
    # Remove port if present
    if ':' in target and not re.match(r'^\[.*\]', target):
        target = target.split(':')[0]
    
    # Check if it's an IP address
    try:
        ip = ipaddress.ip_address(target)
        
        # Allow loopback addresses (for development)
        if ip.is_loopback:
            return True
            
        # Check allowed IP ranges from config
        allowed_ranges = current_app.config.get('PENTEST_ALLOWED_RANGES', [
            '127.0.0.0/8',      # Loopback
            '10.0.0.0/8',       # Private network
            '172.16.0.0/12',    # Private network
            '192.168.0.0/16',   # Private network
        ])
        
        for allowed_range in allowed_ranges:
            if ip in ipaddress.ip_network(allowed_range):
                return True
                
        return False
        
    except ValueError:
        # Check if it's a hostname
        try:
            ip = socket.gethostbyname(target)
            
            # Check if resolved IP is in allowed ranges
            ip_obj = ipaddress.ip_address(ip)
            
            # Allow loopback addresses (for development)
            if ip_obj.is_loopback:
                return True
                
            # Check allowed IP ranges
            allowed_ranges = current_app.config.get('PENTEST_ALLOWED_RANGES', [
                '127.0.0.0/8',      # Loopback
                '10.0.0.0/8',       # Private network
                '172.16.0.0/12',    # Private network
                '192.168.0.0/16',   # Private network
            ])
            
            for allowed_range in allowed_ranges:
                if ip_obj in ipaddress.ip_network(allowed_range):
                    return True
            
            # Additional allowed domains for testing
            allowed_domains = [
                'localhost',
                '127.0.0.1',
                'scanme.nmap.org',  # Nmap's test server
                'testphp.vulnweb.com',  # OWASP test site
                'httpbin.org',
                'example.com',
                'test-domain.local'
            ]
            
            # Check if hostname is in allowed list
            if target in allowed_domains:
                return True
                
            # Check if it's a subdomain of allowed domains
            for domain in allowed_domains:
                if target.endswith('.' + domain):
                    return True
                    
            return False
            
        except socket.gaierror:
            return False

def get_host_info(hostname):
    """
    Get detailed information about a hostname.
    
    Args:
        hostname: String hostname to lookup
        
    Returns:
        Dictionary with host information
    """
    info = {
        'hostname': hostname,
        'addresses': [],
        'error': None
    }
    
    try:
        # Get all IP addresses (both IPv4 and IPv6)
        addrinfo = socket.getaddrinfo(hostname, None)
        for addr in addrinfo:
            family, socktype, proto, canonname, sockaddr = addr
            if family == socket.AF_INET:  # IPv4
                ip = sockaddr[0]
                if ip not in info['addresses']:
                    info['addresses'].append(ip)
            elif family == socket.AF_INET6:  # IPv6
                ip = sockaddr[0]
                if ip not in info['addresses']:
                    info['addresses'].append(ip)
    except socket.gaierror as e:
        info['error'] = f"Could not resolve hostname: {str(e)}"
    
    return info
