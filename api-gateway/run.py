#!/usr/bin/env python3
"""
TechSaaS Platform API Gateway - Entry Point Script

This script provides an entry point for running the API Gateway service.
"""

import os
import argparse
import logging
from app import create_app

def setup_argparse():
    """Set up command line argument parsing"""
    parser = argparse.ArgumentParser(description='TechSaaS API Gateway Service')
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=os.environ.get('API_GATEWAY_PORT', 5000),
        help='Port to run the API Gateway on (default: 5000 or API_GATEWAY_PORT env var)'
    )
    
    parser.add_argument(
        '--host', 
        type=str, 
        default='0.0.0.0',
        help='Host to bind the API Gateway to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Run in debug mode'
    )
    
    parser.add_argument(
        '--enable-discovery', 
        action='store_true',
        help='Enable service discovery'
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = setup_argparse()
    
    # Create the Flask app
    app = create_app()
    
    # Override config with command line arguments
    if args.enable_discovery:
        app.config['ENABLE_SERVICE_DISCOVERY'] = True
    
    # Configure logging based on debug mode
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # Run the app
    print(f"Starting API Gateway on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()
