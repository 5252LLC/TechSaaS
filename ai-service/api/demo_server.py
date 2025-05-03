#!/usr/bin/env python3
"""
Demo Server for Hitomi-LangChain Connector

This provides a simple web interface to demonstrate the capabilities
of the Hitomi-LangChain connector.
"""

import os
import sys
import logging
import uvicorn
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import time
from pathlib import Path

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the connector
try:
    from integration.hitomi_langchain_connector import HitomiLangChainConnector
    from langchain.service import LangChainService
    
    CONNECTOR_AVAILABLE = True
except ImportError as e:
    print(f"Failed to import connector: {e}")
    CONNECTOR_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("hitomi_langchain_demo")

# Create the FastAPI app
app = FastAPI(
    title="Hitomi-LangChain Connector Demo",
    description="Demonstration of the Hitomi-LangChain connector for video analysis",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize templates
templates_path = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_path, exist_ok=True)
templates = Jinja2Templates(directory=templates_path)

# Create static files directory
static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Initialize the connector
if CONNECTOR_AVAILABLE:
    try:
        # Create LangChain service
        langchain_service = LangChainService()
        
        # Create connector
        connector = HitomiLangChainConnector(
            langchain_service=langchain_service,
            temp_dir=os.path.join(os.path.dirname(__file__), "temp"),
            queue_size=5,
            frame_interval=2
        )
        logger.info("Hitomi-LangChain connector initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connector: {e}")
        connector = None
else:
    connector = None
    logger.warning("Hitomi-LangChain connector not available")

# Define request models
class VideoAnalysisRequest(BaseModel):
    url: str
    query: Optional[str] = None

# Define routes
@app.get("/")
async def home(request: Request):
    """Render the home page."""
    # Create a simple HTML template
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hitomi-LangChain Demo</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1 {
                color: #333;
            }
            .container {
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            input, textarea {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 3px;
                cursor: pointer;
            }
            button:hover {
                background-color: #45a049;
            }
            #results {
                margin-top: 20px;
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 5px;
                display: none;
            }
            .frame-preview {
                max-width: 100%;
                margin-top: 10px;
            }
            .status {
                padding: 10px;
                border-radius: 3px;
                margin-bottom: 10px;
            }
            .status.error {
                background-color: #ffebee;
                color: #c62828;
            }
            .status.success {
                background-color: #e8f5e9;
                color: #2e7d32;
            }
            .status.info {
                background-color: #e3f2fd;
                color: #1565c0;
            }
        </style>
    </head>
    <body>
        <h1>Hitomi-LangChain Connector Demo</h1>
        
        <div class="status info">
            <strong>Status:</strong> 
            {% if connector_available %}
                Connector is available and ready for use.
            {% else %}
                Connector is not available. Some dependencies may be missing.
            {% endif %}
        </div>
        
        <div class="container">
            <h2>Video Analysis</h2>
            <form id="videoForm">
                <div>
                    <label for="videoUrl">Video URL:</label>
                    <input type="text" id="videoUrl" name="url" placeholder="Enter a YouTube or other video URL" required>
                </div>
                <div>
                    <label for="videoQuery">Question about the video (optional):</label>
                    <textarea id="videoQuery" name="query" placeholder="What would you like to know about this video?"></textarea>
                </div>
                <button type="submit">Analyze Video</button>
            </form>
        </div>
        
        <div id="results">
            <h2>Analysis Results</h2>
            <div id="jobStatus" class="status info">Processing...</div>
            <div id="framePreview"></div>
            <div id="analysisOutput"></div>
        </div>
        
        <script>
            document.getElementById('videoForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const videoUrl = document.getElementById('videoUrl').value;
                const videoQuery = document.getElementById('videoQuery').value;
                
                // Display results div
                document.getElementById('results').style.display = 'block';
                document.getElementById('jobStatus').innerHTML = 'Submitting job...';
                document.getElementById('jobStatus').className = 'status info';
                document.getElementById('analysisOutput').innerHTML = '';
                document.getElementById('framePreview').innerHTML = '';
                
                // Submit the job
                fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: videoUrl,
                        query: videoQuery
                    }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('jobStatus').innerHTML = 'Error: ' + data.error;
                        document.getElementById('jobStatus').className = 'status error';
                    } else {
                        const jobId = data.job_id;
                        document.getElementById('jobStatus').innerHTML = 'Job submitted. Job ID: ' + jobId;
                        
                        // Poll for job status
                        const statusInterval = setInterval(() => {
                            fetch(`/api/job/${jobId}`)
                                .then(response => response.json())
                                .then(statusData => {
                                    document.getElementById('jobStatus').innerHTML = 'Status: ' + statusData.status;
                                    
                                    // If job is complete
                                    if (statusData.status === 'completed') {
                                        clearInterval(statusInterval);
                                        document.getElementById('jobStatus').className = 'status success';
                                        
                                        // Get the results
                                        fetch(`/api/results/${jobId}`)
                                            .then(response => response.json())
                                            .then(resultsData => {
                                                if (resultsData.error) {
                                                    document.getElementById('analysisOutput').innerHTML = 'Error: ' + resultsData.error;
                                                } else {
                                                    let outputHtml = '<h3>Video Analysis Summary</h3>';
                                                    outputHtml += '<pre>' + resultsData.summary + '</pre>';
                                                    
                                                    if (resultsData.frame_analyses) {
                                                        outputHtml += '<h3>Frame Analyses</h3>';
                                                        resultsData.frame_analyses.forEach((analysis, index) => {
                                                            outputHtml += `<div>
                                                                <h4>Frame ${index + 1} (${analysis.timestamp_str})</h4>
                                                                <img src="data:image/jpeg;base64,${analysis.image_data}" class="frame-preview">
                                                                <p>${analysis.text}</p>
                                                            </div>`;
                                                        });
                                                    }
                                                    
                                                    document.getElementById('analysisOutput').innerHTML = outputHtml;
                                                }
                                            });
                                    }
                                    // If job failed
                                    else if (statusData.status === 'failed') {
                                        clearInterval(statusInterval);
                                        document.getElementById('jobStatus').className = 'status error';
                                        document.getElementById('jobStatus').innerHTML = 'Job failed: ' + statusData.error;
                                    }
                                });
                        }, 2000);
                    }
                })
                .catch(error => {
                    document.getElementById('jobStatus').innerHTML = 'Error: ' + error.message;
                    document.getElementById('jobStatus').className = 'status error';
                });
            });
        </script>
    </body>
    </html>
    """
    
    # Write the template to the templates directory
    template_path = os.path.join(templates_path, "index.html")
    with open(template_path, "w") as f:
        f.write(html_template)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "connector_available": connector is not None
    })

@app.post("/api/analyze")
async def analyze_video(request: VideoAnalysisRequest, background_tasks: BackgroundTasks):
    """Submit a video analysis job."""
    if not connector:
        raise HTTPException(status_code=503, detail="Connector not available")
    
    try:
        # Submit the job
        job = connector.submit_video_analysis_job(request.url, request.query)
        return {"job_id": job["job_id"]}
    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a job."""
    if not connector:
        raise HTTPException(status_code=503, detail="Connector not available")
    
    try:
        status = connector.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results/{job_id}")
async def get_job_results(job_id: str):
    """Get the results of a completed job."""
    if not connector:
        raise HTTPException(status_code=503, detail="Connector not available")
    
    try:
        status = connector.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if status["status"] != "completed":
            return {"error": f"Job is not completed. Current status: {status['status']}"}
        
        # Get results
        results = status.get("results", {})
        return results
    except Exception as e:
        logger.error(f"Error getting job results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/frame/{job_id}/{frame_index}")
async def get_frame(job_id: str, frame_index: int):
    """Get a specific frame from a job."""
    if not connector:
        raise HTTPException(status_code=503, detail="Connector not available")
    
    try:
        frame_data = connector.get_frame_preview(job_id, frame_index)
        if not frame_data:
            raise HTTPException(status_code=404, detail="Frame not found")
        
        return {"image_data": frame_data}
    except Exception as e:
        logger.error(f"Error getting frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "connector_available": connector is not None,
        "timestamp": time.time()
    }

# Run the server if executed directly
if __name__ == "__main__":
    uvicorn.run("demo_server:app", host="0.0.0.0", port=8000, reload=True)
