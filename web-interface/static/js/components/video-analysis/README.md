# Video Analysis Components

## Overview

This directory contains React components for video analysis functionality in the TechSaaS platform. These components work together with the AI service's video analysis API to provide a complete video analysis solution.

## Components

### VideoAnalysisPanel

The main container component that handles:
- Video input (URL or file upload)
- Analysis options selection
- Job submission and monitoring
- Results display via tabs

### TabbedInterface

A reusable tabbed navigation component used by VideoAnalysisPanel to organize different views:
- Summary view
- Frames view
- Objects view
- Timeline view

### FrameGrid

A component for displaying and interacting with video frames:
- Grid display of extracted frames
- Search and filtering capabilities
- Frame detail view on click
- Object detection visualization

## API Integration

Components connect to the following endpoints:
- `${API_BASE_URL}/video/analyze` - For submitting analysis jobs
- `${API_BASE_URL}/video/job-status/:id` - For checking job status
- `${API_BASE_URL}/video/results/:id` - For fetching analysis results

Where `API_BASE_URL` defaults to `http://localhost:8000/api` but can be set via environment variables.

## Usage

The video analysis panel can be initialized in your HTML with:

```html
<div id="video-analysis-container"></div>
<script src="js/components/video-analysis/index.js"></script>
```

## Data Format

The components expect the analysis results in the following format:

```javascript
{
  // Video metadata
  duration: Number,           // Video duration in seconds
  resolution: {               // Video resolution
    width: Number,
    height: Number
  },
  format: String,             // Video format (e.g., "mp4")
  
  // Analysis results
  summary: String,            // Text summary of video content
  frames: [                   // Array of extracted frames
    {
      frame_number: Number,   // Frame number in video
      timestamp: Number,      // Timestamp in seconds
      timestamp_str: String,  // Formatted timestamp (MM:SS)
      image_data: String,     // Base64 encoded JPEG
      is_key_frame: Boolean,  // Whether this is a key frame
      text: String,           // Text description of frame
      objects: [              // Objects detected in this frame
        {
          class: String,      // Object class name
          confidence: Number, // Detection confidence (0-1)
          bbox: [x, y, w, h]  // Bounding box coordinates
        }
      ],
      metadata: {             // Optional additional metadata
        // Key-value pairs
      }
    }
  ],
  
  // Object detection results grouped by class
  objects: {
    [className]: [            // Array of detections for this class
      {
        frame_number: Number,
        timestamp: Number,
        confidence: Number,
        bbox: [x, y, w, h]
      }
    ]
  },
  
  // Scene detection results
  scenes: [
    {
      start_time: Number,     // Start time in seconds
      end_time: Number,       // End time in seconds
      start_time_str: String, // Formatted start time
      end_time_str: String,   // Formatted end time
      duration: Number,       // Scene duration in seconds
      keyframe_index: Number, // Index into frames array
      description: String     // Optional scene description
    }
  ],
  
  // Optional key frame indices
  key_frames: [Number]        // Indices into frames array
}
```

## Troubleshooting

### Common Issues:

1. **No frames displaying**: Ensure frames are properly extracted and image_data is base64-encoded JPEG.

2. **Job status not updating**: Check that the API endpoints are correctly configured and returning the expected format.

3. **Objects not showing**: Verify that object detection was enabled and that objects are returned in the expected format.

## Future Enhancements

Planned enhancements include:
- Timeline visualization for object appearances
- Export functionality for analysis results
- Integration with LangChain for advanced multimodal processing
- Custom plugin support for video analysis algorithms

## Related Documentation

- See the TASK_JOURNAL.md for implementation details and progress
- API documentation is available in /docs/api/video-analysis.md
- For LangChain integration plans, see /docs/architecture/langchain-integration.md
