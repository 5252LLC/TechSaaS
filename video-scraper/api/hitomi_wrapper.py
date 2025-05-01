#!/usr/bin/env python3
"""
TechSaaS Platform - Hitomi-Downloader Integration Wrapper
This module provides a simplified interface to Hitomi-Downloader's extraction capabilities
"""
import os
import sys
import json
import re
import importlib
import logging
import uuid
from urllib.parse import urlparse
import time
import threading
import subprocess
import shutil
import requests
import random

# Import YouTube-specific extractor for specialized handling
from youtube_extractor import (
    ExtractionJob as YouTubeExtractionJob,
    extract_youtube_video,
    cancel_youtube_extraction
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("hitomi_wrapper")

# Constants for extraction settings
MAX_RETRIES = 3
# Use a relative path that will be updated by app.py
DOWNLOADS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads')
# Create the downloads directory if it doesn't exist
os.makedirs(DOWNLOADS_PATH, exist_ok=True)

# Get Hitomi-Downloader path from environment or use default
HITOMI_PATH = os.path.abspath(os.getenv('HITOMI_PATH', '../hitomi-integration'))
HITOMI_SRC_PATH = os.path.join(HITOMI_PATH, 'src')

# Dictionary to store all active extraction jobs
active_jobs = {}

# Create a map of domains to known video platforms
DOMAIN_PLATFORM_MAP = {
    'youtube.com': 'youtube',
    'youtu.be': 'youtube',
    'vimeo.com': 'vimeo',
    'dailymotion.com': 'dailymotion',
    'twitch.tv': 'twitch',
    'tiktok.com': 'tiktok',
    'twitter.com': 'twitter',
    'xvideos.com': 'xvideos',
    'pornhub.com': 'pornhub',
    'xhamster.com': 'xhamster',
    'soundcloud.com': 'soundcloud',
    # Add more mappings as needed
}

class ExtractionJob:
    """
    Class representing a video extraction job
    """
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
        self.thread = None
        self.process = None
        # Store filename without extension so yt-dlp can add the appropriate one
        self.filename = f"video_{self.job_id}"
        self.output_path = os.path.join(output_dir, self.filename)
    
    def _detect_platform(self):
        """Detect the platform from the URL"""
        parsed_url = urlparse(self.url)
        domain = parsed_url.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Check for exact domain match
        if domain in DOMAIN_PLATFORM_MAP:
            return DOMAIN_PLATFORM_MAP[domain]
        
        # Check for partial domain match
        for known_domain, platform in DOMAIN_PLATFORM_MAP.items():
            if known_domain in domain:
                return platform
        
        # Fall back to generic
        return "generic"
    
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
            "duration": (self.end_time - self.start_time) if (self.start_time and self.end_time) else None
        }

def check_hitomi_executable():
    """Check if the Hitomi-Downloader executable is available"""
    hitomi_exe = os.path.join(HITOMI_PATH, 'Hitomi Downloader.exe')
    if os.path.exists(hitomi_exe):
        return hitomi_exe
    
    # On Linux/Mac, check for Python scripts
    hitomi_py = os.path.join(HITOMI_SRC_PATH, 'hitomi_downloader.py')
    if os.path.exists(hitomi_py):
        return hitomi_py
    
    # Check for yt-dlp as a fallback
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        return 'yt-dlp'
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Neither Hitomi-Downloader nor yt-dlp found. Trying to install yt-dlp...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], check=True)
            return 'yt-dlp'
        except subprocess.SubprocessError:
            logger.error("Failed to install yt-dlp")
            return None

def extraction_worker(job):
    """
    Worker function that runs in a separate thread to handle extraction
    
    Args:
        job (ExtractionJob): Job to process
    """
    # Set job status to running
    job.status = "running"
    job.start_time = time.time()
    
    try:
        # Get Hitomi-Downloader executable path
        hitomi_exe = check_hitomi_executable()
        
        # Prepare download directory
        os.makedirs(job.output_dir, exist_ok=True)
        
        # Create command based on the available executable
        if hitomi_exe == 'yt-dlp':
            # Use yt-dlp directly
            # Remove any existing extension from the output path to avoid duplicates
            output_base = os.path.splitext(job.output_path)[0]
            cmd = [
                'yt-dlp',
                '-f', job.quality,
                # Use absolute path and let yt-dlp add the appropriate extension
                '-o', f'{output_base}.%(ext)s',
                '--newline',
                '--progress',
                job.url
            ]
        else:
            # Use Hitomi-Downloader executable
            cmd = [
                sys.executable,
                hitomi_exe,
                '--url', job.url,
                '--output', job.output_path,
                '--quality', job.quality,
                '--no-gui'
            ]
            
        # Log the command for debugging
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Run the command and capture output
        job.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor output for progress information
        output_file = None
        for line in job.process.stdout:
            # Parse progress information
            if "[download]" in line and "%" in line:
                try:
                    # Extract progress percentage
                    progress_text = line.split("%")[0].split()[-1]
                    job.progress = float(progress_text)
                except:
                    pass
                    
            # Check for destination file
            if "[download] Destination:" in line:
                output_file = line.split("[download] Destination:")[1].strip()
                
        # Wait for process to complete
        job.process.wait()
        
        # Check if process completed successfully
        if job.process.returncode == 0:
            job.status = "complete"
            job.progress = 100
            job.end_time = time.time()
            
            # Find the actual downloaded file
            base_filename = os.path.basename(job.output_path)
            matching_files = []
            for file in os.listdir(job.output_dir):
                if file.startswith(base_filename) and not file.endswith(".part"):
                    matching_files.append(file)
            
            if matching_files:
                actual_filename = matching_files[0]
                
                # Set the result with the actual filename including extension
                job.result = {
                    "filename": actual_filename,
                    "path": os.path.join(job.output_dir, actual_filename),
                    "url": job.url,
                    "quality": job.quality
                }
            else:
                # Use the provided output_file if we found it in the output
                if output_file:
                    actual_filename = os.path.basename(output_file)
                    job.result = {
                        "filename": actual_filename,
                        "path": output_file,
                        "url": job.url,
                        "quality": job.quality
                    }
                else:
                    # Fallback if we can't determine the actual file
                    job.result = {
                        "filename": f"{base_filename}.mp4",
                        "path": f"{job.output_path}.mp4",
                        "url": job.url,
                        "quality": job.quality
                    }
        else:
            # Process failed
            job.status = "failed"
            job.error = job.process.stderr.read()
            logger.error(f"Extraction failed: {job.error}")
    except Exception as e:
        # Handle unexpected errors
        job.status = "failed"
        job.error = str(e)
        logger.error(f"Extraction error: {str(e)}")
        
    # Clean up
    job.process = None

def extract_video(url, quality="best", output_dir=DOWNLOADS_PATH):
    """
    Extract video from the given URL
    
    Args:
        url (str): URL of the video to extract
        quality (str): Quality level to extract (best, 1080p, 720p, etc.)
        output_dir (str): Directory to save the extracted video
        
    Returns:
        dict: Job information including job_id for status tracking
    """
    # Create job
    if 'youtube.com' in url or 'youtu.be' in url:
        job = YouTubeExtractionJob(url, quality, output_dir)
    else:
        job = ExtractionJob(url, quality, output_dir)
        
    # Store in global jobs dictionary
    job_id = job.job_id
    active_jobs[job_id] = job
    
    # Start extraction in separate thread
    job.thread = threading.Thread(
        target=extraction_worker,
        args=(job,),
        daemon=True
    )
    job.thread.start()
    
    # Return job ID for status tracking
    return {
        "job_id": job_id,
        "status": job.status,
        "message": "Video extraction started"
    }

def get_job_status(job_id):
    """
    Get the status of an extraction job
    
    Args:
        job_id (str): ID of the job to check
        
    Returns:
        dict: Current job status and details or None if job not found
    """
    if job_id not in active_jobs:
        return None
    
    job = active_jobs[job_id]
    return job.to_dict()

def cancel_job(job_id):
    """
    Cancel an extraction job
    
    Args:
        job_id (str): ID of the job to cancel
        
    Returns:
        bool: True if job was cancelled, False otherwise
    """
    if job_id not in active_jobs:
        return False
    
    job = active_jobs[job_id]
    
    # Use specialized cancellation for YouTube jobs
    if hasattr(job, 'platform') and job.platform == 'youtube':
        return cancel_youtube_extraction(job)
    
    # Standard cancellation for other jobs
    job.status = "cancelled"
    
    # Terminate the process if running
    if job.process and job.process.poll() is None:
        job.process.terminate()
    
    return True

def list_jobs():
    """
    Get a list of all active extraction jobs
    
    Returns:
        list: List of job IDs and their basic status
    """
    return [{"job_id": job_id, "status": job.status, "url": job.url} for job_id, job in active_jobs.items()]

def get_supported_platforms():
    """
    Get a list of supported video platforms
    
    Returns:
        list: List of supported platforms and their details
    """
    platforms = [
        {"name": "YouTube", "domain": "youtube.com", "platform": "youtube"},
        {"name": "Vimeo", "domain": "vimeo.com", "platform": "vimeo"},
        {"name": "Dailymotion", "domain": "dailymotion.com", "platform": "dailymotion"},
        {"name": "Twitch", "domain": "twitch.tv", "platform": "twitch"},
        {"name": "TikTok", "domain": "tiktok.com", "platform": "tiktok"},
        {"name": "Twitter", "domain": "twitter.com", "platform": "twitter"},
        {"name": "SoundCloud", "domain": "soundcloud.com", "platform": "soundcloud"},
        {"name": "PornHub", "domain": "pornhub.com", "platform": "pornhub"},
        {"name": "XVideos", "domain": "xvideos.com", "platform": "xvideos"},
        {"name": "XHamster", "domain": "xhamster.com", "platform": "xhamster"},
        # Add more platforms as needed
    ]
    
    return platforms

class HitomiWrapper:
    def __init__(self):
        self.download_path = DOWNLOADS_PATH
        self.cookie_file = os.path.join(self.download_path, 'cookies.txt')
        self.config_file = os.path.join(self.download_path, 'config.txt')
        self.current_retry = 0
        
        # Ensure download directory exists
        os.makedirs(self.download_path, exist_ok=True)
        
        # Create config and cookie files if they don't exist
        self._create_default_config()
        if not os.path.exists(self.cookie_file):
            self._create_cookies_file()

    def _create_default_config(self):
        """Create a default yt-dlp config file if it doesn't exist."""
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w') as f:
                f.write("# yt-dlp config file\n")
                f.write("--no-mtime\n")
                f.write("--no-warnings\n")
                f.write("--no-check-certificate\n")
                f.write("--prefer-ffmpeg\n")
                f.write("--write-thumbnail\n")
            logger.info(f"Created default config file at {self.config_file}")

    def _create_cookies_file(self, cookies_dict=None):
        """Create a cookies file for yt-dlp."""
        if cookies_dict is None:
            cookies_dict = {
                ".youtube.com": {
                    "CONSENT": "YES+cb.20210418-17-p0.en+FX+410",
                }
            }
        
        with open(self.cookie_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for domain, cookies in cookies_dict.items():
                for name, value in cookies.items():
                    # Domain, flag, path, secure, expiration, name, value
                    f.write(f"{domain}\tTRUE\t/\tFALSE\t{int(time.time()) + 3600*24*365}\t{name}\t{value}\n")
        logger.info(f"Created cookies file at {self.cookie_file}")

    def _get_random_user_agent(self):
        """Get a random user agent to avoid blocking."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        ]
        return random.choice(user_agents)
        
    def _clear_cache(self):
        """Clear yt-dlp cache to avoid stale data issues."""
        cache_dir = os.path.expanduser("~/.cache/yt-dlp")
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                logger.info("Cleared yt-dlp cache")
                return True
            except Exception as e:
                logger.error(f"Failed to clear cache: {str(e)}")
        return False
        
    def _handle_403_error(self, url, error_output):
        """Handle 403 forbidden errors by clearing cache and cookies."""
        logger.info("Handling 403 error")
        self._clear_cache()
        # Wait with jitter to avoid detection
        time.sleep(random.uniform(2.0, 5.0))
        return True
        
    def _handle_nsig_extraction_error(self, url, error_output):
        """Handle nsig extraction failures by trying alternative approaches."""
        logger.info("Handling nsig extraction error")
        # Clear cache
        self._clear_cache()
        # Use different user-agent next time
        time.sleep(random.uniform(1.5, 4.0))
        return True

    def _check_yt_dlp_version(self) -> bool:
        """Check if yt-dlp is installed and updated."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            logger.info(f"yt-dlp version: {version}")
            # Check if version is recent (adjust based on latest release)
            if version < "2023.12.30":
                logger.warning("yt-dlp is outdated. Updating...")
                subprocess.run(["pip", "install", "-U", "yt-dlp"], check=True)
                logger.info("yt-dlp updated successfully")
            return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"yt-dlp not installed or inaccessible: {str(e)}")
            raise Exception("yt-dlp is required. Install with: pip install yt-dlp")

    def _configure_proxy(self, proxy_list: list = None) -> str:
        """Select a proxy from a list or return None if no proxies are available."""
        if not proxy_list:
            proxy_list = [
                # Add your proxy URLs here (e.g., from a proxy service)
                # "http://proxy1:port",
                # "http://proxy2:port",
            ]
        if proxy_list:
            proxy = random.choice(proxy_list)
            logger.info(f"Using proxy: {proxy}")
            return proxy
        logger.warning("No proxies configured. Consider adding proxies for rate-limiting issues.")
        return None

    def _refresh_cookies(self, youtube_url: str) -> bool:
        """Attempt to fetch fresh cookies for YouTube using a simple request."""
        try:
            headers = {"User-Agent": self._get_random_user_agent()}
            response = requests.get("https://www.youtube.com", headers=headers, timeout=10)
            if response.status_code == 200:
                cookies_dict = {
                    ".youtube.com": {
                        "CONSENT": "YES+cb.20210418-17-p0.en+FX+410",
                        # Add other cookies if needed (e.g., SESSION_TOKEN)
                        # Extract from response.cookies if available
                    }
                }
                for cookie in response.cookies:
                    cookies_dict.setdefault(".youtube.com", {})[cookie.name] = cookie.value
                self._create_cookies_file(cookies_dict)
                logger.info("Refreshed cookies successfully")
                return True
            else:
                logger.warning(f"Failed to fetch cookies: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error refreshing cookies: {str(e)}")
            return False

    def _get_alternative_formats(self, url: str) -> list:
        """Get a list of available video formats as a fallback."""
        try:
            cmd = [
                "yt-dlp",
                "-F",
                "--no-playlist",
                "--user-agent", self._get_random_user_agent(),
                "--cookies", self.cookie_file,
                "--config-location", self.config_file,
                url
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            formats = []
            for line in result.stdout.splitlines():
                if "mp4" in line and "video" in line:  # Prioritize mp4 video formats
                    format_id = line.split()[0]
                    if format_id.isdigit():
                        formats.append(format_id)
            logger.info(f"Available formats: {formats}")
            return formats
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to get formats: {str(e)}")
            return []

    def _parse_yt_dlp_error(self, error_output: str) -> dict:
        """Parse yt-dlp error output to determine retry strategy."""
        error_flags = {
            "is_403": "HTTP Error 403: Forbidden" in error_output,
            "is_nsig": "nsig extraction failed" in error_output,
            "is_unavailable": "Video unavailable" in error_output or "This video is not available" in error_output,
            "is_rate_limit": "Too Many Requests" in error_output or "429" in error_output,
        }
        logger.debug(f"Error flags: {error_flags}")
        return error_flags

    def extract_video_info(self, url: str) -> dict:
        """Updated extract_video_info with new features."""
        self._check_yt_dlp_version()  # Ensure yt-dlp is ready
        self.current_retry = 0
        proxy = self._configure_proxy()
        
        while self.current_retry < 3:
            try:
                cmd = [
                    "yt-dlp",
                    "--dump-json",
                    "--no-playlist",
                    "--user-agent", self._get_random_user_agent(),
                    "--cookies", self.cookie_file,
                    "--config-location", self.config_file,
                ]
                if proxy:
                    cmd.extend(["--proxy", proxy])
                if self.current_retry > 0:
                    cmd.extend(["--extractor-args", "youtube:player_client=android,bypass_age_gate"])
                cmd.append(url)

                logger.info(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                video_info = json.loads(result.stdout)
                return {
                    "id": video_info.get("id"),
                    "title": video_info.get("title"),
                    "description": video_info.get("description"),
                    "duration": video_info.get("duration"),
                    "thumbnail": video_info.get("thumbnail"),
                    "uploader": video_info.get("uploader"),
                    "formats": [
                        {
                            "format_id": f.get("format_id"),
                            "format": f.get("format"),
                            "ext": f.get("ext"),
                            "resolution": f.get("resolution"),
                            "filesize": f.get("filesize"),
                            "vcodec": f.get("vcodec"),
                            "acodec": f.get("acodec")
                        }
                        for f in video_info.get("formats", [])
                        if f.get("format_id")
                    ]
                }
            except subprocess.CalledProcessError as e:
                error_output = e.stderr
                logger.error(f"Extraction error (attempt {self.current_retry+1}/3): {error_output}")
                error_flags = self._parse_yt_dlp_error(error_output)

                if error_flags["is_unavailable"]:
                    raise Exception("Video is unavailable or restricted")
                if error_flags["is_403"] or error_flags["is_rate_limit"]:
                    self._handle_403_error(url, error_output)
                    self._refresh_cookies(url)  # Try refreshing cookies
                    proxy = self._configure_proxy()  # Try a different proxy
                elif error_flags["is_nsig"]:
                    self._handle_nsig_extraction_error(url, error_output)
                else:
                    self._clear_cache()
                    time.sleep(random.uniform(1.0, 3.0))

                self.current_retry += 1
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                self.current_retry += 1

        raise Exception(f"Failed to extract video info after 3 retries")

    def download_video(self, url: str, format_id: str = None, output_template: str = None) -> dict:
        """Updated download_video with new features."""
        self._check_yt_dlp_version()
        self.current_retry = 0
        proxy = self._configure_proxy()
        available_formats = self._get_alternative_formats(url) if not format_id else [format_id]

        if output_template is None:
            output_template = os.path.join(self.download_path, "%(title)s.%(ext)s")

        while self.current_retry < 3:
            current_format = available_formats[min(self.current_retry, len(available_formats)-1)] if available_formats else None
            try:
                cmd = [
                    "yt-dlp",
                    "--newline",
                    "--no-playlist",
                    "--user-agent", self._get_random_user_agent(),
                    "--cookies", self.cookie_file,
                    "--config-location", self.config_file,
                    "-o", output_template
                ]
                if current_format:
                    cmd.extend(["-f", current_format])
                if proxy:
                    cmd.extend(["--proxy", proxy])
                if self.current_retry > 0:
                    cmd.extend(["--extractor-args", "youtube:player_client=android,bypass_age_gate"])
                cmd.append(url)

                logger.info(f"Running download command: {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                output_file = None
                progress = 0.0
                stderr_lines = []

                for line in process.stdout:
                    logger.debug(line.strip())
                    if "[download]" in line and "%" in line:
                        try:
                            progress = float(line.split("%")[0].split()[-1])
                        except:
                            pass
                    if "[download] Destination:" in line:
                        output_file = line.split("[download] Destination:")[1].strip()

                process.wait()
                stderr_lines = process.stderr.readlines()

                if process.returncode == 0:
                    return {
                        "status": "complete",
                        "progress": 100.0,
                        "output_file": output_file,
                        "current_retry": self.current_retry
                    }
                else:
                    error_output = "".join(stderr_lines)
                    logger.error(f"Download error (attempt {self.current_retry+1}/3): {error_output}")
                    error_flags = self._parse_yt_dlp_error(error_output)

                    if error_flags["is_unavailable"]:
                        raise Exception("Video is unavailable or restricted")
                    if error_flags["is_403"] or error_flags["is_rate_limit"]:
                        self._handle_403_error(url, error_output)
                        self._refresh_cookies(url)
                        proxy = self._configure_proxy()
                    elif error_flags["is_nsig"]:
                        self._handle_nsig_extraction_error(url, error_output)
                    else:
                        self._clear_cache()
                        time.sleep(random.uniform(1.0, 3.0))

                    self.current_retry += 1
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                self.current_retry += 1

        raise Exception(f"Failed to download video after 3 retries")

if __name__ == "__main__":
    # Simple test case
    result = extract_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(f"Started job: {result['job_id']}")
    
    # Wait for job to complete
    job_id = result['job_id']
    while True:
        status = get_job_status(job_id)
        print(f"Progress: {status['progress']}%")
        if status['status'] in ['completed', 'failed', 'cancelled']:
            print(f"Final status: {status['status']}")
            if status['status'] == 'completed':
                print(f"Result: {status['result']}")
            break
        time.sleep(1)
