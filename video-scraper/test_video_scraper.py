#!/usr/bin/env python3
"""
Video Scraper Test Script
Tests the functionality of the Video Scraper service
"""

import os
import sys
import time
import json
import requests
from datetime import datetime

def print_header(title):
    """Print a formatted header for test sections"""
    print("\n" + "="*80)
    print(f" {title} ".center(80, "="))
    print("="*80 + "\n")

def print_result(test_name, success, message=""):
    """Print test result in a formatted way"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}{f' | {message}' if message else ''}")

def test_api_endpoints():
    """Test the API endpoints"""
    print_header("API Endpoints Test")
    
    # Test server health
    try:
        response = requests.get('http://localhost:5501/')
        print_result("Server Health", response.status_code == 200, 
                    f"Status: {response.status_code}")
    except requests.RequestException as e:
        print_result("Server Health", False, f"Error: {str(e)}")
    
    # Test supported platforms endpoint
    try:
        response = requests.get('http://localhost:5501/api/video-scraper/supported-platforms')
        print_result("Supported Platforms Endpoint", response.status_code == 200, 
                    f"Status: {response.status_code}")
        if response.status_code == 200:
            platforms = response.json()
            print(f"  Supported platforms: {len(platforms)}")
            for platform in platforms[:3]:  # Show first 3 platforms
                print(f"  - {platform}")
            if len(platforms) > 3:
                print(f"  - ... and {len(platforms) - 3} more")
    except requests.RequestException as e:
        print_result("Supported Platforms Endpoint", False, f"Error: {str(e)}")

def test_error_handling():
    """Test error handling for various scenarios"""
    print_header("Error Handling Test")
    
    # Test invalid URL
    try:
        response = requests.post('http://localhost:5501/api/video-scraper/info', 
                               json={'url': 'not-a-url'})
        expected_error = response.status_code != 200 and "error" in response.json()
        print_result("Invalid URL Handling", expected_error, 
                    f"Status: {response.status_code}, Error: {response.json().get('error', 'No error message')}")
    except requests.RequestException as e:
        print_result("Invalid URL Handling", False, f"Request error: {str(e)}")
    except json.JSONDecodeError:
        print_result("Invalid URL Handling", False, "Invalid JSON response")
    
    # Test unsupported platform
    try:
        response = requests.post('http://localhost:5501/api/video-scraper/info', 
                               json={'url': 'https://example.com/video'})
        expected_error = response.status_code != 200 or "error" in response.json()
        print_result("Unsupported Platform Handling", expected_error, 
                    f"Status: {response.status_code}, Response: {response.json()}")
    except requests.RequestException as e:
        print_result("Unsupported Platform Handling", False, f"Request error: {str(e)}")
    except json.JSONDecodeError:
        print_result("Unsupported Platform Handling", False, "Invalid JSON response")

def test_video_extraction(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"):
    """Test video extraction for a given URL"""
    print_header(f"Video Extraction Test: {url}")
    
    # Start extraction
    job_id = None
    try:
        print(f"Starting extraction for: {url}")
        response = requests.post('http://localhost:5501/api/video-scraper/info', 
                               json={'url': url})
        
        if response.status_code == 200:
            job_id = response.json().get('job_id')
            print_result("Extraction Started", job_id is not None, f"Job ID: {job_id}")
        else:
            print_result("Extraction Started", False, 
                        f"Status: {response.status_code}, Response: {response.json()}")
            return
    except requests.RequestException as e:
        print_result("Extraction Started", False, f"Request error: {str(e)}")
        return
    except json.JSONDecodeError:
        print_result("Extraction Started", False, "Invalid JSON response")
        return
    
    if not job_id:
        return
    
    # Monitor job status
    max_checks = 10
    check_interval = 2  # seconds
    for i in range(max_checks):
        try:
            print(f"Checking job status ({i+1}/{max_checks})...")
            response = requests.get(f'http://localhost:5501/api/job/{job_id}')
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status')
                progress = status_data.get('progress', 0)
                
                print(f"  Status: {status}, Progress: {progress}%")
                
                if status in ['complete', 'completed']:
                    print_result("Job Completed", True, f"Result: {status_data.get('result')}")
                    break
                elif status == 'failed':
                    print_result("Job Completed", False, f"Error: {status_data.get('error')}")
                    break
            else:
                print(f"  Error checking status: {response.status_code}")
        except requests.RequestException as e:
            print(f"  Request error: {str(e)}")
        
        # Only sleep if we're going to check again
        if i < max_checks - 1:
            time.sleep(check_interval)
    else:
        print_result("Job Completed", False, "Timed out waiting for completion")

def check_download_directory():
    """Check the download directory contents"""
    print_header("Download Directory Check")
    
    # Determine the download directory (uses application default)
    downloads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
    
    if os.path.exists(downloads_path):
        files = os.listdir(downloads_path)
        print_result("Download Directory", True, f"Found {len(files)} files")
        
        # Show file details
        print("\nFiles in download directory:")
        for file in files:
            file_path = os.path.join(downloads_path, file)
            size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
            modified = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            print(f"  - {file} ({size:.2f} MB, modified: {modified})")
    else:
        print_result("Download Directory", False, f"Directory not found: {downloads_path}")

def run_all_tests():
    """Run all tests"""
    print_header("VIDEO SCRAPER TEST SUITE")
    print(f"Starting tests at: {datetime.now()}")
    
    test_api_endpoints()
    test_error_handling()
    test_video_extraction()
    check_download_directory()
    
    print_header("TEST SUMMARY")
    print(f"Tests completed at: {datetime.now()}")
    print("\nNote: Review the output above for detailed test results.")

if __name__ == "__main__":
    run_all_tests()
