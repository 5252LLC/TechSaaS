# Multimodal Processing API Reference

This document provides a comprehensive reference for the TechSaaS platform's multimodal processing API endpoints. These endpoints enable developers to leverage the platform's powerful multimodal analysis capabilities.

## Base URL

All API endpoints are accessible through the base URL:
```
https://api.techsaas.example.com/v1
```

For local development:
```
http://localhost:5252/api
```

## Authentication

All API requests require authentication using an API key in the request header:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### Multimodal Analysis

#### Submit Multimodal Analysis Job

```
POST /video-analysis/jobs
```

Submit a new video analysis job with multimodal processing options.

**Request Body:**
```json
{
  "video_url": "https://example.com/video.mp4",
  "options": {
    "enable_multimodal": true,
    "analyze_audio": true,
    "extract_text": true,
    "detect_objects": true,
    "cross_reference": true,
    "speech_to_text": true,
    "scene_detection": true,
    "entity_extraction": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "jobId": "job-123456",
  "message": "Job submitted successfully",
  "estimatedTimeSeconds": 120
}
```

**Status Codes:**
- `200 OK`: Job submitted successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Invalid or missing API key
- `413 Payload Too Large`: Video file too large
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

#### Check Job Status

```
GET /video-analysis/jobs/{jobId}/status
```

Check the status of a multimodal analysis job.

**Path Parameters:**
- `jobId`: The ID of the job to check

**Response:**
```json
{
  "jobId": "job-123456",
  "status": "in_progress",
  "progress": 45,
  "message": "Processing video frames",
  "estimatedRemainingSeconds": 67
}
```

**Status Values:**
- `queued`: Job is in the queue awaiting processing
- `preparing`: System is preparing resources for job execution
- `in_progress`: Job is currently being processed
- `completed`: Job has completed successfully
- `failed`: Job failed to complete
- `cancelled`: Job was cancelled by the user

#### Get Analysis Results

```
GET /video-analysis/jobs/{jobId}/results
```

Retrieve the results of a completed multimodal analysis job.

**Path Parameters:**
- `jobId`: The ID of the completed job

**Query Parameters:**
- `include_raw_data` (optional): Boolean flag to include raw analysis data (default: false)
- `format` (optional): Response format (json, csv) (default: json)

**Response:**
```json
{
  "success": true,
  "data": {
    "jobId": "job-123456",
    "status": "completed",
    "createdAt": "2025-05-03T12:45:30Z",
    "completedAt": "2025-05-03T12:48:15Z",
    "videoMetadata": {
      "duration": 120.5,
      "width": 1920,
      "height": 1080,
      "fps": 30,
      "codec": "h264",
      "hasAudio": true,
      "fileSize": 24156032
    },
    "frames": [
      {
        "frameNumber": 0,
        "timestamp": 0,
        "objects": [
          {
            "id": 1,
            "label": "person",
            "confidence": 0.95,
            "boundingBox": [10, 10, 100, 200]
          }
        ],
        "keyFrame": true,
        "annotations": ["Start of video segment"]
      }
    ],
    "audioSegments": [
      {
        "startTime": 0,
        "endTime": 10.5,
        "speaker": "Speaker A",
        "transcript": "Welcome to our demonstration of multimodal analysis.",
        "sentiment": "positive"
      }
    ],
    "textContent": {
      "summary": "This video demonstrates multimodal analysis technology with examples of visual object detection and audio transcription.",
      "entities": [
        { "entity": "multimodal analysis", "type": "TECHNOLOGY", "count": 3 },
        { "entity": "object detection", "type": "FEATURE", "count": 1 }
      ],
      "sentiment": {
        "overall": 0.75,
        "segments": [
          { "timestamp": 0, "value": 0.8 },
          { "timestamp": 10, "value": 0.6 }
        ]
      }
    },
    "crossModalConnections": [
      {
        "id": "conn-1",
        "timestamp": 5.2,
        "primaryModality": "visual",
        "primaryContent": "Person gesturing",
        "relatedModalities": [
          { "modality": "audio", "content": "Welcome to our demonstration", "confidence": 0.92 },
          { "modality": "text", "content": "demonstration of multimodal analysis", "confidence": 0.85 }
        ]
      }
    ]
  }
}
```

#### Cancel Job

```
POST /video-analysis/jobs/{jobId}/cancel
```

Cancel a multimodal analysis job that is queued or in progress.

**Path Parameters:**
- `jobId`: The ID of the job to cancel

**Response:**
```json
{
  "success": true,
  "message": "Job cancelled successfully"
}
```

### Model Information

#### List Available Models

```
GET /multimodal/models
```

List all available models for multimodal processing.

**Query Parameters:**
- `capability` (optional): Filter by capability (video, audio, text, image)
- `provider` (optional): Filter by provider (ollama, huggingface)

**Response:**
```json
{
  "models": [
    {
      "id": "ollama/llava-1.5",
      "name": "LLaVA 1.5",
      "provider": "ollama",
      "capabilities": ["image", "text"],
      "description": "Large Language and Vision Assistant model",
      "minRequiredMemoryGB": 8.0,
      "recommendedGPU": true,
      "loaded": true
    },
    {
      "id": "huggingface/microsoft/phi-3-mini",
      "name": "Phi-3 Mini",
      "provider": "huggingface",
      "capabilities": ["text"],
      "description": "Compact text generation model",
      "minRequiredMemoryGB": 2.0,
      "recommendedGPU": false,
      "loaded": false
    }
  ]
}
```

#### Get Model Information

```
GET /multimodal/models/{modelId}
```

Get detailed information about a specific model.

**Path Parameters:**
- `modelId`: The ID of the model

**Response:**
```json
{
  "id": "ollama/phi-vision:latest",
  "name": "Phi Vision",
  "provider": "ollama",
  "capabilities": ["image", "text", "video"],
  "description": "Multimodal vision-language model",
  "parameters": {
    "temperature": {
      "default": 0.7,
      "min": 0.0,
      "max": 1.0,
      "description": "Controls randomness in generation"
    },
    "top_p": {
      "default": 0.9,
      "min": 0.0,
      "max": 1.0,
      "description": "Controls diversity via nucleus sampling"
    }
  },
  "performance": {
    "averageProcessingTimePerFrameMs": 120,
    "maxBatchSize": 16,
    "throughputFPS": 8
  },
  "loaded": true,
  "lastUsed": "2025-05-03T10:15:22Z"
}
```

### System Status

#### Get Multimodal System Status

```
GET /multimodal/status
```

Get the current status of the multimodal processing system.

**Response:**
```json
{
  "status": "operational",
  "activeModels": ["ollama/llava-1.5", "ollama/phi-vision:latest"],
  "availableModalities": ["video", "audio", "text", "image"],
  "queueStatus": {
    "activeJobs": 2,
    "queuedJobs": 5,
    "estimatedQueueTimeSeconds": 180
  },
  "resourceUtilization": {
    "cpuPercent": 65,
    "memoryPercent": 78,
    "gpuPercent": 92
  },
  "uptime": "3d 7h 22m"
}
```

## Rate Limits

| Plan | Requests per minute | Jobs per day | Max video length | Max file size |
|------|---------------------|--------------|------------------|---------------|
| Free | 10                  | 5            | 5 minutes        | 100 MB        |
| Pro  | 60                  | 50           | 30 minutes       | 1 GB          |
| Enterprise | 300           | Unlimited    | 4 hours          | 10 GB         |

## Error Codes

| Code | Description |
|------|-------------|
| 1000 | General API error |
| 1001 | Invalid or unsupported video format |
| 1002 | Video processing error |
| 1003 | Model loading error |
| 1004 | Resource allocation error |
| 1005 | Cross-modal connection error |
| 1006 | Job queue full |
| 1007 | Processing timeout |

## Webhooks

You can configure webhooks to receive notifications about job status changes.

### Register Webhook

```
POST /webhooks
```

**Request Body:**
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["job.queued", "job.completed", "job.failed"],
  "secret": "your-webhook-secret"
}
```

**Response:**
```json
{
  "id": "wh-123456",
  "url": "https://your-server.com/webhook",
  "events": ["job.queued", "job.completed", "job.failed"],
  "created": "2025-05-03T11:30:45Z",
  "status": "active"
}
```

## SDK Integration

Code examples for integrating with the multimodal API using our official SDKs.

### Python

```python
from techsaas import MultimodalClient

# Initialize client
client = MultimodalClient(api_key="YOUR_API_KEY")

# Submit job
job = client.submit_job(
    video_url="https://example.com/video.mp4",
    options={
        "enable_multimodal": True,
        "analyze_audio": True,
        "extract_text": True
    }
)

# Poll for results
while not job.is_completed():
    print(f"Progress: {job.get_progress()}%")
    time.sleep(5)

# Get results
results = job.get_results()
print(results.cross_modal_connections)
```

### JavaScript

```javascript
import { MultimodalClient } from '@techsaas/client';

// Initialize client
const client = new MultimodalClient({ apiKey: 'YOUR_API_KEY' });

// Submit job
const job = await client.submitJob({
  videoUrl: 'https://example.com/video.mp4',
  options: {
    enableMultimodal: true,
    analyzeAudio: true,
    extractText: true
  }
});

// Poll for results
job.onProgressUpdate((progress) => {
  console.log(`Progress: ${progress}%`);
});

// Get results when complete
job.onComplete((results) => {
  console.log(results.crossModalConnections);
});
```

## Best Practices

1. **Optimize Video Before Upload**
   - Compress videos to reduce size without significant quality loss
   - Consider pre-processing to standardize resolution and format

2. **Selective Modality Processing**
   - Enable only the modalities you need (video, audio, text)
   - Disable cross-modal referencing for simple analyses to improve performance

3. **Handle Rate Limits**
   - Implement exponential backoff for retries
   - Cache results to avoid redundant API calls

4. **Result Processing**
   - Process large result sets incrementally
   - Store job IDs for future reference rather than full result objects

5. **Error Handling**
   - Implement robust error handling for all API requests
   - Check job status before requesting results
   
## Changelog

### v1.3.0 (May 2, 2025)
- Added support for multimodal processing
- Added cross-modal connection analysis
- Introduced sentiment analysis for audio segments

### v1.2.0 (April 15, 2025)
- Added support for video scene detection
- Enhanced object tracking capabilities
- Improved speech-to-text accuracy

### v1.1.0 (March 28, 2025)
- Added support for Hugging Face models
- Enhanced API error reporting
- Improved job queue management
