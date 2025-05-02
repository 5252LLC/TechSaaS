#!/usr/bin/env python3
"""
Test script to directly run the video scraper service
"""
import os
import sys
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Get configuration
video_scraper_port = os.getenv('VIDEO_SCRAPER_PORT', '5500')

print(f"Starting Video Scraper service on port {video_scraper_port}")
print(f"Environment variable VIDEO_SCRAPER_PORT: {os.getenv('VIDEO_SCRAPER_PORT')}")

# Run the video scraper service directly
try:
    subprocess.run(
        ["python", "app.py"],
        cwd="video-scraper/api",
        check=True
    )
except subprocess.CalledProcessError as e:
    print(f"Error running video scraper: {str(e)}")
except KeyboardInterrupt:
    print("Service stopped by user")
