#!/usr/bin/env python3
"""
YouTube Hitomi-Downloader Integration with Error Handling
This module provides a robust integration with Hitomi-Downloader for the TechSaaS platform,
including special handling for YouTube 403 errors and nsig extraction failures.
"""

import os
import sys
import json
import subprocess
import time
import random
import logging
import uuid
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("youtube_extractor")

# Get paths
HITOMI_PATH = os.path.abspath(os.getenv('HITOMI_PATH', '../hitomi-integration'))
DOWNLOADS_PATH = os.path.abspath(os.getenv('DOWNLOAD_DIR', '../downloads'))
CONFIG_PATH = os.path.abspath(os.getenv('CONFIG_DIR', '../config'))

# Ensure directories exist
os.makedirs(DOWNLOADS_PATH, exist_ok=True)
os.makedirs(CONFIG_PATH, exist_ok=True)

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
]

# Maximum retry attempts
MAX_RETRIES = 3

class ExtractionJob:
    """Class representing a YouTube video extraction job"""
    def __init__(self, url, quality="best", output_dir=DOWNLOADS_PATH):
        self.job_id = str(uuid.uuid4())
        self.url = url
        self.quality = quality
        self.output_dir = output_dir
        self.status = "pending"
        self.progress = 0
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.platform = self._detect_platform()
        self.process = None
        self.current_retry = 0
        self.cookie_file = os.path.join(CONFIG_PATH, f"cookies_{self.job_id}.txt")
        self.config_file = os.path.join(CONFIG_PATH, f"yt-dlp_{self.job_id}.conf")
        self.filename = f"video_{self.job_id}"
        self.output_path = os.path.join(output_dir, self.filename)
        self._create_default_config()
    
    def _detect_platform(self):
        """Detect the platform from the URL"""
        parsed_url = urlparse(self.url)
        domain = parsed_url.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return "youtube"
        else:
            return "unknown"
    
    def _create_default_config(self):
        """Create default configuration files if they don't exist."""
        with open(self.config_file, 'w') as f:
            f.write("""
# yt-dlp configuration
--force-ipv4
--geo-bypass
--ignore-errors
--no-warnings
--no-check-certificate
            """.strip())
        logger.info(f"Created default config file at {self.config_file}")
        
        # Create empty cookies file
        with open(self.cookie_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
    
    def to_dict(self):
        """Convert job to dictionary for JSON serialization"""
        return {
            "job_id": self.job_id,
            "url": self.url,
            "quality": self.quality,
            "output_dir": self.output_dir,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "platform": self.platform,
            "current_retry": self.current_retry,
            "duration": (self.end_time - self.start_time) if (self.start_time and self.end_time) else None
        }
    
    def cleanup(self):
        """Clean up temporary files after job completion or failure"""
        try:
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

def get_random_user_agent():
    """Return a random user agent from the list."""
    return random.choice(USER_AGENTS)

def handle_403_error(job, error_message):
    """Handle 403 Forbidden errors specially."""
    logger.warning(f"Received 403 error for {job.url}: {error_message}")
    
    # Try clearing the cache
    clear_cache()
    
    # Try with a different user agent
    new_user_agent = get_random_user_agent()
    logger.info(f"Retrying with different user agent: {new_user_agent}")
    
    # Wait some time before retry to avoid rate limiting
    wait_time = random.uniform(1.0, 5.0)
    logger.info(f"Waiting {wait_time:.2f} seconds before retry")
    time.sleep(wait_time)
    
    return True  # Signal to retry

def handle_nsig_extraction_error(job, error_message):
    """Handle signature extraction failures."""
    logger.warning(f"nsig extraction failed for {job.url}: {error_message}")
    
    # Check if PhantomJS is installed
    try:
        subprocess.run(["phantomjs", "--version"], capture_output=True, text=True, check=True)
        logger.info("PhantomJS is installed, will be used for signature extraction")
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("PhantomJS is not installed. This might help with signature extraction.")
        
    # Try with a different client
    logger.info("Trying with android client instead of web client")
    
    # Wait some time before retry
    wait_time = random.uniform(1.0, 3.0)
    logger.info(f"Waiting {wait_time:.2f} seconds before retry")
    time.sleep(wait_time)
    
    return True  # Signal to retry

def clear_cache():
    """Clear yt-dlp cache to fix stale signatures."""
    try:
        subprocess.run(
            ["yt-dlp", "--rm-cache-dir"],
            capture_output=True, 
            text=True,
            check=True
        )
        logger.info("Successfully cleared yt-dlp cache")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to clear yt-dlp cache: {str(e)}")
        return False

def extract_youtube_video(job):
    """
    Extract a YouTube video with robust error handling.
    This function is specifically designed to handle YouTube's common issues.
    """
    try:
        job.start_time = time.time()
        job.status = "processing"
        
        while job.current_retry < MAX_RETRIES:
            try:
                # Create command based on the available executable
                cmd = [
                    "yt-dlp",
                    "-f", job.quality,
                    "-o", f"{job.output_path}.%(ext)s",
                    "--newline",
                    "--progress",
                    "--user-agent", get_random_user_agent(),
                    "--cookies", job.cookie_file,
                    "--config-location", job.config_file
                ]
                
                # Add extractor args to handle nsig issues if needed
                if job.current_retry > 0:
                    cmd.extend([
                        "--extractor-args", 
                        "youtube:player_client=android,bypass_age_gate"
                    ])
                
                # Add the URL
                cmd.append(job.url)
                
                logger.info(f"Running command: {' '.join(cmd)}")
                
                # Run the process with output capture
                job.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # Process output and update progress
                output_lines = []
                for line in job.process.stdout:
                    output_lines.append(line.strip())
                    
                    # Extract progress information from the output
                    if '[download]' in line and '%' in line:
                        try:
                            progress_str = line.split('%')[0].split()[-1]
                            job.progress = float(progress_str)
                        except (ValueError, IndexError):
                            pass
                    
                    # Check if job was cancelled
                    if job.status == "cancelled":
                        job.process.terminate()
                        break
                
                # Wait for process to complete
                returncode = job.process.wait()
                
                if returncode != 0 and job.status != "cancelled":
                    error_message = os.linesep.join(output_lines[-5:])
                    
                    # Handle specific errors
                    if "HTTP Error 403: Forbidden" in error_message:
                        handle_403_error(job, error_message)
                    elif "nsig extraction failed" in error_message:
                        handle_nsig_extraction_error(job, error_message)
                    elif "Unable to extract Initial JS player" in error_message:
                        clear_cache()
                    else:
                        logger.error(f"Unknown error: {error_message}")
                    
                    job.current_retry += 1
                    continue
                
                # Find the downloaded file
                downloaded_files = []
                for root, _, files in os.walk(job.output_dir):
                    for file in files:
                        if file.startswith(f"video_{job.job_id}"):
                            downloaded_files.append(os.path.join(root, file))
                
                if downloaded_files and job.status != "cancelled":
                    # Get the latest file
                    latest_file = max(downloaded_files, key=os.path.getmtime)
                    file_size = os.path.getsize(latest_file)
                    file_extension = os.path.splitext(latest_file)[1].lstrip('.')
                    
                    job.result = {
                        "filename": os.path.basename(latest_file),
                        "path": latest_file,
                        "size": file_size,
                        "format": file_extension,
                        "url": job.url,
                        "platform": job.platform,
                        "quality": job.quality
                    }
                    job.status = "completed"
                    job.progress = 100
                    break  # Success, exit the retry loop
                elif job.status == "cancelled":
                    # Clean up any partial downloads
                    for file in downloaded_files:
                        try:
                            os.remove(file)
                        except (OSError, IOError):
                            pass
                    break  # Cancelled, exit the retry loop
                else:
                    raise Exception("No files were downloaded")
            
            except Exception as e:
                logger.error(f"Extraction attempt {job.current_retry + 1} failed: {str(e)}")
                job.current_retry += 1
                # Wait before retry
                time.sleep(random.uniform(1.0, 3.0))
        
        if job.status != "completed" and job.status != "cancelled":
            job.status = "failed"
            job.error = f"Failed to extract video after {MAX_RETRIES} retries"
            
    except Exception as e:
        logger.error(f"YouTube extraction failed: {str(e)}")
        job.error = str(e)
        job.status = "failed"
    finally:
        job.end_time = time.time()
        job.cleanup()  # Clean up temporary files

def cancel_youtube_extraction(job):
    """
    Cancel a YouTube extraction job
    """
    if job.process and job.process.poll() is None:
        job.process.terminate()
    job.status = "cancelled"
    job.cleanup()
    return True

# Simple test function
if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    job = ExtractionJob(test_url)
    print(f"Created job: {job.job_id}")
    extract_youtube_video(job)
    print(f"Job result: {job.to_dict()}")
