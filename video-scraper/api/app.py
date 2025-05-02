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

@app.route('/video-scraper')
def video_scraper_page():
    """
    Main video scraper page
    """
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

@app.route('/api/extract', methods=['POST'])
def extract_video_new_endpoint():
    """
    Extract video from URL - New endpoint aligned with frontend JS
    """
    data = request.json
    
    if not data or 'url' not in data:
        return jsonify({"error": "URL is required"}), 400
    
    url = data.get('url')
    quality = data.get('quality', 'best')
    
    # Basic URL validation
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return jsonify({"error": "Invalid URL format"}), 400
    
    try:
        # Use the existing extraction function
        result = extract_video(url, quality=quality, output_dir=DOWNLOAD_DIR)
        app.logger.info(f"Started extraction job: {result['job_id']} for URL: {url}")
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error starting video extraction: {str(e)}")
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

@app.route('/api/video-scraper/platforms')
def platforms():
    """
    Alias for supported_platforms to match test expectations
    """
    return supported_platforms()

@app.route('/api/video-scraper/job/<job_id>')
def job_status_endpoint(job_id):
    """
    Check status of a video extraction job
    New endpoint to match test expectations
    """
    try:
        job_status_data = get_job_status(job_id)
        return jsonify(job_status_data)
    except Exception as e:
        app.logger.error(f"Error checking job status: {str(e)}")
        return jsonify({"error": str(e), "status": "failed"}), 500

@app.route('/api/video-scraper/downloads')
def downloads_endpoint():
    """
    List all available downloads in the format expected by tests
    """
    try:
        # Get the raw downloads data from the original function
        download_data = list_downloads()
        
        # Transform this into a simple array format expected by tests
        result = []
        
        # If we have a dictionary with 'files' key, use that array
        if isinstance(download_data, dict) and 'files' in download_data:
            file_list = download_data['files']
            file_details = download_data.get('fileDetails', {})
            
            # Convert to the expected format
            for filename in file_list:
                file_info = {
                    "filename": filename,
                    "url": f"/api/video-scraper/download/{filename}"
                }
                
                # Add file size if available
                if filename in file_details and 'size' in file_details[filename]:
                    file_info["size_bytes"] = file_details[filename]['size']
                    
                # Add creation time if available
                if filename in file_details and 'ctime' in file_details[filename]:
                    time_obj = file_details[filename]['ctime']
                    file_info["created"] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time_obj))
                    
                result.append(file_info)
        elif isinstance(download_data, list):
            # If it's already a list, use it directly
            result = download_data
        else:
            # Fallback to empty array
            result = []
            
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error listing downloads: {str(e)}")
        # Return an empty list on error rather than error message
        return jsonify([])

@app.route('/api/video-scraper/download-file/<path:filename>', methods=['GET'])
def download_video_file(filename):
    """
    Serve downloaded video files with proper content-disposition headers
    """
    try:
        app.logger.info(f"Download request for file: {filename}")
        
        # List files in the downloads directory
        files = os.listdir(DOWNLOAD_DIR)
        
        # Exact match first
        if filename in files:
            return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
            
        # Case-insensitive match
        matching_files = [f for f in files if f.lower() == filename.lower()]
        if matching_files:
            return send_from_directory(DOWNLOAD_DIR, matching_files[0], as_attachment=True)
            
        # Job ID match (for video_UUID.ext format)
        if filename.startswith('video_'):
            job_id = filename.split('.')[0].replace('video_', '')
            job_id_matches = [f for f in files if f.startswith(f'video_{job_id}')]
            if job_id_matches:
                return send_from_directory(DOWNLOAD_DIR, job_id_matches[0], as_attachment=True)
                
        # If no match was found, return a helpful error
        app.logger.error(f"File not found: {filename}")
        app.logger.info(f"Available files: {files}")
        return jsonify({
            "error": f"File not found: {filename}",
            "available_files": files
        }), 404
        
    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {str(e)}")
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
        app.logger.debug(f"Files in download directory: {files}")
        
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

@app.route('/api/video-scraper/check-file/<path:filename>', methods=['GET'])
def check_file_exists(filename):
    """
    Check if a file exists before attempting to download it
    Returns the actual filename if found through any matching method
    """
    try:
        app.logger.info(f"Checking if file exists: {filename}")
        
        # List files in the downloads directory
        files = os.listdir(DOWNLOAD_DIR)
        
        # Exact match
        if filename in files:
            return jsonify({"exists": True, "filename": filename})
            
        # Case-insensitive match
        matching_files = [f for f in files if f.lower() == filename.lower()]
        if matching_files:
            return jsonify({"exists": True, "filename": matching_files[0]})
            
        # Job ID match (for video_UUID.ext format)
        if filename.startswith('video_'):
            # Extract job ID from filename
            job_id = filename.split('.')[0].replace('video_', '')
            job_id_matches = [f for f in files if f.startswith(f'video_{job_id}')]
            if job_id_matches:
                return jsonify({"exists": True, "filename": job_id_matches[0]})
                
        # Try to find any recently downloaded file with similar job ID pattern
        # This handles cases where the extension might be different or missing
        if '_' in filename:
            file_parts = filename.split('_', 1)
            if len(file_parts) > 1:
                partial_id = file_parts[1].split('.')[0]
                partial_matches = [f for f in files if partial_id in f]
                if partial_matches:
                    app.logger.info(f"Found partial match: {partial_matches[0]} for {filename}")
                    return jsonify({"exists": True, "filename": partial_matches[0]})
        
        # No match found
        app.logger.warning(f"No matching file found for: {filename}")
        return jsonify({"exists": False, "available_files": files[:10]}), 404
        
    except Exception as e:
        app.logger.error(f"Error checking file {filename}: {str(e)}")
        return jsonify({"error": str(e), "exists": False}), 500

@app.route('/api/video-scraper/list-downloads', methods=['GET'])
def list_downloads():
    """
    List all available downloads with file metadata to help find matches
    """
    try:
        # Get all files in the downloads directory
        files = os.listdir(DOWNLOAD_DIR)
        
        # Filter to only include video files
        video_files = [f for f in files if f.endswith(('.mp4', '.webm', '.mkv', '.avi', '.mov'))]
        
        # Get detailed file information
        file_details = {}
        for file in video_files:
            file_path = os.path.join(DOWNLOAD_DIR, file)
            if os.path.isfile(file_path):
                stats = os.stat(file_path)
                file_details[file] = {
                    'size': stats.st_size,
                    'mtime': stats.st_mtime,
                    'ctime': stats.st_ctime
                }
        
        # Sort files by modification time (newest first)
        sorted_files = sorted(video_files, 
                             key=lambda f: file_details.get(f, {}).get('mtime', 0),
                             reverse=True)
        
        return jsonify({
            "files": sorted_files,
            "fileDetails": file_details,
            "count": len(sorted_files),
            "downloadDir": DOWNLOAD_DIR
        })
        
    except Exception as e:
        app.logger.error(f"Error listing downloads: {str(e)}")
        return jsonify({"error": str(e), "files": []}), 500

@app.route('/api/video-scraper/search')
def search_videos():
    """
    Search for videos across platforms
    """
    query = request.args.get('q')
    platform = request.args.get('platform', 'youtube')
    
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    
    try:
        # In a production environment, this would call an actual search API
        # For now, we're generating relevant results based on the search query
        app.logger.info(f"Searching for '{query}' on platform: {platform}")
        
        # Create dynamic results based on the search query
        results = []
        
        # Create more relevant results based on the query
        if platform == 'youtube' or platform == 'all':
            results.extend([
                {
                    "id": f"vid-{hash(query)}-1",
                    "title": f"{query} - Top Video Results",
                    "thumbnail": f"https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "duration": "3:45",
                    "platform": "youtube",
                    "uploader": "YouTube Creator",
                    "date": "2025-04-15"
                },
                {
                    "id": f"vid-{hash(query)}-2",
                    "title": f"Best of {query} Compilation 2025",
                    "thumbnail": "https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg",
                    "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                    "duration": "4:20",
                    "platform": "youtube",
                    "uploader": "Trending Videos",
                    "date": "2025-03-22"
                },
                {
                    "id": f"vid-{hash(query)}-3",
                    "title": f"How to: {query} Tutorial",
                    "thumbnail": "https://i.ytimg.com/vi/LXb3EKWsInQ/hqdefault.jpg",
                    "url": "https://www.youtube.com/watch?v=LXb3EKWsInQ",
                    "duration": "10:15",
                    "platform": "youtube",
                    "uploader": "Tutorial Expert",
                    "date": "2025-02-11"
                }
            ])
        
        if platform == 'vimeo' or platform == 'all':
            results.extend([
                {
                    "id": f"vimeo-{hash(query)}-1",
                    "title": f"Professional {query} - HD Video",
                    "thumbnail": "https://i.vimeocdn.com/video/548367049-0e7f148bad7186add28d992d529a6464c379442799d09c7ab7f2e3216b35568f-d_640",
                    "url": "https://vimeo.com/148751763",
                    "duration": "5:30",
                    "platform": "vimeo",
                    "uploader": "Vimeo Filmmaker",
                    "date": "2025-05-01"
                },
                {
                    "id": f"vimeo-{hash(query)}-2",
                    "title": f"{query} - Cinematic Sequence",
                    "thumbnail": "https://i.vimeocdn.com/video/590587169-4d5f9907e2fa49dadf8df897d4579df883b0478b283acd12e3343a23ddf657c3-d_640",
                    "url": "https://vimeo.com/174312494",
                    "duration": "2:45",
                    "platform": "vimeo",
                    "uploader": "Visual Artist",
                    "date": "2025-04-20"
                }
            ])
            
        # Add a search-specific note to explain these are sample results
        for result in results:
            result["title"] = result["title"].replace("{query}", query)
            
        return jsonify({
            "query": query,
            "platform": platform,
            "results": results,
            "note": "These are sample results. In a production environment, this would use the platform's actual search API."
        })
    except Exception as e:
        app.logger.error(f"Error searching videos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/browser')
def browser():
    """
    Web Browser Interface (placeholder)
    This will be expanded in a future task but ensures link works now
    """
    return render_template('browser.html')

if __name__ == "__main__":
    print(f"Starting Video Scraper API on port {PORT}")
    print(f"Download directory: {DOWNLOAD_DIR}")
    print("Press Ctrl+C to stop")
    app.run(host='0.0.0.0', port=PORT, debug=True)
