import React, { useState, useEffect } from 'react';
import FrameGrid from './FrameGrid';
import TabbedInterface from './TabbedInterface';
import TimelineVisualization from './TimelineVisualization';
import HeatmapVisualization from './HeatmapVisualization';
import ObjectTrackingVisualization from './ObjectTrackingVisualization';
import { videoAnalysisApi } from '../../services/api-client';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

const VideoAnalysisPanel = () => {
  const [videoUrl, setVideoUrl] = useState('');
  const [fileUpload, setFileUpload] = useState(null);
  const [analysisOptions, setAnalysisOptions] = useState({
    extract_frames: true,
    object_detection: true,
    scene_detection: true,
    text_analysis: true
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [statusCheckInterval, setStatusCheckInterval] = useState(null);

  // Check job status periodically if jobId exists
  useEffect(() => {
    if (jobId && jobStatus !== 'completed' && jobStatus !== 'failed') {
      const intervalId = setInterval(() => {
        checkJobStatus(jobId);
      }, 3000);
      
      setStatusCheckInterval(intervalId);
      
      return () => clearInterval(intervalId);
    }
    
    return () => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    };
  }, [jobId, jobStatus]);

  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    };
  }, []);

  const handleVideoUrlChange = (e) => {
    setVideoUrl(e.target.value);
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFileUpload(e.target.files[0]);
      setVideoUrl(''); // Clear URL if file is uploaded
    }
  };

  const handleOptionChange = (e) => {
    const { name, checked } = e.target;
    setAnalysisOptions(prev => ({
      ...prev,
      [name]: checked
    }));
  };

  const submitAnalysisJob = async () => {
    setError(null);
    setIsSubmitting(true);
    
    try {
      let data;
      let options = { ...analysisOptions };
      
      if (fileUpload) {
        data = new FormData();
        data.append('video_file', fileUpload);
        
        // Add analysis options to formData
        Object.entries(analysisOptions).forEach(([key, value]) => {
          data.append(key, value.toString());
        });
      } else if (videoUrl) {
        data = { video_url: videoUrl, ...options };
      } else {
        throw new Error('Please provide a video URL or upload a file');
      }
      
      const response = await videoAnalysisApi.submitAnalysisJob(data);
      
      if (response && response.job_id) {
        setJobId(response.job_id);
        setJobStatus('processing');
        
        // Start checking status immediately
        checkJobStatus(response.job_id);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      setError(err.message || 'An error occurred during job submission');
      setJobStatus('failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const checkJobStatus = async (id) => {
    try {
      const statusData = await videoAnalysisApi.checkJobStatus(id);
      
      setJobStatus(statusData.status);
      
      // If job is complete, fetch results
      if (statusData.status === 'completed') {
        fetchJobResults(id);
      } else if (statusData.status === 'failed') {
        setError(statusData.error || 'Analysis failed without specific error details');
      }
    } catch (err) {
      console.error('Error checking job status:', err);
      setError('Failed to check job status. Please try again.');
    }
  };

  const fetchJobResults = async (id) => {
    try {
      const resultsData = await videoAnalysisApi.getJobResults(id);
      setAnalysisResults(resultsData);
    } catch (err) {
      console.error('Error fetching job results:', err);
      setError('Failed to fetch analysis results. Please try again.');
    }
  };

  const cancelAnalysisJob = async () => {
    try {
      if (jobId) {
        await videoAnalysisApi.cancelJob(jobId);
        setJobStatus('cancelled');
        setError('Analysis job cancelled');
        
        if (statusCheckInterval) {
          clearInterval(statusCheckInterval);
          setStatusCheckInterval(null);
        }
      }
    } catch (err) {
      console.error('Error cancelling job:', err);
      setError('Failed to cancel analysis job');
    }
  };

  const downloadResults = async (format = 'json') => {
    try {
      if (jobId && jobStatus === 'completed') {
        await videoAnalysisApi.exportResults(jobId, format);
      }
    } catch (err) {
      console.error(`Error exporting results as ${format}:`, err);
      setError(`Failed to export results as ${format}`);
    }
  };

  const renderInputForm = () => {
    return (
      <div className="input-form">
        <h3>Video Analysis</h3>
        
        <div className="form-group">
          <label>Video URL:</label>
          <input
            type="text"
            value={videoUrl}
            onChange={handleVideoUrlChange}
            placeholder="Enter video URL"
            disabled={!!fileUpload || isSubmitting}
            className="form-control"
          />
        </div>
        
        <div className="form-group">
          <label>Upload Video:</label>
          <input
            type="file"
            onChange={handleFileChange}
            accept="video/*"
            disabled={!!videoUrl || isSubmitting}
            className="form-control"
          />
        </div>
        
        <div className="options-group">
          <h4>Analysis Options</h4>
          
          <div className="checkbox-group">
            <label>
              <input
                type="checkbox"
                name="extract_frames"
                checked={analysisOptions.extract_frames}
                onChange={handleOptionChange}
                disabled={isSubmitting}
              /> 
              Extract Frames
            </label>
            
            <label>
              <input
                type="checkbox"
                name="object_detection"
                checked={analysisOptions.object_detection}
                onChange={handleOptionChange}
                disabled={isSubmitting}
              /> 
              Object Detection
            </label>
            
            <label>
              <input
                type="checkbox"
                name="scene_detection"
                checked={analysisOptions.scene_detection}
                onChange={handleOptionChange}
                disabled={isSubmitting}
              /> 
              Scene Detection
            </label>
            
            <label>
              <input
                type="checkbox"
                name="text_analysis"
                checked={analysisOptions.text_analysis}
                onChange={handleOptionChange}
                disabled={isSubmitting}
              /> 
              Text Analysis
            </label>
          </div>
        </div>
        
        <button 
          onClick={submitAnalysisJob} 
          disabled={(!videoUrl && !fileUpload) || isSubmitting}
          className="btn btn-primary"
        >
          {isSubmitting ? 'Submitting...' : 'Analyze Video'}
        </button>
      </div>
    );
  };

  const renderJobStatus = () => {
    return (
      <div className="job-status">
        <h4>Analysis Job Status</h4>
        <div className="status-container">
          <div className="status-indicator">
            <div className={`status-badge ${jobStatus}`}>{jobStatus}</div>
            {jobStatus === 'processing' && (
              <div className="progress-container">
                <div className="progress-bar"></div>
              </div>
            )}
          </div>
          <div className="status-actions">
            {jobStatus === 'processing' && (
              <button 
                className="btn btn-outline btn-small" 
                onClick={cancelAnalysisJob}
              >
                Cancel
              </button>
            )}
            {jobStatus === 'completed' && (
              <div className="export-buttons">
                <button 
                  className="btn btn-outline btn-small" 
                  onClick={() => downloadResults('json')}
                >
                  Export JSON
                </button>
                <button 
                  className="btn btn-outline btn-small" 
                  onClick={() => downloadResults('csv')}
                >
                  Export CSV
                </button>
              </div>
            )}
          </div>
        </div>
        {error && <div className="error-message">{error}</div>}
      </div>
    );
  };

  const renderAnalysisResults = () => {
    if (!analysisResults) return null;
    
    const tabs = getTabs();
    
    return (
      <div className="analysis-results">
        <h3>Analysis Results</h3>
        
        <TabbedInterface 
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        >
          {tabs.map(tab => tab.content)}
        </TabbedInterface>
      </div>
    );
  };

  const getTabs = () => {
    return [
      { 
        id: 'summary', 
        label: 'Summary', 
        content: renderSummaryTab() 
      },
      { 
        id: 'frames', 
        label: 'Frames', 
        content: renderFramesTab() 
      },
      { 
        id: 'objects', 
        label: 'Objects', 
        content: renderObjectsTab() 
      },
      { 
        id: 'timeline', 
        label: 'Timeline', 
        content: renderTimelineTab() 
      },
      {
        id: 'heatmap',
        label: 'Heatmap',
        content: renderHeatmapTab()
      },
      {
        id: 'tracking',
        label: 'Object Tracking',
        content: renderTrackingTab()
      }
    ];
  };

  const renderFramesTab = () => {
    return (
      <div className="frames-tab">
        {analysisResults.frames && analysisResults.frames.length > 0 ? (
          <FrameGrid 
            frames={analysisResults.frames} 
            jobId={jobId} 
            autoLoadFrames={true} 
          />
        ) : (
          <div className="empty-state">No frames were extracted from this video</div>
        )}
      </div>
    );
  };

  const renderSummaryTab = () => {
    const { summary, duration, resolution, format } = analysisResults;
    
    return (
      <div className="summary-tab">
        <div className="summary-section">
          <h4>Video Information</h4>
          <table className="info-table">
            <tbody>
              <tr>
                <td>Duration:</td>
                <td>{formatDuration(duration)}</td>
              </tr>
              <tr>
                <td>Resolution:</td>
                <td>{resolution?.width || 'N/A'} x {resolution?.height || 'N/A'}</td>
              </tr>
              <tr>
                <td>Format:</td>
                <td>{format || 'N/A'}</td>
              </tr>
              <tr>
                <td>Frames Analyzed:</td>
                <td>{analysisResults.frames?.length || 0}</td>
              </tr>
              <tr>
                <td>Objects Detected:</td>
                <td>{countTotalObjects()}</td>
              </tr>
              <tr>
                <td>Scenes Detected:</td>
                <td>{analysisResults.scenes?.length || 0}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        {summary && (
          <div className="summary-section">
            <h4>Content Summary</h4>
            <p className="summary-text">{summary}</p>
          </div>
        )}
        
        {analysisResults.key_frames && analysisResults.key_frames.length > 0 && (
          <div className="summary-section">
            <h4>Key Frames</h4>
            <div className="key-frames-preview">
              {analysisResults.key_frames.slice(0, 5).map((frameIndex, idx) => {
                return (
                  <div className="key-frame-preview" key={idx}>
                    <img 
                      src={`${API_BASE_URL}/video/frame/${jobId}/${frameIndex}`}
                      alt={`Key Frame ${idx + 1}`}
                      onError={(e) => {
                        e.target.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNlZWVlZWUiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTRweCIgZmlsbD0iIzU1NSI+RXJyb3IgbG9hZGluZyBpbWFnZTwvdGV4dD48L3N2Zz4=';
                      }}
                    />
                    <div className="key-frame-time">
                      {analysisResults.frames[frameIndex].timestamp_str}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderObjectsTab = () => {
    const { objects } = analysisResults;
    
    if (!objects || Object.keys(objects).length === 0) {
      return <div className="empty-state">No objects were detected in this video</div>;
    }
    
    // Process object data for visualization
    const objectClasses = Object.keys(objects).sort();
    const objectCounts = objectClasses.map(cls => objects[cls].length);
    
    return (
      <div className="objects-tab">
        <div className="objects-summary">
          <h4>Objects Detected</h4>
          <div className="object-class-list">
            {objectClasses.map((cls, idx) => (
              <div className="object-class-item" key={cls}>
                <div className="object-class-name">{cls}</div>
                <div className="object-class-count">{objectCounts[idx]}</div>
                <div className="object-class-bar" style={{ width: `${Math.min(100, (objectCounts[idx] / Math.max(...objectCounts)) * 100)}%` }}></div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="objects-timeline">
          <h4>Object Appearances</h4>
          <div className="timeline-container">
            {/* Timeline visualization will go here */}
            <div className="timeline-placeholder">
              Timeline visualization component will be implemented in a future update
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderTimelineTab = () => {
    const { scenes } = analysisResults;
    
    if (!scenes || scenes.length === 0) {
      return <div className="empty-state">No scene transitions were detected in this video</div>;
    }
    
    return (
      <div className="timeline-tab">
        {analysisResults ? (
          <TimelineVisualization 
            analysisResults={analysisResults}
            jobId={jobId}
            onTimeSelect={(time) => console.log(`Selected time: ${time}`)}
          />
        ) : (
          <div className="empty-state">No analysis results available for timeline visualization</div>
        )}
      </div>
    );
  };

  const renderHeatmapTab = () => {
    return (
      <div className="heatmap-tab">
        {analysisResults ? (
          <HeatmapVisualization 
            analysisResults={analysisResults}
            dimensions={{ width: 640, height: 360 }}
          />
        ) : (
          <div className="empty-state">No analysis results available for heatmap visualization</div>
        )}
      </div>
    );
  };

  const renderTrackingTab = () => {
    return (
      <div className="tracking-tab">
        {analysisResults ? (
          <ObjectTrackingVisualization 
            analysisResults={analysisResults}
            jobId={jobId}
          />
        ) : (
          <div className="empty-state">No analysis results available for object tracking</div>
        )}
      </div>
    );
  };

  // Helper functions
  const formatDuration = (seconds) => {
    if (!seconds && seconds !== 0) return 'N/A';
    
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    return [
      hrs > 0 ? hrs.toString().padStart(2, '0') : null,
      mins.toString().padStart(2, '0'),
      secs.toString().padStart(2, '0')
    ].filter(Boolean).join(':');
  };

  const countTotalObjects = () => {
    if (!analysisResults.objects) return 0;
    
    return Object.values(analysisResults.objects)
      .reduce((total, instances) => total + instances.length, 0);
  };

  return (
    <div className="video-analysis-panel">
      {renderInputForm()}
      
      {jobId && jobStatus && renderJobStatus()}
      
      {analysisResults && renderAnalysisResults()}
    </div>
  );
};

export default VideoAnalysisPanel;
