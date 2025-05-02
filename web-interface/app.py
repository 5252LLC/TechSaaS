"""
TechSaaS Platform - Web Interface Service
Main web browser interface with integrated web browser and search capabilities
"""
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Initialize Flask app
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# Configuration
PORT = int(os.getenv('WEB_INTERFACE_PORT', 5252))
VIDEO_SCRAPER_URL = f"http://localhost:{os.getenv('VIDEO_SCRAPER_PORT', 5501)}"
API_GATEWAY_URL = f"http://localhost:{os.getenv('API_GATEWAY_PORT', 5000)}"

@app.route('/')
def index():
    """Web Interface home page"""
    return render_template('index.html')

@app.route('/browser')
def browser():
    """Web browser interface"""
    url = request.args.get('url', '')
    return render_template('browser.html', url=url)

@app.route('/video-scraper')
def video_scraper():
    """Video scraper interface"""
    return render_template('video-scraper.html')

@app.route('/api/search', methods=['POST'])
def search():
    """Search endpoint that processes search requests"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        search_engine = data.get('engine', 'google')
        
        # Placeholder for actual search implementation
        results = [
            {"title": "Sample Result 1", "url": "https://example.com/1", "snippet": "This is a sample search result"},
            {"title": "Sample Result 2", "url": "https://example.com/2", "snippet": "Another sample search result"}
        ]
        
        return jsonify({
            "query": query,
            "engine": search_engine,
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape_url():
    """Forward scraping request to video scraper service"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # In the actual implementation, this would make a request to the video scraper service
        # This is a placeholder
        return jsonify({
            "status": "initiated",
            "message": f"Scraping initiated for {url}",
            "job_id": "browser-initiated-job-12345"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def status():
    """Status endpoint for health checks"""
    return jsonify({
        "service": "TechSaaS Web Interface",
        "version": "1.0.0",
        "status": "operational"
    })

if __name__ == '__main__':
    print(f"Starting Web Interface service on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
