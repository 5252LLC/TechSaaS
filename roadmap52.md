# TechSaaS Platform: Product Requirements Document (PRD)

## 1. Introduction

### 1.1 Purpose
This document outlines the requirements for enhancing the TechSaaS platform with an integrated video scraping solution based on Hitomi-Downloader and transitioning the AI infrastructure from AI16z to LangChain with Ollama integration.

### 1.2 Project Scope
The scope includes:
- Integration of Hitomi-Downloader for advanced video scraping
- Transition from AI16z to LangChain for AI capabilities
- Web browser/search interface integration
- Creation of a microservices architecture
- Implementation of security and anonymization features

### 1.3 Definitions & Acronyms
- **TechSaaS**: Technology Software as a Service platform
- **Hitomi-Downloader**: Advanced multi-site content downloader
- **LangChain**: Framework for developing applications powered by language models
- **Ollama**: Local large language model runtime
- **AI16z**: Previous AI implementation being replaced
- **Windsurf**: AI-powered coding environment for implementation

## 2. System Architecture

### 2.1 High-Level Architecture
```
TechSaaS Platform
├── API Gateway (Port 5000)
├── Web Browser Interface (Port 5252)
├── Video Scraper Service (Port 5500)
│   └── Hitomi-Downloader Integration
├── Web Scraper Service (Port 5501)
├── AI Service
│   ├── LangChain Framework
│   └── Ollama Model Integration
└── Security Layer
    ├── Authentication
    ├── Encryption
    └── Anonymization
```

### 2.2 Component Interactions
1. Web Interface → API Gateway → Services
2. Video Scraper ↔ Hitomi-Downloader ↔ Storage
3. AI Service (LangChain) ↔ All Components
4. Security Layer → All Communications

## 3. Functional Requirements

### 3.1 Video Scraper Integration (Hitomi-Downloader)

#### 3.1.1 Core Requirements
- Integrate Hitomi-Downloader as the primary video scraping engine
- Support all platforms compatible with Hitomi-Downloader
- Implement a Flask wrapper to expose Hitomi functionality via REST API
- Create web interface for controlling Hitomi-Downloader

#### 3.1.2 Implementation Details
1. **Wrapper Service Creation**
   - Create Python Flask service to interface with Hitomi-Downloader
   - Implement API endpoints for all major Hitomi functions
   - Handle authentication and rate limiting

2. **Interface Integration**
   - Design responsive web UI for video scraping
   - Create dashboard for monitoring downloads
   - Implement search interface for finding content

3. **Storage Management**
   - Configure content storage with proper organization
   - Implement metadata extraction and indexing
   - Create export functionality for downloaded content

### 3.2 AI Transition (AI16z to LangChain)

#### 3.2.1 Core Requirements
- Replace AI16z integration with LangChain framework
- Implement Ollama for local model deployment
- Maintain all existing AI functionality during transition
- Add new capabilities enabled by LangChain

#### 3.2.2 Implementation Details
1. **LangChain Setup**
   - Install LangChain framework and dependencies
   - Configure for use with local Ollama models
   - Set up appropriate prompt templates

2. **Ollama Integration**
   - Install Ollama runtime
   - Deploy selected models (llama3.2:3b, grok:3b)
   - Configure model selection based on task requirements

3. **Service Migration**
   - Identify all AI16z touchpoints in codebase
   - Create equivalent LangChain implementations
   - Test for functional equivalence

4. **Enhanced Capabilities**
   - Implement agents for specific tasks
   - Create tools for web searching, calculation, etc.
   - Add memory systems for conversation context

### 3.3 Web Browser & Search Interface

#### 3.3.1 Core Requirements
- Create an integrated web browser within the platform
- Implement search functionality across multiple engines
- Connect browser actions to video/content scraping

#### 3.3.2 Implementation Details
1. **Browser Implementation**
   - Create Flask-based browser interface
   - Implement URL navigation and history
   - Add content rendering capabilities

2. **Search Integration**
   - Create search interface with multiple engine options
   - Implement results parsing and display
   - Add direct navigation from search results

3. **Scraping Connection**
   - Detect scrapable content in browser
   - Add one-click scraping from browser interface
   - Implement context menu for advanced options

## 4. Technical Implementation Plan

### 4.1 Phase 1: Environment Setup (Days 1-2)

#### 4.1.1 Directory Structure Creation
```bash
# Create the main structure
mkdir -p techsaas-platform/{api-gateway,video-scraper,web-interface,ai-service,security}

# Create video scraper subdirectories
mkdir -p techsaas-platform/video-scraper/{api,hitomi-integration,templates,static}

# Create AI service subdirectories
mkdir -p techsaas-platform/ai-service/{langchain,ollama,prompts,tools}

# Create web interface directories
mkdir -p techsaas-platform/web-interface/{browser,video-scraper,templates,static}

# Initialize git repository
cd techsaas-platform
git init
```

#### 4.1.2 Dependency Installation
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core dependencies
pip install flask requests beautifulsoup4 yt-dlp langchain langchain-community pydantic==1.10.8

# Install AI dependencies
pip install langchain langchain-community

# Node.js dependencies
npm init -y
npm install express axios cors dotenv
```

#### 4.1.3 Hitomi-Downloader Setup
```bash
# Clone Hitomi-Downloader repository
git clone https://github.com/KurtBestor/Hitomi-Downloader.git hitomi

# Setup for programmatic access
# (See detailed instructions in Section 4.1.4)
```

#### 4.1.4 Hitomi-Downloader Integration Notes
Since Hitomi-Downloader is primarily a GUI application, we'll need to:
1. Identify the core Python modules for scraping functionality
2. Create a wrapper that can call these modules programmatically
3. Expose key functions through a REST API
4. Handle authentication and rate limiting

### 4.2 Phase 2: Video Scraper Implementation (Days 3-6)

#### 4.2.1 Flask API Wrapper Creation

**File: `video-scraper/api/app.py`**
```python
from flask import Flask, request, jsonify
import sys
import os
import json

# Add Hitomi-Downloader to path (adjust as needed)
sys.path.append("../hitomi")

# Import Hitomi modules (these will need to be identified)
# For example: from hitomi import downloader, extractor

app = Flask(__name__)

@app.route('/api/sites', methods=['GET'])
def get_supported_sites():
    # Return list of supported sites from Hitomi
    # Implementation depends on Hitomi's internals
    return jsonify({"sites": ["example.com", "video.com"]})

@app.route('/api/extract', methods=['POST'])
def extract_video_info():
    url = request.json.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        # Call Hitomi's extraction functionality
        # video_info = extractor.extract(url)
        # Example response structure:
        video_info = {
            "title": "Example Video",
            "formats": ["720p", "1080p"],
            "thumbnail": "http://example.com/thumb.jpg"
        }
        return jsonify(video_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    url = request.json.get('url')
    format = request.json.get('format')
    output_dir = request.json.get('output_dir', './downloads')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        # Call Hitomi's download functionality
        # result = downloader.download(url, format, output_dir)
        # Example response:
        result = {
            "status": "success",
            "file_path": f"{output_dir}/example_video.mp4",
            "size": "15.2 MB"
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create downloads directory if it doesn't exist
    os.makedirs('./downloads', exist_ok=True)
    app.run(debug=True, port=5500)
```

#### 4.2.2 Web Interface Implementation

**File: `web-interface/templates/video-scraper.html`**
```html
<!DOCTYPE html>
<html>
<head>
    <title>TechSaaS Video Scraper</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <h1>TechSaaS Video Scraper</h1>
        <div class="tab-container">
            <div id="url-tab" class="tab active" onclick="showTab('url-tab')">URL Input</div>
            <div id="search-tab" class="tab" onclick="showTab('search-tab')">Search</div>
            <div id="downloads-tab" class="tab" onclick="showTab('downloads-tab')">Downloads</div>
        </div>
        
        <div id="url-tab-content" class="tab-content active">
            <form id="url-form">
                <div class="form-group">
                    <input type="text" id="video-url" placeholder="Enter video URL" required>
                </div>
                <button type="submit">Extract Video</button>
            </form>
            
            <div id="video-info" class="results-container" style="display: none;">
                <h2>Video Information</h2>
                <div id="video-details"></div>
                <button id="download-btn">Download Video</button>
            </div>
        </div>
        
        <div id="search-tab-content" class="tab-content">
            <form id="search-form">
                <div class="form-group">
                    <input type="text" id="search-query" placeholder="Search videos" required>
                </div>
                <button type="submit">Search</button>
            </form>
            
            <div id="search-results" class="results-container"></div>
        </div>
        
        <div id="downloads-tab-content" class="tab-content">
            <h2>Download History</h2>
            <div id="download-history"></div>
        </div>
    </div>
    
    <script src="/static/js/video-scraper.js"></script>
</body>
</html>
```

**File: `web-interface/static/js/video-scraper.js`**
```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Tab functionality
    window.showTab = function(tabId) {
        // Hide all tab contents
        const tabContents = document.getElementsByClassName('tab-content');
        for (let i = 0; i < tabContents.length; i++) {
            tabContents[i].classList.remove('active');
        }
        
        // Deactivate all tabs
        const tabs = document.getElementsByClassName('tab');
        for (let i = 0; i < tabs.length; i++) {
            tabs[i].classList.remove('active');
        }
        
        // Activate selected tab and content
        document.getElementById(tabId).classList.add('active');
        document.getElementById(tabId + '-content').classList.add('active');
    };
    
    // URL form submission
    document.getElementById('url-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const url = document.getElementById('video-url').value;
        
        // Show loading indicator
        document.getElementById('video-details').innerHTML = '<p>Loading...</p>';
        document.getElementById('video-info').style.display = 'block';
        
        // Call API to extract video info
        fetch('/api/video-scraper/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                document.getElementById('video-details').innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }
            
            // Display video information
            let html = `
                <div class="video-info-card">
                    <h3>${data.title}</h3>
                    <img src="${data.thumbnail}" alt="Thumbnail" class="video-thumbnail">
                    <div class="format-selector">
                        <label for="format-select">Select Format:</label>
                        <select id="format-select">
            `;
            
            data.formats.forEach(format => {
                html += `<option value="${format}">${format}</option>`;
            });
            
            html += `
                        </select>
                    </div>
                </div>
            `;
            
            document.getElementById('video-details').innerHTML = html;
        })
        .catch(error => {
            document.getElementById('video-details').innerHTML = `<p class="error">Error: ${error.message}</p>`;
        });
    });
    
    // Download button functionality
    document.getElementById('download-btn').addEventListener('click', function() {
        const url = document.getElementById('video-url').value;
        const format = document.getElementById('format-select')?.value || '';
        
        fetch('/api/video-scraper/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                url: url,
                format: format
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Error: ${data.error}`);
                return;
            }
            
            alert(`Download started! File will be saved to: ${data.file_path}`);
            updateDownloadHistory();
        })
        .catch(error => {
            alert(`Error: ${error.message}`);
        });
    });
    
    // Search form functionality
    document.getElementById('search-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const query = document.getElementById('search-query').value;
        
        // Show loading indicator
        document.getElementById('search-results').innerHTML = '<p>Searching...</p>';
        
        // Call API to search videos
        fetch(`/api/video-scraper/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                document.getElementById('search-results').innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }
            
            if (data.results.length === 0) {
                document.getElementById('search-results').innerHTML = '<p>No results found.</p>';
                return;
            }
            
            // Display search results
            let html = '<div class="results-grid">';
            
            data.results.forEach(result => {
                html += `
                    <div class="result-card">
                        <img src="${result.thumbnail}" alt="Thumbnail" class="result-thumbnail">
                        <h3>${result.title}</h3>
                        <p>${result.description}</p>
                        <button class="extract-btn" data-url="${result.url}">Extract</button>
                    </div>
                `;
            });
            
            html += '</div>';
            document.getElementById('search-results').innerHTML = html;
            
            // Add event listeners to extract buttons
            document.querySelectorAll('.extract-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const url = this.getAttribute('data-url');
                    document.getElementById('video-url').value = url;
                    showTab('url-tab');
                    document.getElementById('url-form').dispatchEvent(new Event('submit'));
                });
            });
        })
        .catch(error => {
            document.getElementById('search-results').innerHTML = `<p class="error">Error: ${error.message}</p>`;
        });
    });
    
    // Function to update download history
    function updateDownloadHistory() {
        fetch('/api/video-scraper/history')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                document.getElementById('download-history').innerHTML = `<p class="error">${data.error}</p>`;
                return;
            }
            
            if (data.downloads.length === 0) {
                document.getElementById('download-history').innerHTML = '<p>No download history available.</p>';
                return;
            }
            
            // Display download history
            let html = '<div class="history-list">';
            
            data.downloads.forEach(download => {
                html += `
                    <div class="history-item">
                        <h3>${download.title}</h3>
                        <p>Downloaded: ${new Date(download.timestamp).toLocaleString()}</p>
                        <p>Format: ${download.format}</p>
                        <p>Status: ${download.status}</p>
                        <a href="/download/${download.id}" class="download-link">Download File</a>
                    </div>
                `;
            });
            
            html += '</div>';
            document.getElementById('download-history').innerHTML = html;
        })
        .catch(error => {
            document.getElementById('download-history').innerHTML = `<p class="error">Error: ${error.message}</p>`;
        });
    }
    
    // Load download history when tab is shown
    document.getElementById('downloads-tab').addEventListener('click', updateDownloadHistory);
});
```

### 4.3 Phase 3: LangChain Integration (Days 7-10)

#### 4.3.1 Setup LangChain and Ollama

**File: `ai-service/setup.py`**
```python
import os
import subprocess
import sys
import platform

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("Error: Python 3.9 or higher is required.")
        sys.exit(1)
    print(f"✓ Python version {version.major}.{version.minor}.{version.micro} detected.")

def install_dependencies():
    """Install required Python packages."""
    print("Installing Python dependencies...")
    requirements = [
        "langchain==0.1.0",
        "langchain-community==0.0.15",
        "langchain-core==0.1.10",
        "langchain-text-splitters==0.0.1",
        "pydantic==1.10.8",
        "flask==2.3.3",
        "requests==2.31.0",
        "beautifulsoup4==4.12.2"
    ]
    
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + requirements)
    print("✓ Python dependencies installed.")

def setup_ollama():
    """Setup Ollama based on platform."""
    system = platform.system().lower()
    
    print(f"Setting up Ollama for {system}...")
    
    if system == "linux":
        try:
            subprocess.check_call(["curl", "-fsSL", "https://ollama.com/install.sh", "|", "sh"])
            print("✓ Ollama installed.")
        except:
            print("! Could not install Ollama automatically. Please install manually from https://ollama.com/")
    
    elif system == "darwin":  # macOS
        try:
            subprocess.check_call(["brew", "install", "ollama"])
            print("✓ Ollama installed via Homebrew.")
        except:
            print("! Could not install Ollama via Homebrew. Please install manually from https://ollama.com/")
    
    elif system == "windows":
        print("! Automated Ollama installation not supported on Windows.")
        print("  Please download and install Ollama from https://ollama.com/")
    
    else:
        print(f"! Unsupported platform: {system}")
        print("  Please install Ollama manually from https://ollama.com/")

def pull_models():
    """Pull the required models for Ollama."""
    models = ["llama3.2:3b", "grok:3b"]
    
    print("Pulling language models (this may take some time)...")
    for model in models:
        try:
            print(f"Pulling {model}...")
            subprocess.check_call(["ollama", "pull", model])
            print(f"✓ Model {model} pulled successfully.")
        except:
            print(f"! Failed to pull model {model}. Please pull manually with: ollama pull {model}")

def create_directories():
    """Create necessary directories."""
    directories = [
        "langchain",
        "ollama",
        "prompts",
        "tools",
        "memory"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✓ Directories created.")

def setup():
    """Main setup function."""
    print("Setting up AI service with LangChain and Ollama...")
    
    check_python_version()
    install_dependencies()
    create_directories()
    setup_ollama()
    pull_models()
    
    print("\nSetup complete! Next steps:")
    print("1. Start Ollama service: ollama serve")
    print("2. Test the setup: python test_setup.py")
    print("3. Begin implementing LangChain components")

if __name__ == "__main__":
    setup()
```

#### 4.3.2 Create LangChain Components

**File: `ai-service/langchain/base.py`**
```python
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
import os

class LangChainService:
    """Base service for LangChain integration."""
    
    def __init__(self, model_name="llama3.2:3b"):
        """Initialize with the specified model."""
        self.model_name = model_name
        self.llm = Ollama(model=model_name)
        self.memory = ConversationBufferMemory(memory_key="chat_history")
    
    def create_chain(self, template, input_variables, output_key="text"):
        """Create a LangChain chain with the given template."""
        prompt = PromptTemplate(
            input_variables=input_variables,
            template=template
        )
        
        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            output_key=output_key,
            memory=self.memory
        )
    
    def generate_response(self, chain, **kwargs):
        """Generate a response using the given chain and inputs."""
        try:
            response = chain.invoke(kwargs)
            return {
                "status": "success",
                "response": response[chain.output_key],
                "model": self.model_name
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "model": self.model_name
            }
    
    def switch_model(self, model_name):
        """Switch to a different model."""
        self.model_name = model_name
        self.llm = Ollama(model=model_name)
        return {"status": "success", "model": model_name}
    
    def clear_memory(self):
        """Clear conversation memory."""
        self.memory.clear()
        return {"status": "success", "message": "Memory cleared"}
```

**File: `ai-service/prompts/templates.py`**
```python
# Collection of prompt templates for different tasks

VIDEO_ANALYSIS_TEMPLATE = """
You are analyzing a video from {source}. Here is the information about the video:

Title: {title}
Description: {description}
Duration: {duration}
Tags: {tags}

Based on this information, please provide:
1. A brief summary of what this video likely contains
2. Key points that might be covered
3. Potential audience for this content
4. Any cautionary notes about the content (if applicable)

Your analysis:
"""

WEB_SCRAPING_TEMPLATE = """
You are analyzing content scraped from {url}. Here is the extracted text:

{content}

Please provide:
1. A concise summary of this content
2. The main topics or themes
3. Key facts or data points
4. Any biases or perspectives you notice
5. Recommendations for further research

Your analysis:
"""

SOCIAL_MEDIA_TEMPLATE = """
You are analyzing a social media profile from {platform}. Here is the profile information:

Username: {username}
Bio: {bio}
Followers: {followers}
Following: {following}
Recent Activity: {activity}

Please provide:
1. A professional assessment of this profile
2. Apparent interests or focus areas
3. Potential audience or community
4. Recommendations for engagement

Your analysis:
"""

CRYPTO_ANALYSIS_TEMPLATE = """
You are analyzing cryptocurrency data for {coin}. Here is the current information:

Current Price: {price}
24h Change: {change_24h}
Market Cap: {market_cap}
Volume: {volume}
Recent News: {news}

Please provide:
1. A brief market analysis
2. Notable trends or patterns
3. Key factors potentially influencing price
4. Cautionary notes (remind that this is not financial advice)

Your analysis:
"""

GENERAL_CHAT_TEMPLATE = """
You are an AI assistant for the TechSaaS platform. The user has asked:

{query}

Previous conversation:
{chat_history}

Provide a helpful, concise, and accurate response:
"""
```

**File: `ai-service/tools/web_tools.py`**
```python
from langchain.tools import Tool
from langchain.utilities import GoogleSearchAPIWrapper
import requests
from bs4 import BeautifulSoup

class WebTools:
    """Collection of web-related tools for LangChain."""
    
    def __init__(self, api_key=None):
        """Initialize with optional API key for search."""
        self.api_key = api_key
    
    def search_tool(self):
        """Create a search tool."""
        if self.api_key:
            search = GoogleSearchAPIWrapper(api_key=self.api_key)
            return Tool(
                name="Search",
                func=search.run,
                description="Useful for searching the web for current information."
            )
        else:
            return Tool(
                name="Search",
                func=self._basic_search,
                description="Basic web search functionality."
            )
    
    def _basic_search(self, query):
        """Basic search implementation without API key."""
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for g in soup.find_all('div', class_='g'):
                anchors = g.find_all('a')
                if anchors:
                    link = anchors[0]['href']
                    title = g.find('h3').text if g.find('h3') else "No title"
                    snippet = g.find('div', class_='VwiC3b').text if g.find('div', class_='VwiC3b') else "No snippet"
                    results.append(f"{title}\n{snippet}\n{link}\n")
            
            return "\n".join(results[:5])
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def webpage_tool(self):
        """Create a webpage content extraction tool."""
        return Tool(
            name="GetWebPage",
            func=self._get_webpage_content,
            description="Extract content from a webpage given its URL."
        )
    
    def _get_webpage_content(self, url):
        """Extract main content from a webpage."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Remove blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Truncate if too long
            if len(text) > 8000:
                text = text[:8000] + "...[content truncated]"
            
            return text
        except Exception as e:
            return f"Failed to extract webpage content: {str(e)}"
```

#### 4.3.3 Create Flask API for LangChain

**File: `ai-service/app.py`**
```python
from flask import Flask, request, jsonify
import os
import sys

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import LangChain components
from langchain.base import LangChainService
from prompts.templates import (
    VIDEO_ANALYSIS_TEMPLATE,
    WEB_SCRAPING_TEMPLATE,
    SOCIAL_MEDIA_TEMPLATE,
    CRYPTO_ANALYSIS_TEMPLATE,
    GENERAL_CHAT_TEMPLATE
)

app = Flask(__name__)
langchain_service = LangChainService()

# Create chains for different tasks
video_chain = langchain_service.create_chain(
    VIDEO_ANALYSIS_TEMPLATE,
    ["source", "title", "description", "duration", "tags"],
    "analysis"
)

web_chain = langchain_service.create_chain