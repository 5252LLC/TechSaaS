/**
 * End-to-End Integration Test for MultimodalVisualization Component
 * 
 * This test verifies the full integration between:
 * - MultimodalVisualization React component
 * - VideoAnalysisPanel container component
 * - Backend API endpoints
 * - Data processing pipeline
 */

// Import testing utilities
const { render, fireEvent, waitFor, screen } = require('@testing-library/react');
const { rest } = require('msw');
const { setupServer } = require('msw/node');
const fetch = require('node-fetch');

// Import components to test
const { VideoAnalysisPanel } = require('./VideoAnalysisPanel');
const { MultimodalVisualization } = require('./MultimodalVisualization');
const { videoAnalysisApi } = require('../../services/api-client');

// Mock data for tests
const mockAnalysisResults = {
  jobId: "test-job-123",
  status: "completed",
  videoMetadata: {
    duration: 120.5,
    width: 1280,
    height: 720,
    fps: 30,
    codec: "h264",
    hasAudio: true
  },
  frames: [
    {
      frameNumber: 0,
      timestamp: 0,
      objects: [
        { id: 1, label: "person", confidence: 0.95, boundingBox: [10, 10, 100, 200] }
      ],
      keyFrame: true,
      annotations: ["Start of video segment"]
    },
    {
      frameNumber: 30,
      timestamp: 1.0,
      objects: [
        { id: 1, label: "person", confidence: 0.97, boundingBox: [15, 12, 105, 205] },
        { id: 2, label: "car", confidence: 0.89, boundingBox: [200, 300, 100, 50] }
      ],
      keyFrame: false,
      annotations: []
    }
  ],
  audioSegments: [
    {
      startTime: 0,
      endTime: 10.5,
      speaker: "Speaker A",
      transcript: "Welcome to our demonstration of multimodal analysis.",
      sentiment: "positive"
    },
    {
      startTime: 10.5,
      endTime: 15.2,
      speaker: "Speaker B",
      transcript: "This technology combines video, audio, and text analysis.",
      sentiment: "neutral"
    }
  ],
  textContent: {
    summary: "This video demonstrates multimodal analysis technology with examples of visual object detection and audio transcription.",
    entities: [
      { entity: "multimodal analysis", type: "TECHNOLOGY", count: 3 },
      { entity: "object detection", type: "FEATURE", count: 1 }
    ],
    sentiment: {
      overall: 0.75,  // Range: -1 (negative) to 1 (positive)
      segments: [
        { timestamp: 0, value: 0.8 },
        { timestamp: 10, value: 0.6 }
      ]
    }
  },
  crossModalConnections: [
    {
      id: "conn-1",
      timestamp: 5.2,
      primaryModality: "visual",
      primaryContent: "Person gesturing",
      relatedModalities: [
        { modality: "audio", content: "Welcome to our demonstration", confidence: 0.92 },
        { modality: "text", content: "demonstration of multimodal analysis", confidence: 0.85 }
      ]
    },
    {
      id: "conn-2",
      timestamp: 12.5,
      primaryModality: "audio",
      primaryContent: "This technology combines...",
      relatedModalities: [
        { modality: "visual", content: "Technology diagram shown", confidence: 0.88 }
      ]
    }
  ]
};

// Setup mock server
const server = setupServer(
  // Mock job submission endpoint
  rest.post('/api/video-analysis/jobs', (req, res, ctx) => {
    return res(ctx.json({
      success: true,
      jobId: 'test-job-123'
    }));
  }),
  
  // Mock job status endpoint
  rest.get('/api/video-analysis/jobs/:jobId/status', (req, res, ctx) => {
    const { jobId } = req.params;
    return res(ctx.json({
      jobId,
      status: 'completed',
      progress: 100
    }));
  }),
  
  // Mock results endpoint
  rest.get('/api/video-analysis/jobs/:jobId/results', (req, res, ctx) => {
    return res(ctx.json({
      success: true,
      data: mockAnalysisResults
    }));
  })
);

// Setup and teardown for tests
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Helper function to setup test component
function renderVideoAnalysisPanel() {
  return render(<VideoAnalysisPanel />);
}

// Tests
describe('Multimodal Analysis Integration Tests', () => {
  test('VideoAnalysisPanel loads and renders MultimodalVisualization component', async () => {
    const { getByText, getByLabelText } = renderVideoAnalysisPanel();
    
    // Check that the panel renders
    expect(getByText('Video Analysis')).toBeInTheDocument();
    
    // Fill out the form
    fireEvent.change(getByLabelText('Video URL'), {
      target: { value: 'https://example.com/sample.mp4' }
    });
    
    // Submit the form
    fireEvent.click(getByText('Analyze Video'));
    
    // Wait for the job to complete
    await waitFor(() => {
      expect(getByText('Analysis Results')).toBeInTheDocument();
    });
    
    // Check that the multimodal tab exists
    expect(getByText('Multimodal Analysis')).toBeInTheDocument();
    
    // Click the multimodal tab
    fireEvent.click(getByText('Multimodal Analysis'));
    
    // Verify that MultimodalVisualization component renders
    await waitFor(() => {
      expect(getByText('Cross-Modal Connections')).toBeInTheDocument();
    });
  });

  test('MultimodalVisualization correctly displays analysis results', async () => {
    // Direct rendering of the MultimodalVisualization component
    const { getByText, getAllByText } = render(
      <MultimodalVisualization 
        analysisResults={mockAnalysisResults}
        jobId="test-job-123"
      />
    );
    
    // Check that the component displays cross-modal connections
    expect(getByText('Cross-Modal Connections')).toBeInTheDocument();
    expect(getByText('Content Understanding')).toBeInTheDocument();
    expect(getByText('Audio Analysis')).toBeInTheDocument();
    
    // Verify specific content from mock data is displayed
    expect(getByText('Person gesturing')).toBeInTheDocument();
    expect(getByText('This technology combines video, audio, and text analysis.')).toBeInTheDocument();
    expect(getByText('Welcome to our demonstration of multimodal analysis.')).toBeInTheDocument();
  });

  test('MultimodalVisualization handles data loading states', async () => {
    // Setup server to delay response
    server.use(
      rest.get('/api/video-analysis/jobs/:jobId/results', (req, res, ctx) => {
        return res(ctx.delay(500), ctx.json({
          success: true,
          data: mockAnalysisResults
        }));
      })
    );
    
    const { getByText, getByTestId } = render(
      <VideoAnalysisPanel initialJobId="test-job-123" />
    );
    
    // Verify loading state is shown
    expect(getByTestId('loading-indicator')).toBeInTheDocument();
    
    // Wait for data to load
    await waitFor(() => {
      expect(getByText('Analysis Results')).toBeInTheDocument();
    });
  });

  test('MultimodalVisualization handles error states', async () => {
    // Setup server to return error
    server.use(
      rest.get('/api/video-analysis/jobs/:jobId/results', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({
          success: false,
          error: 'Internal server error'
        }));
      })
    );
    
    const { getByText } = render(
      <VideoAnalysisPanel initialJobId="error-job-456" />
    );
    
    // Wait for error message
    await waitFor(() => {
      expect(getByText(/Error loading analysis results/i)).toBeInTheDocument();
    });
  });

  test('End-to-end flow from job submission to multimodal results display', async () => {
    const { getByText, getByLabelText } = renderVideoAnalysisPanel();
    
    // Fill form
    fireEvent.change(getByLabelText('Video URL'), {
      target: { value: 'https://example.com/sample.mp4' }
    });
    
    // Enable multimodal analysis option
    fireEvent.click(getByLabelText('Enable multimodal analysis'));
    
    // Submit form
    fireEvent.click(getByText('Analyze Video'));
    
    // Wait for job submission
    await waitFor(() => {
      expect(getByText(/Analysis in progress/i)).toBeInTheDocument();
    });
    
    // Wait for job completion
    await waitFor(() => {
      expect(getByText('Analysis Results')).toBeInTheDocument();
    }, { timeout: 3000 });
    
    // Click multimodal tab
    fireEvent.click(getByText('Multimodal Analysis'));
    
    // Verify content is displayed
    await waitFor(() => {
      expect(getByText('Cross-Modal Connections')).toBeInTheDocument();
      expect(getByText('Person gesturing')).toBeInTheDocument();
      expect(getByText('This video demonstrates multimodal analysis')).toBeInTheDocument();
    });
  });
});
