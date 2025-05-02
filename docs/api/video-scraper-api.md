# TechSaaS Video Scraper API Documentation

The Video Scraper API provides programmatic access to the video extraction capabilities of the TechSaaS platform.

## Base URL

All API endpoints are accessible from the base URL:

```
http://localhost:5501
```

For production deployment, the API will be available at:

```
https://techsaas.tech/api/video-scraper
```

## Authentication

Currently, the API does not require authentication for local usage. For production use, authentication will be implemented with API keys.

## API Endpoints

### Service Status

```
GET /api/status
```

Returns the current operational status of the Video Scraper service.

**Response**
```json
{
  "service": "TechSaaS Video Scraper",
  "version": "1.0.0",
  "status": "operational"
}
```

### Supported Platforms

```
GET /api/video-scraper/platforms
```

Returns a list of supported video platforms and their capabilities.

**Response**
```json
[
  {
    "name": "YouTube",
    "domain": "youtube.com",
    "support_level": "full"
  },
  {
    "name": "Vimeo",
    "domain": "vimeo.com",
    "support_level": "full"
  },
  {
    "name": "Dailymotion",
    "domain": "dailymotion.com",
    "support_level": "full"
  }
]
```

### Extract Video Information

```
POST /api/video-scraper/info
```

Extracts video information from a URL. This is an asynchronous operation that returns a job ID for tracking.

**Request Body**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response**
```json
{
  "job_id": "12345678-abcd-1234-efgh-123456789012",
  "status": "processing",
  "message": "Video information extraction in progress"
}
```

### Check Job Status

```
GET /api/video-scraper/job/{job_id}
```

Checks the status of an extraction job. When completed, returns the video information.

**Response (Processing)**
```json
{
  "job_id": "12345678-abcd-1234-efgh-123456789012",
  "status": "processing",
  "progress": 0.45,
  "message": "Extracting video info..."
}
```

**Response (Completed)**
```json
{
  "job_id": "12345678-abcd-1234-efgh-123456789012",
  "status": "completed",
  "video_info": {
    "title": "Never Gonna Give You Up",
    "uploader": "Rick Astley",
    "duration": 212,
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "formats": [
      {
        "format_id": "22",
        "format_note": "720p",
        "ext": "mp4",
        "filesize": 19321772
      },
      {
        "format_id": "18",
        "format_note": "360p",
        "ext": "mp4",
        "filesize": 12342343
      }
    ]
  }
}
```

**Response (Failed)**
```json
{
  "job_id": "12345678-abcd-1234-efgh-123456789012",
  "status": "failed",
  "error": "Unable to extract video information: Video unavailable"
}
```

### Cancel Job

```
POST /api/video-scraper/job/{job_id}/cancel
```

Cancels an ongoing extraction job.

**Response**
```json
{
  "job_id": "12345678-abcd-1234-efgh-123456789012",
  "status": "cancelled",
  "message": "Job cancelled successfully"
}
```

### Download Video

```
POST /api/video-scraper/download
```

Initiates a video download with the specified format.

**Request Body**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format_id": "22"
}
```

**Response**
```json
{
  "status": "download_started",
  "download_id": "download_12345678",
  "message": "Download started in background. Check status with the download ID."
}
```

### Check Download Status

```
GET /api/video-scraper/status/{download_id}
```

Checks the status of a download.

**Response (In Progress)**
```json
{
  "status": "in_progress",
  "progress": 0.45,
  "status_message": "Downloading: 45% complete"
}
```

**Response (Completed)**
```json
{
  "status": "completed",
  "filename": "video_12345.mp4",
  "size_bytes": 19321772,
  "download_url": "/api/video-scraper/download/video_12345.mp4"
}
```

**Response (Failed)**
```json
{
  "status": "failed",
  "error": "Download failed: Network error"
}
```

### List Downloads

```
GET /api/video-scraper/downloads
```

Lists all available downloads.

**Response**
```json
[
  {
    "filename": "video_12345.mp4",
    "size_bytes": 19321772,
    "created": "2025-05-01T12:34:56",
    "url": "/api/video-scraper/download/video_12345.mp4"
  },
  {
    "filename": "video_67890.mp4",
    "size_bytes": 8765432,
    "created": "2025-05-02T09:12:34",
    "url": "/api/video-scraper/download/video_67890.mp4"
  }
]
```

### Download File

```
GET /api/video-scraper/download/{filename}
```

Downloads a specific file.

**Response**
Binary file stream with appropriate Content-Type and Content-Disposition headers.

## Error Handling

All API errors follow a consistent format:

```json
{
  "error": "Error message describing what went wrong",
  "status_code": 400
}
```

### Common Error Codes

- `400` - Bad Request (invalid parameters)
- `404` - Not Found (resource doesn't exist)
- `500` - Server Error (internal processing error)

## Rate Limiting

To prevent abuse, the API implements rate limiting:
- 60 requests per minute for extraction operations
- 10 concurrent downloads per client

## Webhooks (Coming Soon)

Future versions will support webhooks for asynchronous notifications when jobs complete.

```
POST /api/video-scraper/webhooks/register
```

**Request Body**
```json
{
  "callback_url": "https://your-server.com/webhook",
  "events": ["job_complete", "download_complete"]
}
```

## Client Libraries

Official client libraries are under development for the following languages:
- Python
- JavaScript/Node.js
- PHP
