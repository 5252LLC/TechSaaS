"""
TechSaaS Platform - Video Scraper Service
Flask API wrapper for Hitomi-Downloader integration
"""
import os
import uuid
import json
import time
import threading
import sys
import logging
import shutil
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Make sure api directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Direct imports
from hitomi_wrapper import (
    extract_video, 
    get_job_status, 
    cancel_job, 
    get_supported_platforms,
    list_jobs,
    HitomiWrapper
)

# Load environment variables
load_dotenv(override=True)

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create Flask app
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

# Initialize the Hitomi Wrapper for enhanced extraction
hitomi_wrapper = HitomiWrapper()

# Configuration
PORT = int(os.getenv('VIDEO_SCRAPER_PORT', 5501))

# Define consistent download paths
# Use the video-scraper/downloads folder (more accessible to web server)
VIDEO_SCRAPER_DOWNLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads')
# Standardize on a single download directory
DOWNLOAD_DIR = VIDEO_SCRAPER_DOWNLOADS

# Update the global DOWNLOADS_PATH to match our standardized path
hitomi_wrapper.DOWNLOADS_PATH = DOWNLOAD_DIR

# Enable CORS
CORS(app)

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Copy existing files from other download locations to our standardized path
def migrate_downloads():
    # Paths to check for existing downloads
    paths_to_check = [
        "/home/fiftytwo/Desktop/52 codes/52TechSaas/downloads/",
        "/home/fiftytwo/Desktop/52 codes/52TechSaas/video-scraper/api/downloads/"
    ]
    
    for path in paths_to_check:
        if os.path.exists(path) and path != DOWNLOAD_DIR:
            try:
                for filename in os.listdir(path):
                    if filename.endswith(('.mp4', '.webm', '.mkv')):
                        source = os.path.join(path, filename)
                        destination = os.path.join(DOWNLOAD_DIR, filename)
                        if not os.path.exists(destination):
                            shutil.copy2(source, destination)
                            app.logger.info(f"Migrated file: {filename} from {path} to {DOWNLOAD_DIR}")
            except Exception as e:
                app.logger.error(f"Error migrating files from {path}: {str(e)}")

# Run migration on startup
migrate_downloads()

@app.route('/')
def index():
    """Video Scraper service main page"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """Status endpoint for health checks"""
    return jsonify({
        "service": "TechSaaS Video Scraper",
        "version": "1.0.0",
        "status": "operational"
    })

@app.route('/api/extract', methods=['POST'])
def extract_video_endpoint():
    """
    Extract video from provided URL using Hitomi-Downloader
    Expects JSON with video URL and optional parameters
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({"error": "URL is required"}), 400
            
        url = data.get('url')
        quality = data.get('quality', 'best')
        output_dir = data.get('output_dir', DOWNLOAD_DIR)
        
        # Use our hitomi_wrapper to extract the video
        result = extract_video(url, quality, output_dir)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/video-scraper/info', methods=['POST'])
def extract_info():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    # Basic URL validation
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return jsonify({"error": "Invalid URL format"}), 400
    
    # Check if platform is supported
    platforms = get_supported_platforms()
    domain = parsed_url.netloc.lower()
    if 'www.' in domain:
        domain = domain.replace('www.', '')
    
    # Check if domain matches any supported platform
    supported = False
    for platform in platforms:
        if platform['domain'] in domain or domain in platform['domain']:
            supported = True
            break
    
    if not supported:
        return jsonify({"error": f"Unsupported platform: {domain}"}), 400
    
    try:
        # Create an extraction job and return the job ID for tracking
        result = extract_video(url, quality="best", output_dir=DOWNLOAD_DIR)
        app.logger.info(f"Started extraction job: {result['job_id']} for URL: {url}")
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error extracting video info: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/video-scraper/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        hitomi_wrapper._check_yt_dlp_version()
        download_id = f"{int(time.time())}_{url.split('/')[-1]}"
        output_template = os.path.join(DOWNLOAD_DIR, f"{download_id}.%(ext)s")
        
        def download_task():
            try:
                result = hitomi_wrapper.download_video(url, format_id, output_template)
                app.logger.info(f"Download completed: {result}")
            except Exception as e:
                app.logger.error(f"Download task error: {str(e)}")
        
        thread = threading.Thread(target=download_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "download_started",
            "download_id": download_id,
            "message": "Download started in background. Check status with the download ID."
        })
    except Exception as e:
        app.logger.error(f"Error starting download: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/video-scraper/status/<download_id>', methods=['GET'])
def check_download_status(download_id):
    """Check the status of a background download"""
    try:
        # Look for files matching the download_id pattern
        files = os.listdir(DOWNLOAD_DIR)
        matching_files = [f for f in files if f.startswith(download_id)]
        
        if matching_files:
            file_path = os.path.join(DOWNLOAD_DIR, matching_files[0])
            file_size = os.path.getsize(file_path)
            return jsonify({
                "status": "complete",
                "file": matching_files[0],
                "file_size": file_size,
                "download_url": f"/downloads/{matching_files[0]}"
            })
        else:
            # Check if there are any in-progress downloads
            # This is a simplified check - in a real app, you'd track jobs in a database
            return jsonify({
                "status": "in_progress",
                "message": "Download still in progress or not found"
            })
    except Exception as e:
        app.logger.error(f"Error checking download status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/job/<job_id>', methods=['GET'])
def job_status(job_id):
    """
    Check status of a video extraction job
    """
    try:
        job_data = get_job_status(job_id)
        
        if not job_data:
            return jsonify({"error": "Job not found"}), 404
            
        # Handle completed jobs with result data
        if job_data.get("status") == "complete" and job_data.get("result"):
            # Check if the file exists
            if "filename" in job_data["result"]:
                file_path = job_data["result"]["filename"]
                base_file_name = os.path.basename(file_path)
                
                # Check for files with this base name in the downloads directory
                matching_files = []
                for file in os.listdir(DOWNLOAD_DIR):
                    if file.startswith(f"video_{job_id}"):
                        matching_files.append(file)
                
                if matching_files:
                    # Update the result with the actual filename including extension
                    job_data["result"]["filename"] = matching_files[0]
        
        return jsonify(job_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/job/<job_id>/cancel', methods=['POST'])
def cancel_job_endpoint(job_id):
    """
    Cancel a video extraction job
    """
    try:
        result = cancel_job(job_id)
        if not result:
            return jsonify({"error": "Job not found or already completed"}), 404
            
        return jsonify({"status": "cancelled", "job_id": job_id})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/video-scraper/supported-platforms', methods=['GET'])
def supported_platforms():
    """
    List all supported video platforms
    """
    try:
        platforms = get_supported_platforms()
        return jsonify(platforms)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/downloads/<path:filename>', methods=['GET'])
def download_file(filename):
    """
    Serve downloaded files
    """
    try:
        # Add debug logging
        app.logger.info(f"Request for file: {filename}")
        app.logger.info(f"Looking in directory: {DOWNLOAD_DIR}")
        
        # List files in the downloads directory
        files = os.listdir(DOWNLOAD_DIR)
        app.logger.info(f"Files in download directory: {files}")
        
        # Try to find a matching file (case insensitive)
        matching_files = [f for f in files if f.lower() == filename.lower()]
        if matching_files:
            return send_from_directory(DOWNLOAD_DIR, matching_files[0], as_attachment=True)
            
        # Try to find a file that starts with the job ID portion of the filename
        if filename.startswith('video_'):
            job_id = filename.split('.')[0].replace('video_', '')
            job_id_matches = [f for f in files if f.startswith(f'video_{job_id}')]
            if job_id_matches:
                return send_from_directory(DOWNLOAD_DIR, job_id_matches[0], as_attachment=True)
        
        return jsonify({"error": f"File not found: {filename}", "path": DOWNLOAD_DIR, "files": files}), 404
        
    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {str(e)}")
        return jsonify({"error": str(e), "path": DOWNLOAD_DIR, "files": os.listdir(DOWNLOAD_DIR)}), 404

if __name__ == "__main__":
    print(f"Starting Video Scraper API on port {PORT}")
    print(f"Download directory: {DOWNLOAD_DIR}")
    print("Press Ctrl+C to stop")
    app.run(host='0.0.0.0', port=PORT, debug=True)
