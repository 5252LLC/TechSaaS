# Multimodal Processing Integration

The TechSaaS platform's Multimodal Processing Integration module enables analysis of content using multiple modalities (video, audio, text, images) simultaneously, providing richer insights and cross-modal correlations.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Visualization Components](#visualization-components)
- [Integration Testing](#integration-testing)
- [Development Guidelines](#development-guidelines)
- [Troubleshooting](#troubleshooting)

## Overview

The Multimodal Processing Integration combines various data modalities to provide comprehensive content understanding:

- **Video Analysis**: Object detection, scene segmentation, action recognition
- **Audio Analysis**: Speech recognition, speaker diarization, audio event detection
- **Text Analysis**: Natural language understanding, entity extraction, sentiment analysis
- **Cross-Modal Analysis**: Temporal and semantic connections across modalities

This unified approach enables the TechSaaS platform to extract deeper insights from multimedia content than would be possible with single-modality analysis.

## Architecture

The multimodal processing system follows a layered architecture:

1. **Web Interface Layer**
   - `VideoAnalysisPanel`: Main UI container component
   - `MultimodalVisualization`: Component for displaying multimodal results
   - Various specialized visualization components for different result types

2. **API Layer**
   - REST endpoints for job submission, status checking, and result retrieval
   - WebSocket support for real-time updates during processing

3. **Processing Layer**
   - `UnifiedModelManager`: Manages AI models across different providers
   - `ProcessorFactory`: Creates appropriate processors for different content types
   - `MultimodalProcessor`: Coordinates analysis across modalities

4. **Model Layer**
   - Integrations with Ollama, Hugging Face, and other model providers
   - Support for local and remote model execution

## Components

### Core Components

#### UnifiedModelManager

Manages loading, unloading, and execution of AI models across different providers:

```python
# Example usage:
manager = UnifiedModelManager()
model_info = manager.get_model_info("ollama/llava-1.5")
if manager.is_model_available("ollama/llava-1.5"):
    manager.load_model("ollama/llava-1.5")
```

#### MultimodalProcessor

Processes multimedia content using multiple modalities:

```python
# Example usage:
processor = MultimodalProcessor(model_manager=model_manager)
result = processor.process(
    data={
        "video_path": "/path/to/video.mp4",
        "enable_audio_analysis": True,
        "enable_text_extraction": True
    },
    model_id="ollama/phi-vision:latest"
)
```

#### VideoAnalysisPanel

React component for video analysis job submission and results visualization:

```jsx
// Example usage:
<VideoAnalysisPanel 
  initialJobId={jobId} 
  enableMultimodal={true} 
/>
```

#### MultimodalVisualization

React component for displaying multimodal analysis results:

```jsx
// Example usage:
<MultimodalVisualization 
  analysisResults={results}
  jobId="job-123"
/>
```

### Supporting Components

- `ImageProcessor`: Processes image content
- `TextProcessor`: Processes text content
- `AudioProcessor`: Processes audio content
- `VideoProcessor`: Processes video content
- `CrossModalConnector`: Establishes connections between different modalities

## Setup and Installation

### Prerequisites

- Python 3.9+
- Node.js 16+
- CUDA-compatible GPU (recommended for video processing)
- 16GB+ RAM

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/525277x/techsaas-platform.git
   cd techsaas-platform
   ```

2. Install Python dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Install Ollama (for local model execution):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

4. Install JavaScript dependencies:
   ```bash
   cd web-interface
   npm install
   cd ..
   ```

5. Configure the models:
   ```bash
   # Pull required models for multimodal processing
   ollama pull llava-1.5
   ollama pull phi-vision
   ```

## Usage

### Web Interface

1. Start the web server:
   ```bash
   cd web-interface
   python app.py
   ```

2. Navigate to http://localhost:5252 in your browser

3. Upload a video or provide a URL

4. Enable multimodal analysis options

5. Submit the job and view results in the MultimodalVisualization component

### API Usage

```python
import requests

# Submit a job
response = requests.post(
    "http://localhost:5252/api/video-analysis/jobs",
    json={
        "video_url": "https://example.com/video.mp4",
        "options": {
            "enable_multimodal": True,
            "analyze_audio": True,
            "extract_text": True,
            "detect_objects": True
        }
    }
)
job_id = response.json()["jobId"]

# Check job status
status_response = requests.get(
    f"http://localhost:5252/api/video-analysis/jobs/{job_id}/status"
)
status = status_response.json()["status"]

# Get results when job is completed
if status == "completed":
    results_response = requests.get(
        f"http://localhost:5252/api/video-analysis/jobs/{job_id}/results"
    )
    results = results_response.json()["data"]
```

## API Reference

### Video Analysis API

#### POST /api/video-analysis/jobs

Submit a new video analysis job.

**Request Body:**
```json
{
  "video_url": "https://example.com/video.mp4",
  "options": {
    "enable_multimodal": true,
    "analyze_audio": true,
    "extract_text": true,
    "detect_objects": true,
    "cross_reference": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "jobId": "job-123456",
  "message": "Job submitted successfully"
}
```

#### GET /api/video-analysis/jobs/{jobId}/status

Check the status of a video analysis job.

**Response:**
```json
{
  "jobId": "job-123456",
  "status": "in_progress",
  "progress": 45,
  "message": "Processing video frames"
}
```

#### GET /api/video-analysis/jobs/{jobId}/results

Get the results of a completed video analysis job.

**Response:**
```json
{
  "success": true,
  "data": {
    "jobId": "job-123456",
    "status": "completed",
    "videoMetadata": { ... },
    "frames": [ ... ],
    "audioSegments": [ ... ],
    "textContent": { ... },
    "crossModalConnections": [ ... ]
  }
}
```

## Visualization Components

### MultimodalVisualization

The main component for displaying multimodal analysis results with the following features:

- **Cross-Modal Connections**: Visualizes connections between different modalities
- **Content Understanding**: Displays textual summaries and extracted entities
- **Audio Analysis**: Shows speech transcription and audio event timeline
- **Visual Analysis**: Presents annotated frames and object tracking

### TimelineVisualization

Visualizes temporal relationships in multimodal data:

- Timeline representation of video segments
- Speech and audio events
- Key frames and scene transitions

### HeatmapVisualization

Generates spatial heatmaps showing:

- Object detection density
- Visual attention areas
- Motion patterns

### ObjectTrackingVisualization

Tracks objects across video frames:

- Persistent object IDs
- Motion trajectories
- Object interactions

## Integration Testing

The multimodal system includes comprehensive integration tests to verify correct functionality:

### Python Integration Tests

Located in `/ai-service/tests/integration/test_multimodal_integration.py`, these tests verify:

- Processing pipeline integration
- Model manager functionality
- Cross-modal analysis
- Error handling

Run the tests with:
```bash
cd ai-service
python -m unittest tests/integration/test_multimodal_integration.py
```

### JavaScript Integration Tests

Located in `/web-interface/static/js/components/video-analysis/test-multimodal-integration.js`, these tests verify:

- UI component integration
- API communication
- Result visualization
- Error handling and loading states

Run the tests with:
```bash
cd web-interface
npm test -- --testPathPattern=test-multimodal-integration
```

## Development Guidelines

### Adding a New Modality

1. Create a new processor class that extends `BaseProcessor`
2. Implement the `process()` method for the new modality
3. Register the processor with `ProcessorFactory`
4. Update `MultimodalProcessor` to incorporate the new modality
5. Add visualization components for the new modality

### Integrating a New Model Provider

1. Create a provider-specific adapter in the `models` directory
2. Update `UnifiedModelManager` to support the new provider
3. Register capabilities for models from the new provider
4. Add appropriate error handling for provider-specific issues

## Troubleshooting

### Common Issues

#### Model Loading Failures

**Symptoms:** Jobs fail with "Model loading error" or timeout errors

**Solutions:**
- Check system memory availability
- Ensure GPU drivers are up to date
- Verify model availability in the configured provider

#### Cross-Modal Integration Errors

**Symptoms:** Missing cross-modal connections or modalities processed in isolation

**Solutions:**
- Check `enable_cross_reference` flag is set to true
- Verify all required processors are registered
- Check synchronization between different modal processors

#### Visualization Component Errors

**Symptoms:** Blank visualization or JavaScript console errors

**Solutions:**
- Check browser console for detailed error messages
- Verify the structure of analysis results matches expected format
- Test individual visualization components in isolation

### Logs and Diagnostics

- Application logs: `/logs/application.log`
- Processing logs: `/logs/processing.log`
- Model logs: `/logs/models.log`

Enable debug logging by setting:
```
export DEBUG_LEVEL=debug
```

## Contributing

Please see the [Contributing Guide](../CONTRIBUTING.md) for details on code style, branch naming, and pull request processes.
