"""
TechSaaS Platform - API Gateway Service
Main API Gateway service that routes requests to appropriate microservices
"""
import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Initialize Flask app
app = Flask(__name__)

# Configuration
PORT = int(os.getenv('API_GATEWAY_PORT', 5000))
VIDEO_SCRAPER_URL = f"http://localhost:{os.getenv('VIDEO_SCRAPER_PORT', 5501)}"
WEB_INTERFACE_URL = f"http://localhost:{os.getenv('WEB_INTERFACE_PORT', 5252)}"
WEB_SCRAPER_URL = f"http://localhost:{os.getenv('WEB_SCRAPER_PORT', 5502)}"

@app.route('/')
def index():
    """Root endpoint that provides API documentation"""
    return jsonify({
        "service": "TechSaaS API Gateway",
        "version": "1.0.0",
        "endpoints": {
            "/api/video-scraper": "Video scraping service",
            "/api/web-interface": "Web browser interface",
            "/api/web-scraper": "Web content scraping service",
            "/api/ai": "AI analysis service"
        }
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({"status": "healthy"})

@app.route('/api/<path:service_path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_gateway(service_path):
    """
    Main gateway function that routes API requests to appropriate microservices
    based on the service path
    """
    try:
        # Route based on service path prefix
        if service_path.startswith('video-scraper'):
            # Forward to video scraper service
            target_url = f"{VIDEO_SCRAPER_URL}/{service_path.replace('video-scraper/', '', 1)}"
        elif service_path.startswith('web-interface'):
            # Forward to web interface service
            target_url = f"{WEB_INTERFACE_URL}/{service_path.replace('web-interface/', '', 1)}"
        elif service_path.startswith('web-scraper'):
            # Forward to web scraper service
            target_url = f"{WEB_SCRAPER_URL}/{service_path.replace('web-scraper/', '', 1)}"
        else:
            return jsonify({"error": "Invalid service path"}), 404
            
        # Implementation will forward requests to appropriate services
        # This is a placeholder for actual service forwarding logic
        return jsonify({
            "message": f"Request would be forwarded to {target_url}",
            "service_path": service_path,
            "method": request.method
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"Starting API Gateway service on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
