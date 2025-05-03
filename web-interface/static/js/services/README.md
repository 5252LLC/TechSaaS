# TechSaaS API Client Services

This directory contains API client services that handle communication between the TechSaaS web interface and the backend API services.

## Video Analysis API Client

The Video Analysis API client (`api-client.js`) provides a standardized interface for interacting with the TechSaaS video analysis backend services. This client handles all the API calls related to video analysis, including submitting jobs, checking status, and retrieving results.

### Features

- **Standardized Error Handling**: Consistent error handling across all API calls with appropriate logging
- **Authentication Support**: Automatic token inclusion for authenticated requests
- **Request/Response Interceptors**: Pre-process requests and post-process responses
- **Comprehensive Video Analysis Methods**: Full coverage of the video analysis API endpoints

### Key Components

#### Base API Client

The base API client is an Axios instance configured with default settings:
- Base URL configuration
- Default timeout settings
- Standard headers
- Request/response interceptors for authentication and error handling

#### Video Analysis API Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `submitAnalysisJob` | Submit a video for analysis | `data`: FormData or Object, `options`: Object (optional) |
| `checkJobStatus` | Check the status of an analysis job | `jobId`: String |
| `getJobResults` | Get the results of a completed job | `jobId`: String |
| `getFrame` | Get a specific frame from a video | `jobId`: String, `frameIndex`: Number |
| `cancelJob` | Cancel a running analysis job | `jobId`: String |
| `exportResults` | Export analysis results in different formats | `jobId`: String, `format`: String (optional) |

### Usage

```javascript
import { videoAnalysisApi } from '../../services/api-client';

// Submit a video URL for analysis
const submitVideoUrl = async () => {
  try {
    const response = await videoAnalysisApi.submitAnalysisJob({
      video_url: 'https://example.com/video.mp4',
      extract_frames: true,
      object_detection: true
    });
    console.log('Job submitted:', response.job_id);
  } catch (error) {
    console.error('Error submitting job:', error);
  }
};

// Submit a video file for analysis
const submitVideoFile = async (videoFile) => {
  try {
    const formData = new FormData();
    formData.append('video_file', videoFile);
    const response = await videoAnalysisApi.submitAnalysisJob(formData);
    console.log('Job submitted:', response.job_id);
  } catch (error) {
    console.error('Error submitting job:', error);
  }
};

// Check job status
const checkStatus = async (jobId) => {
  try {
    const status = await videoAnalysisApi.checkJobStatus(jobId);
    console.log('Job status:', status.status);
  } catch (error) {
    console.error('Error checking job status:', error);
  }
};
```

### Integration with Components

The API client is integrated with the following React components:

1. **VideoAnalysisPanel**: Handles the overall video analysis workflow
2. **FrameGrid**: Displays and interacts with video frames retrieved from the API

## Security Considerations

- API keys and authentication tokens are stored securely and never exposed in client-side code
- All requests are made with appropriate security headers
- Rate limiting and error handling are implemented to prevent abuse
- Proper CORS configuration is enforced
