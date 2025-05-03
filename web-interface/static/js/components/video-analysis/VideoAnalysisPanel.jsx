import React, { useState, useEffect } from 'react';
import FrameGrid from './FrameGrid';
import TabbedInterface from './TabbedInterface';
import axios from 'axios';

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
      const formData = new FormData();
      
      if (fileUpload) {
        formData.append('video_file', fileUpload);
      } else if (videoUrl) {
        formData.append('video_url', videoUrl);
      } else {
        throw new Error('Please provide a video URL or upload a file');
      }
      
      // Add analysis options to formData
      Object.entries(analysisOptions).forEach(([key, value]) => {
        formData.append(key, value.toString());
      });
      
      const response = await axios.post(`${API_BASE_URL}/video/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data && response.data.job_id) {
        setJobId(response.data.job_id);
        setJobStatus('processing');
        
        // Start checking status immediately
        checkJobStatus(response.data.job_id);
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

  const checkJobStatus = async (jId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/video/job-status/${jId}`);
      
      if (response.data) {
        setJobStatus(response.data.status);
        
        if (response.data.status === 'completed') {
          fetchAnalysisResults(jId);
          if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
            setStatusCheckInterval(null);
          }
        } else if (response.data.status === 'failed') {
          setError(response.data.error || 'Analysis job failed');
          if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
            setStatusCheckInterval(null);
          }
        }
      }
    } catch (err) {
      setError('Error checking job status');
      setJobStatus('failed');
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        setStatusCheckInterval(null);
      }
    }
  };

  const fetchAnalysisResults = async (jId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/video/results/${jId}`);
      
      if (response.data) {
        setAnalysisResults(response.data);
        setActiveTab('summary');
      }
    } catch (err) {
      setError('Error fetching analysis results');
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
        
        <div className={`status-indicator status-${jobStatus}`}>
          <span className="status-text">{jobStatus}</span>
          {jobStatus === 'processing' && (
            <div className="spinner"></div>
          )}
        </div>
        
        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}
      </div>
    );
  };

  const renderAnalysisResults = () => {
    if (!analysisResults) return null;
    
    const tabs = [
      { id: 'summary', label: 'Summary' },
      { id: 'frames', label: 'Frames', disabled: !analysisResults.frames || analysisResults.frames.length === 0 },
      { id: 'objects', label: 'Objects', disabled: !analysisResults.objects || Object.keys(analysisResults.objects).length === 0 },
      { id: 'timeline', label: 'Timeline', disabled: !analysisResults.scenes || analysisResults.scenes.length === 0 },
    ];
    
    return (
      <div className="analysis-results">
        <h3>Analysis Results</h3>
        
        <TabbedInterface 
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        >
          {activeTab === 'summary' && renderSummaryTab()}
          {activeTab === 'frames' && renderFramesTab()}
          {activeTab === 'objects' && renderObjectsTab()}
          {activeTab === 'timeline' && renderTimelineTab()}
        </TabbedInterface>
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
                const frame = analysisResults.frames[frameIndex];
                return (
                  <div className="key-frame-preview" key={idx}>
                    <img 
                      src={`data:image/jpeg;base64,${frame.image_data}`} 
                      alt={`Key Frame ${idx + 1}`}
                    />
                    <div className="key-frame-time">
                      {frame.timestamp_str}
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

  const renderFramesTab = () => {
    return (
      <div className="frames-tab">
        {analysisResults.frames && analysisResults.frames.length > 0 ? (
          <FrameGrid frames={analysisResults.frames} />
        ) : (
          <div className="empty-state">No frames were extracted from this video</div>
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
        <div className="scenes-list">
          <h4>Scene Timeline</h4>
          
          {scenes.map((scene, idx) => (
            <div className="scene-item" key={idx}>
              <div className="scene-header">
                <div className="scene-number">Scene {idx + 1}</div>
                <div className="scene-time">
                  {scene.start_time_str} - {scene.end_time_str}
                </div>
                <div className="scene-duration">
                  {formatDuration(scene.duration)}
                </div>
              </div>
              
              {scene.keyframe_index !== undefined && analysisResults.frames && (
                <div className="scene-keyframe">
                  <img 
                    src={`data:image/jpeg;base64,${analysisResults.frames[scene.keyframe_index].image_data}`}
                    alt={`Scene ${idx + 1} keyframe`}
                  />
                </div>
              )}
              
              {scene.description && (
                <div className="scene-description">
                  {scene.description}
                </div>
              )}
            </div>
          ))}
        </div>
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
