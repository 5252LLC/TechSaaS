/**
 * API Integration Tests for Video Analysis Components
 * 
 * This file contains tests to verify the proper integration between 
 * the Video Analysis UI components and the backend API endpoints.
 */

// Import required dependencies
import { videoAnalysisApi } from '../../services/api-client';
import { mount } from 'enzyme';
import React from 'react';
import VideoAnalysisPanel from './VideoAnalysisPanel';
import TimelineVisualization from './TimelineVisualization';
import HeatmapVisualization from './HeatmapVisualization';
import ObjectTrackingVisualization from './ObjectTrackingVisualization';

// Mock API responses
jest.mock('../../services/api-client', () => ({
  videoAnalysisApi: {
    submitAnalysisJob: jest.fn(),
    checkJobStatus: jest.fn(),
    getJobResults: jest.fn(),
    getFrame: jest.fn(),
    cancelJob: jest.fn(),
    exportResults: jest.fn()
  }
}));

describe('Video Analysis API Integration Tests', () => {
  
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('VideoAnalysisPanel API Integration', () => {
    
    test('submits analysis job with file upload', async () => {
      // Setup
      const mockFile = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      const mockJobId = 'test-job-123';
      
      videoAnalysisApi.submitAnalysisJob.mockResolvedValue({
        data: { jobId: mockJobId, status: 'pending' }
      });

      // Mount component
      const wrapper = mount(<VideoAnalysisPanel />);
      
      // Simulate file upload and submission
      const fileInput = wrapper.find('input[type="file"]');
      fileInput.simulate('change', { target: { files: [mockFile] } });
      
      const submitButton = wrapper.find('button[data-testid="submit-button"]');
      await submitButton.simulate('click');
      
      // Assertions
      expect(videoAnalysisApi.submitAnalysisJob).toHaveBeenCalled();
      const formData = videoAnalysisApi.submitAnalysisJob.mock.calls[0][0];
      expect(formData.get('video')).toBe(mockFile);
    });
    
    test('checks job status periodically', async () => {
      // Setup
      const mockJobId = 'test-job-123';
      
      videoAnalysisApi.checkJobStatus.mockResolvedValueOnce({
        data: { jobId: mockJobId, status: 'processing', progress: 50 }
      }).mockResolvedValueOnce({
        data: { jobId: mockJobId, status: 'completed', progress: 100 }
      });
      
      // Mount component with existing jobId
      const wrapper = mount(<VideoAnalysisPanel initialJobId={mockJobId} />);
      
      // Fast-forward timers
      jest.useFakeTimers();
      jest.advanceTimersByTime(5000);
      jest.useRealTimers();
      
      // Wait for state updates
      await new Promise(resolve => setTimeout(resolve, 0));
      wrapper.update();
      
      // Assertions
      expect(videoAnalysisApi.checkJobStatus).toHaveBeenCalledWith(mockJobId);
    });
    
    test('fetches results when job is complete', async () => {
      // Setup
      const mockJobId = 'test-job-123';
      const mockResults = {
        frames: [{ index: 0, objects: [] }],
        summary: { duration: 60, frameCount: 1800 }
      };
      
      videoAnalysisApi.checkJobStatus.mockResolvedValue({
        data: { jobId: mockJobId, status: 'completed', progress: 100 }
      });
      
      videoAnalysisApi.getJobResults.mockResolvedValue({
        data: mockResults
      });
      
      // Mount component with completed job
      const wrapper = mount(<VideoAnalysisPanel initialJobId={mockJobId} initialStatus="completed" />);
      
      // Wait for results fetch
      await new Promise(resolve => setTimeout(resolve, 0));
      wrapper.update();
      
      // Assertions
      expect(videoAnalysisApi.getJobResults).toHaveBeenCalledWith(mockJobId);
    });
  });
  
  describe('TimelineVisualization API Integration', () => {
    
    test('renders with analysis results', async () => {
      // Setup
      const mockJobId = 'test-job-123';
      const mockResults = {
        scenes: [
          { start: 0, end: 300, keyFrames: [0, 150, 299] }
        ],
        objects: [
          { frame: 0, class: 'person', confidence: 0.95 },
          { frame: 150, class: 'car', confidence: 0.85 }
        ]
      };
      
      // Mount component
      const wrapper = mount(
        <TimelineVisualization 
          jobId={mockJobId}
          analysisResults={mockResults}
        />
      );
      
      // Assertions
      expect(wrapper.find('.timeline-visualization')).toHaveLength(1);
      expect(wrapper.find('.scene-marker')).toHaveLength(1);
      expect(wrapper.find('.object-detection')).toHaveLength(2);
    });
  });
  
  describe('HeatmapVisualization API Integration', () => {
    
    test('renders heatmap with object detections', () => {
      // Setup
      const mockAnalysisResults = {
        objects: [
          { frame: 0, class: 'person', bbox: [0.1, 0.2, 0.3, 0.4], confidence: 0.95 },
          { frame: 0, class: 'car', bbox: [0.5, 0.6, 0.2, 0.1], confidence: 0.85 }
        ],
        summary: { frameWidth: 1920, frameHeight: 1080 }
      };
      
      // Mount component
      const wrapper = mount(
        <HeatmapVisualization analysisResults={mockAnalysisResults} />
      );
      
      // Assertions
      expect(wrapper.find('.heatmap-visualization')).toHaveLength(1);
      expect(wrapper.find('canvas')).toHaveLength(1);
    });
  });
  
  describe('ObjectTrackingVisualization API Integration', () => {
    
    test('loads frame images from API', async () => {
      // Setup
      const mockJobId = 'test-job-123';
      const mockFrameData = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAA';
      
      videoAnalysisApi.getFrame.mockResolvedValue({
        data: { imageData: mockFrameData }
      });
      
      const mockAnalysisResults = {
        tracks: [
          { id: 1, frames: [0, 1, 2], class: 'person', positions: [[0.1, 0.2], [0.15, 0.25], [0.2, 0.3]] }
        ],
        summary: { frameCount: 30 }
      };
      
      // Mount component
      const wrapper = mount(
        <ObjectTrackingVisualization 
          jobId={mockJobId}
          analysisResults={mockAnalysisResults}
        />
      );
      
      // Simulate frame navigation
      const nextFrameButton = wrapper.find('.next-frame-button');
      await nextFrameButton.simulate('click');
      
      // Wait for frame loading
      await new Promise(resolve => setTimeout(resolve, 0));
      
      // Assertions
      expect(videoAnalysisApi.getFrame).toHaveBeenCalledWith(mockJobId, 1);
    });
  });
});
