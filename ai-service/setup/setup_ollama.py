#!/usr/bin/env python3
"""
Platform-specific Ollama Setup Script

This script handles the installation and configuration of Ollama based on the
detected operating system. It supports:
- Linux (Ubuntu, Debian, RHEL/CentOS, Arch)
- macOS
- Windows (via WSL)

It detects the platform, installs Ollama using the appropriate method, and
verifies the installation is working correctly.
"""

import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ollama-setup')

# Ollama version to install - this will be updated dynamically if possible
OLLAMA_VERSION = "0.5.7"

# Official Ollama script URL - this is more reliable than hardcoded GitHub URLs
OLLAMA_INSTALL_SCRIPT_URL = "https://ollama.com/install.sh"

# GitHub API URL to get latest release info
OLLAMA_GITHUB_API_URL = "https://api.github.com/repos/jmorganca/ollama/releases/latest"

# URLs for downloading Ollama - will be determined dynamically when possible
OLLAMA_URLS = {
    "linux": f"https://github.com/jmorganca/ollama/releases/download/v{OLLAMA_VERSION}/ollama-linux-amd64",
    "darwin": f"https://github.com/jmorganca/ollama/releases/download/v{OLLAMA_VERSION}/ollama-darwin-amd64",
    "windows": f"https://github.com/jmorganca/ollama/releases/download/v{OLLAMA_VERSION}/ollama-windows-amd64.exe"
}

# Installation directories
DEFAULT_INSTALL_DIRS = {
    "linux": "/usr/local/bin",
    "darwin": "/usr/local/bin",
    "windows": "C:\\Program Files\\Ollama"
}

# Ollama service configurations
SYSTEMD_SERVICE_FILE = """
[Unit]
Description=Ollama Service
After=network.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Restart=always
User={user}
Environment=HOME={home}
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
"""

LAUNCHD_PLIST = """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ollama.service</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/ollama</string>
        <string>serve</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>{home}/Library/Logs/ollama.log</string>
    <key>StandardOutPath</key>
    <string>{home}/Library/Logs/ollama.log</string>
</dict>
</plist>
"""


def get_latest_ollama_version() -> Optional[str]:
    """
    Get the latest Ollama version from GitHub API.
    
    Returns:
        Optional[str]: Latest version string or None if retrieval failed
    """
    try:
        # Set up a request with a user agent to avoid GitHub API limitations
        headers = {'User-Agent': 'TechSaaS-Ollama-Setup/1.0'}
        req = urllib.request.Request(OLLAMA_GITHUB_API_URL, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            version = data['tag_name']
            
            # Remove 'v' prefix if present
            if version.startswith('v'):
                version = version[1:]
                
            logger.info(f"Found latest Ollama version: {version}")
            return version
    except Exception as e:
        logger.warning(f"Failed to get latest Ollama version from GitHub: {str(e)}")
        logger.warning("Using fallback version from script")
        return None


def get_download_urls(version: str) -> Dict[str, str]:
    """
    Generate download URLs for the specified version.
    
    Args:
        version: Ollama version to download
        
    Returns:
        Dict[str, str]: Dictionary of platform-specific download URLs
    """
    base_url = f"https://github.com/jmorganca/ollama/releases/download/v{version}"
    
    return {
        "linux": f"{base_url}/ollama-linux-amd64",
        "darwin": f"{base_url}/ollama-darwin-amd64",
        "windows": f"{base_url}/ollama-windows-amd64.exe"
    }


def use_official_install_script() -> bool:
    """
    Use the official Ollama install script for installation.
    
    Returns:
        bool: True if installation succeeded
    """
    try:
        logger.info("Using official Ollama installation script")
        
        # Download the install script
        script_path = os.path.join(tempfile.gettempdir(), "ollama_install.sh")
        urllib.request.urlretrieve(OLLAMA_INSTALL_SCRIPT_URL, script_path)
        
        # Make it executable
        os.chmod(script_path, 0o755)
        
        # Run the script
        logger.info("Running Ollama official installation script")
        subprocess.run(
            ["/bin/bash", script_path],
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info("Official Ollama installation script completed successfully")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to use official installation script: {str(e)}")
        logger.warning("Falling back to manual installation method")
        return False


def detect_platform() -> Tuple[str, Optional[str]]:
    """
    Detect the operating system and specific distribution.
    
    Returns:
        Tuple[str, Optional[str]]: (OS name, Distribution name or None)
    """
    system = platform.system().lower()
    
    # Detect Windows and return
    if system == "windows":
        return system, None
    
    # Detect macOS and return
    if system == "darwin":
        return system, None
    
    # For Linux, detect specific distribution
    if system == "linux":
        # Try to detect distribution
        try:
            with open("/etc/os-release", "r") as f:
                os_release = f.read()
                
            # Extract ID from os-release file
            for line in os_release.splitlines():
                if line.startswith("ID="):
                    distro = line.split("=")[1].strip().strip('"')
                    return system, distro
        except (FileNotFoundError, IOError):
            # If we can't determine the specific distro, just return Linux
            pass
        
        # Check for common distribution files as fallback
        if os.path.exists("/etc/debian_version"):
            return system, "debian"
        elif os.path.exists("/etc/redhat-release"):
            return system, "rhel"
        elif os.path.exists("/etc/arch-release"):
            return system, "arch"
    
    # Fallback to just the system name
    return system, None


def check_if_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if Ollama is already installed and get version information.
    
    Returns:
        Tuple[bool, Optional[str]]: (True if installed, Version string or None)
    """
    # Try the newer --version format first
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            version_info = result.stdout.strip()
            logger.info(f"Ollama is already installed: {version_info}")
            return True, version_info
        
    except FileNotFoundError:
        pass
    
    # Try the older 'version' subcommand format as fallback
    try:
        result = subprocess.run(
            ["ollama", "version"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            version_info = result.stdout.strip()
            logger.info(f"Ollama is already installed: {version_info}")
            return True, version_info
        else:
            logger.debug(f"Ollama check failed with: {result.stderr}")
    
    except FileNotFoundError:
        logger.debug("Ollama executable not found")
    
    return False, None


def parse_version(version_info: str) -> Optional[str]:
    """
    Parse version number from Ollama version string.
    
    Args:
        version_info: Full version string from 'ollama version'
        
    Returns:
        Optional[str]: Version number or None if parsing failed
    """
    if not version_info:
        return None
    
    # Try to match newer format: "ollama version is X.Y.Z"
    match = re.search(r'ollama version is (\d+\.\d+\.\d+)', version_info)
    if match:
        return match.group(1)
    
    # Try to match older format: "ollama version vX.Y.Z" or "ollama version X.Y.Z"
    match = re.search(r'ollama version (v?\d+\.\d+\.\d+)', version_info)
    if match:
        version = match.group(1)
        # Remove 'v' prefix if present
        if version.startswith('v'):
            version = version[1:]
        return version
    
    return None


def compare_versions(installed_version: Optional[str], target_version: str) -> Tuple[bool, str]:
    """
    Compare installed version with target version.
    
    Args:
        installed_version: Installed version string (e.g., "0.1.27")
        target_version: Target version string (e.g., "0.1.27")
        
    Returns:
        Tuple[bool, str]: (True if update needed, Comparison result description)
    """
    if installed_version is None:
        return True, "No installed version detected"
    
    try:
        # Split version strings into components
        installed = [int(x) for x in installed_version.split('.')]
        target = [int(x) for x in target_version.split('.')]
        
        # Ensure both lists have the same length
        while len(installed) < len(target):
            installed.append(0)
        while len(target) < len(installed):
            target.append(0)
        
        # Compare each component
        for i, t in zip(installed, target):
            if i < t:
                return True, f"Installed version {installed_version} is older than target {target_version}"
            elif i > t:
                return False, f"Installed version {installed_version} is newer than target {target_version}"
        
        # Versions are equal
        return False, f"Installed version {installed_version} matches target {target_version}"
    
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Could not compare versions: {installed_version} vs {target_version}")
        return True, "Version comparison failed, update recommended"


def download_ollama(system: str, version: str, output_dir: str = None) -> str:
    """
    Download the appropriate Ollama binary for the detected system.
    
    Args:
        system: Operating system name
        version: Ollama version to download
        output_dir: Directory to save the binary
        
    Returns:
        str: Path to the downloaded binary
    """
    # Generate URLs for this specific version
    urls = get_download_urls(version)
    
    if system not in urls:
        raise ValueError(f"Unsupported system: {system}")
    
    url = urls[system]
    output_dir = output_dir or tempfile.gettempdir()
    
    # Create the output filename
    if system == "windows":
        output_file = os.path.join(output_dir, "ollama.exe")
    else:
        output_file = os.path.join(output_dir, "ollama")
    
    logger.info(f"Downloading Ollama from {url}")
    
    try:
        # Download the file
        urllib.request.urlretrieve(url, output_file)
        
        # Make binary executable (except on Windows)
        if system != "windows":
            os.chmod(output_file, 0o755)
        
        logger.info(f"Downloaded Ollama to {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"Failed to download Ollama: {str(e)}")
        raise


def update_ollama(binary_path: str, system: str) -> bool:
    """
    Update an existing Ollama installation.
    
    Args:
        binary_path: Path to the new Ollama binary
        system: Operating system name
        
    Returns:
        bool: True if update succeeded
    """
    install_dir = DEFAULT_INSTALL_DIRS[system]
    
    # Determine destination path
    if system == "windows":
        dest_path = os.path.join(install_dir, "ollama.exe")
    else:
        dest_path = os.path.join(install_dir, "ollama")
    
    # Create backup of existing binary
    if os.path.exists(dest_path):
        backup_path = f"{dest_path}.backup"
        try:
            shutil.copy2(dest_path, backup_path)
            logger.info(f"Backed up existing Ollama binary to {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create backup of existing Ollama: {str(e)}")
    
    try:
        # Copy new binary to install directory
        shutil.copy2(binary_path, dest_path)
        
        # Make binary executable (except on Windows)
        if system != "windows":
            os.chmod(dest_path, 0o755)
        
        logger.info(f"Successfully updated Ollama at {dest_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to update Ollama: {str(e)}")
        
        # Try to restore backup
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, dest_path)
                logger.info("Restored Ollama from backup after failed update")
            except Exception as restore_err:
                logger.error(f"Failed to restore Ollama from backup: {str(restore_err)}")
        
        return False


def install_linux(distro: Optional[str], binary_path: str) -> bool:
    """
    Install Ollama on Linux.
    
    Args:
        distro: Linux distribution name
        binary_path: Path to the Ollama binary
        
    Returns:
        bool: True if installation succeeded
    """
    # Try to use the official installation script first for better compatibility
    if use_official_install_script():
        return True
        
    # Fallback to manual installation if the script fails
    install_dir = DEFAULT_INSTALL_DIRS["linux"]
    
    # Create destination directory if it doesn't exist
    os.makedirs(install_dir, exist_ok=True)
    
    # Copy binary to install directory
    dest_path = os.path.join(install_dir, "ollama")
    shutil.copy2(binary_path, dest_path)
    os.chmod(dest_path, 0o755)
    
    logger.info(f"Installed Ollama to {dest_path}")
    
    # Set up systemd service
    try:
        # Get current user for service file
        username = os.environ.get("USER", "root")
        home_dir = os.path.expanduser("~")
        
        # Generate service file content
        service_content = SYSTEMD_SERVICE_FILE.format(
            user=username,
            home=home_dir
        )
        
        # Write service file
        service_path = os.path.join("/tmp", "ollama.service")
        with open(service_path, "w") as f:
            f.write(service_content)
        
        # Try to install service file (might require sudo)
        logger.info("Attempting to install systemd service file...")
        
        try:
            subprocess.run(
                ["sudo", "cp", service_path, "/etc/systemd/system/ollama.service"],
                check=True
            )
            
            subprocess.run(
                ["sudo", "systemctl", "daemon-reload"],
                check=True
            )
            
            subprocess.run(
                ["sudo", "systemctl", "enable", "ollama"],
                check=True
            )
            
            logger.info("Installed and enabled Ollama systemd service")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning(
                "Could not install systemd service automatically. "
                f"Service file is available at {service_path}"
            )
    
    except Exception as e:
        logger.warning(f"Failed to set up systemd service: {str(e)}")
        logger.warning(
            "You can manually start Ollama with 'ollama serve' "
            "or set up a service later."
        )
    
    return True


def install_macos(binary_path: str) -> bool:
    """
    Install Ollama on macOS.
    
    Args:
        binary_path: Path to the Ollama binary
        
    Returns:
        bool: True if installation succeeded
    """
    # Try to use the official installation script first for better compatibility
    if use_official_install_script():
        return True
        
    # Fallback to manual installation if the script fails
    install_dir = DEFAULT_INSTALL_DIRS["darwin"]
    
    # Create destination directory if it doesn't exist
    os.makedirs(install_dir, exist_ok=True)
    
    # Copy binary to install directory
    dest_path = os.path.join(install_dir, "ollama")
    shutil.copy2(binary_path, dest_path)
    os.chmod(dest_path, 0o755)
    
    logger.info(f"Installed Ollama to {dest_path}")
    
    # Set up launchd service
    try:
        # Generate plist content
        home_dir = os.path.expanduser("~")
        plist_content = LAUNCHD_PLIST.format(home=home_dir)
        
        # Define paths
        plist_path = os.path.join(home_dir, "Library/LaunchAgents", "com.ollama.service.plist")
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        
        # Write plist file
        with open(plist_path, "w") as f:
            f.write(plist_content)
        
        # Load service
        subprocess.run(
            ["launchctl", "load", plist_path],
            check=True
        )
        
        logger.info("Installed and loaded Ollama launchd service")
    
    except Exception as e:
        logger.warning(f"Failed to set up launchd service: {str(e)}")
        logger.warning(
            "You can manually start Ollama with 'ollama serve' "
            "or set up a service later."
        )
    
    return True


def install_windows(binary_path: str) -> bool:
    """
    Install Ollama on Windows.
    
    Args:
        binary_path: Path to the Ollama binary
        
    Returns:
        bool: True if installation succeeded
    """
    # Check if WSL is installed
    try:
        subprocess.run(
            ["wsl", "--status"],
            check=True,
            capture_output=True
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error(
            "Windows Subsystem for Linux (WSL) is not installed. "
            "Ollama requires WSL to run on Windows."
        )
        return False
    
    # Create install directory
    install_dir = DEFAULT_INSTALL_DIRS["windows"]
    os.makedirs(install_dir, exist_ok=True)
    
    # Copy binary to install directory
    dest_path = os.path.join(install_dir, "ollama.exe")
    shutil.copy2(binary_path, dest_path)
    
    logger.info(f"Installed Ollama to {dest_path}")
    
    # Create shortcut for starting Ollama
    try:
        start_script = os.path.join(install_dir, "start-ollama.bat")
        with open(start_script, "w") as f:
            f.write(f'@echo off\n"{dest_path}" serve\n')
        
        logger.info(f"Created startup script at {start_script}")
    except Exception as e:
        logger.warning(f"Failed to create startup script: {str(e)}")
    
    return True


def verify_installation() -> bool:
    """
    Verify that Ollama has been installed correctly and is working.
    
    Returns:
        bool: True if verification passed
    """
    logger.info("Verifying Ollama installation...")
    
    # Check if ollama binary is available (try new format first)
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"Ollama version: {result.stdout.strip()}")
    except (subprocess.SubprocessError, FileNotFoundError):
        # Try old format as fallback
        try:
            result = subprocess.run(
                ["ollama", "version"],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Ollama version: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("Could not verify Ollama version. Installation verification failed.")
            return False
    
    # Attempt to start the Ollama service
    try:
        # Check if Ollama is already running
        try:
            subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                check=True,
                capture_output=True
            )
            logger.info("Ollama service is already running")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            # Ollama is not running, try to start it
            logger.info("Starting Ollama service for verification...")
            
            # Start Ollama in the background
            process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for Ollama to start (up to 10 seconds)
            for _ in range(10):
                time.sleep(1)
                try:
                    result = subprocess.run(
                        ["curl", "-s", "http://localhost:11434/api/tags"],
                        check=True,
                        capture_output=True
                    )
                    logger.info("Ollama service started successfully")
                    
                    # Stop the Ollama process
                    process.terminate()
                    return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass
            
            # If we get here, Ollama didn't start
            process.terminate()
            logger.error("Ollama service failed to start within the timeout period")
            return False
    
    except Exception as e:
        logger.error(f"Error verifying Ollama installation: {str(e)}")
        return False


def setup_ollama(force: bool = False, update_only: bool = False) -> bool:
    """
    Set up Ollama on the current system.
    
    Args:
        force: Force reinstallation even if already installed
        update_only: Only update if a newer version is available
        
    Returns:
        bool: True if setup succeeded
    """
    logger.info("Starting Ollama setup...")
    
    # Try to get the latest version from GitHub
    latest_version = get_latest_ollama_version()
    if latest_version:
        global OLLAMA_VERSION
        OLLAMA_VERSION = latest_version
    
    # Check if already installed
    installed, version_info = check_if_installed()
    
    if installed:
        # Parse installed version
        installed_version = parse_version(version_info)
        update_needed, reason = compare_versions(installed_version, OLLAMA_VERSION)
        
        logger.info(reason)
        
        if update_needed:
            logger.info(f"Ollama needs updating from {installed_version} to {OLLAMA_VERSION}")
        elif force:
            logger.info("Ollama is already up to date, but force reinstall was requested")
        else:
            logger.info("Ollama is already up to date")
            
            # Verify the installation
            if verify_installation():
                logger.info("Ollama installation verified successfully")
                return True
            else:
                logger.warning("Ollama is installed but verification failed. Proceeding with reinstallation...")
                update_needed = True
        
        # Skip if not update_needed and not force
        if not update_needed and not force:
            return True
        
        # If only update mode, try to update the binary
        if update_only and not force and update_needed:
            # Detect platform
            system, _ = detect_platform()
            
            # Download new binary
            try:
                binary_path = download_ollama(system, OLLAMA_VERSION)
                
                # Update the binary
                if update_ollama(binary_path, system):
                    logger.info(f"Successfully updated Ollama to version {OLLAMA_VERSION}")
                    
                    # Verify the installation
                    if verify_installation():
                        logger.info("Ollama update verified successfully")
                        return True
                    else:
                        logger.warning("Ollama update verification failed. Proceeding with full reinstallation...")
                else:
                    logger.warning("Failed to update Ollama. Proceeding with full reinstallation...")
            except Exception as e:
                logger.error(f"Failed during update: {str(e)}")
                logger.warning("Proceeding with full reinstallation...")
    
    # Detect platform
    system, distro = detect_platform()
    logger.info(f"Detected platform: {system}" + (f" ({distro})" if distro else ""))
    
    # For Linux and macOS, try official script first
    if system in ("linux", "darwin") and use_official_install_script():
        # Verify installation after using official script
        if verify_installation():
            logger.info(f"Ollama was successfully installed using official script")
            return True
        else:
            logger.warning("Ollama was installed but verification failed. Trying manual installation...")
    
    # Otherwise use manual installation process
    try:
        # Download Ollama binary
        binary_path = download_ollama(system, OLLAMA_VERSION)
    except Exception as e:
        logger.error(f"Failed to download Ollama: {str(e)}")
        return False
    
    # Install based on platform
    success = False
    try:
        if system == "linux":
            success = install_linux(distro, binary_path)
        elif system == "darwin":
            success = install_macos(binary_path)
        elif system == "windows":
            success = install_windows(binary_path)
        else:
            logger.error(f"Unsupported platform: {system}")
            return False
    except Exception as e:
        logger.error(f"Error during installation: {str(e)}")
        return False
    
    # Verify installation
    if success:
        if verify_installation():
            logger.info(f"Ollama was successfully installed/updated to version {OLLAMA_VERSION}")
            return True
        else:
            logger.error("Ollama was installed but verification failed")
            return False
    else:
        logger.error("Ollama installation failed")
        return False


def main():
    """Main entry point for Ollama setup."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Set up Ollama on the current system')
    parser.add_argument('--force', action='store_true', help='Force reinstallation even if already installed')
    parser.add_argument('--update-only', action='store_true', help='Only update if a newer version is available')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run setup
    success = setup_ollama(force=args.force, update_only=args.update_only)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
