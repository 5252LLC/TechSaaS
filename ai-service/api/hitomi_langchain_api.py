#!/usr/bin/env python3
"""
Hitomi-LangChain API

This module provides RESTful API endpoints for the Hitomi-LangChain connector,
enabling access to multimodal video analysis capabilities via HTTP.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any
import time
from pathlib import Path
import base64

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import FastAPI components
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Body, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Import connector
from integration.hitomi_langchain_connector import HitomiLangChainConnector, ProcessingJob

# Import LangChain service for integration
from langchain.service import LangChainService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("hitomi_langchain_api")

# Create FastAPI app
app = FastAPI(
    title="Hitomi-LangChain API",
    description="API for multimodal video analysis using Hitomi and LangChain",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize connector
langchain_service = LangChainService()
connector = HitomiLangChainConnector(langchain_service=langchain_service)

# API models
class SubmitVideoAnalysisRequest(BaseModel):
    url: str
    query: Optional[str] = None
    extraction_job_id: Optional[str] = None
    
class VideoAnalysisResponse(BaseModel):
    job_id: str
    url: str
    query: Optional[str] = None
    status: str
    progress: int
    message: Optional[str] = None
    
class FramePreviewRequest(BaseModel):
    job_id: str
    frame_number: int

# API endpoints
@app.get("/")
async def root():
    """Root endpoint to check API status."""
    return {"status": "Hitomi-LangChain API is running"}

@app.post("/analyze", response_model=VideoAnalysisResponse)
async def analyze_video(request: SubmitVideoAnalysisRequest):
    """Submit a video for analysis."""
    try:
        job = connector.submit_video_analysis_job(
            url=request.url,
            query=request.query,
            extraction_job_id=request.extraction_job_id
        )
        
        return {
            "job_id": job["job_id"],
            "url": job["url"],
            "query": job["query"],
            "status": job["status"],
            "progress": job["progress"],
            "message": "Video analysis job submitted successfully"
        }
    except Exception as e:
        logger.error(f"Error submitting video analysis job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting video analysis job: {str(e)}"
        )

@app.get("/status/{job_id}", response_model=Dict[str, Any])
async def get_job_status(job_id: str):
    """Get the status of a video analysis job."""
    job_status = connector.get_job_status(job_id)
    if not job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return job_status

@app.get("/preview/{job_id}/{frame_number}")
async def get_frame_preview(job_id: str, frame_number: int):
    """Get a preview image for a specific frame."""
    image_data = connector.get_frame_preview(job_id, frame_number)
    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frame {frame_number} not found for job {job_id}"
        )
    
    # Decode base64 image data
    image_bytes = base64.b64decode(image_data)
    
    # Return as streaming response
    return StreamingResponse(
        content=iter([image_bytes]),
        media_type="image/jpeg"
    )

@app.get("/jobs", response_model=List[Dict[str, Any]])
async def list_jobs():
    """Get a list of all video analysis jobs."""
    return connector.list_jobs()

@app.delete("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a video analysis job."""
    success = connector.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return {"message": f"Job {job_id} cancelled successfully"}

@app.delete("/cleanup/{job_id}")
async def cleanup_job(job_id: str):
    """Clean up resources associated with a job."""
    success = connector.cleanup_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return {"message": f"Job {job_id} cleaned up successfully"}

@app.post("/memory/{job_id}")
async def store_in_memory(job_id: str, memory_key: Optional[str] = None):
    """Store video analysis results in LangChain memory."""
    job_status = connector.get_job_status(job_id)
    if not job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job_status["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not completed yet"
        )
    
    # Use provided memory key or generate from job ID
    memory_key = memory_key or f"video_analysis_{job_id}"
    
    try:
        # Store in LangChain memory
        if hasattr(langchain_service, 'memory_manager'):
            langchain_service.memory_manager.add_message(
                memory_key, 
                f"Video Analysis Request: {job_status['url']} - {job_status['query'] if job_status.get('query') else 'No specific query'}",
                role="human"
            )
            langchain_service.memory_manager.add_message(
                memory_key,
                f"Video Analysis Result: {json.dumps(job_status.get('result', {}), indent=2)}",
                role="ai"
            )
            
            return {"message": f"Video analysis results stored in memory with key {memory_key}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LangChain memory manager not available"
            )
    except Exception as e:
        logger.error(f"Error storing video analysis results in memory: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error storing video analysis results in memory: {str(e)}"
        )

# Run the API server when executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
