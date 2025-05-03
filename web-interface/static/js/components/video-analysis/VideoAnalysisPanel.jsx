import React, { useState, useEffect } from 'react';
import FrameGrid from './FrameGrid';
import TabbedInterface from './TabbedInterface';
import TimelineVisualization from './TimelineVisualization';
import HeatmapVisualization from './HeatmapVisualization';
import ObjectTrackingVisualization from './ObjectTrackingVisualization';
import MultimodalVisualization from './MultimodalVisualization';
import { videoAnalysisApi } from '../../services/api-client';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

const VideoAnalysisPanel = () => {
  const [videoUrl, setVideoUrl] = useState('');
  const [fileUpload, setFileUpload] = useState(null);
  const [analysisOptions, setAnalysisOptions] = useState({
    extract_frames: true,
    object_detection: true,
    scene_detection: true,
    text_analysis: true,
    multimodal_analysis: true,
    content_summarization: true,
    audio_analysis: false
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [statusCheckInterval, setStatusCheckInterval] = useState(null);
  const [processingProgress, setProcessingProgress] = useState(0);

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
    setProcessingProgress(0);
    
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
      
      if (response && response.data && response.data.job_id) {
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

  const checkJobStatus = async (id) => {
    try {
      const response = await videoAnalysisApi.checkJobStatus(id);
      const statusData = response.data;
      
      setJobStatus(statusData.status);
      
      // Update progress if available
      if (statusData.progress !== undefined) {
        setProcessingProgress(statusData.progress);
      }
      
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
      const response = await videoAnalysisApi.getJobResults(id);
      setAnalysisResults(response.data);
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
      setError('Failed to cancel job. It may still be processing.');
    }
  };

  const downloadResults = async (format) => {
    try {
      if (jobId) {
        const response = await videoAnalysisApi.exportResults(jobId, format);
        
        if (response && response.data && response.data.downloadUrl) {
          // Create a temporary link and trigger download
          const link = document.createElement('a');
          link.href = response.data.downloadUrl;
          link.download = `video-analysis-${jobId}.${format}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        } else {
          throw new Error('Invalid response for export');
        }
      }
    } catch (err) {
      console.error('Error exporting results:', err);
      setError(`Failed to export results as ${format.toUpperCase()}. Please try again.`);
    }
  };

  const renderForm = () => {
    return (
      <div className="analysis-form">
        <h3>Submit Video for Analysis</h3>
        
        <div className="form-group">
          <label>Video URL</label>
          <input 
            type="text" 
            value={videoUrl} 
            onChange={handleVideoUrlChange}
            placeholder="Enter YouTube URL or direct link to video"
            disabled={isSubmitting || !!fileUpload}
            className="form-control"
          />
        </div>
        
        <div className="form-group">
          <label>Upload Video</label>
          <input 
            type="file" 
            onChange={handleFileChange} 
            accept="video/*"
            disabled={isSubmitting || !!videoUrl}
            className="form-control"
          />
          {fileUpload && (
            <div className="file-info">
              <span>{fileUpload.name}</span>
              <span className="file-size">({formatFileSize(fileUpload.size)})</span>
            </div>
          )}
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

            <label className="new-option">
              <input
                type="checkbox"
                name="multimodal_analysis"
                checked={analysisOptions.multimodal_analysis}
                onChange={handleOptionChange}
                disabled={isSubmitting}
              /> 
              Multimodal Analysis
            </label>
            
            <label className="new-option">
              <input
                type="checkbox"
                name="content_summarization"
                checked={analysisOptions.content_summarization}
                onChange={handleOptionChange}
                disabled={isSubmitting}
              /> 
              Content Summarization
            </label>
            
            <label className="new-option">
              <input
                type="checkbox"
                name="audio_analysis"
                checked={analysisOptions.audio_analysis}
                onChange={handleOptionChange}
                disabled={isSubmitting}
              /> 
              Audio Analysis
            </label>
          </div>
        </div>
        
        <button 
          onClick={submitAnalysisJob} 
          disabled={(!videoUrl && !fileUpload) || isSubmitting}
          className="btn btn-primary"
          data-testid="submit-button"
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
                <div 
                  className="progress-bar" 
                  style={{ width: `${processingProgress}%` }}
                ></div>
                <span className="progress-text">{processingProgress}%</span>
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
      </div>
    );
  };

  const renderResults = () => {
    if (!analysisResults) return null;
    
    const tabs = [
      {
        id: 'summary',
        title: 'Summary',
        content: renderSummary()
      },
      {
        id: 'frames',
        title: 'Frames',
        content: <FrameGrid frames={analysisResults.frames} jobId={jobId} />
      },
      {
        id: 'timeline',
        title: 'Timeline',
        content: (
          <TimelineVisualization 
            analysisResults={analysisResults} 
            jobId={jobId}
          />
        )
      },
      {
        id: 'heatmap',
        title: 'Heatmap',
        content: (
          <HeatmapVisualization 
            analysisResults={analysisResults}
          />
        )
      },
      {
        id: 'tracking',
        title: 'Object Tracking',
        content: (
          <ObjectTrackingVisualization 
            analysisResults={analysisResults}
            jobId={jobId}
          />
        )
      },
      {
        id: 'multimodal',
        title: 'Multimodal Analysis',
        content: (
          <MultimodalVisualization
            analysisResults={analysisResults}
            jobId={jobId}
          />
        )
      }
    ];
    
    return (
      <div className="analysis-results">
        <h3>Analysis Results</h3>
        <TabbedInterface 
          tabs={tabs} 
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </div>
    );
  };

  const renderSummary = () => {
    if (!analysisResults) return null;
    
    const { summary, multimodal_summary = {} } = analysisResults;
    
    return (
      <div className="results-summary">
        <div className="summary-section">
          <h4>Video Information</h4>
          <table className="summary-table">
            <tbody>
              <tr>
                <th>Duration</th>
                <td>{formatTime(summary?.duration || 0)}</td>
              </tr>
              <tr>
                <th>Resolution</th>
                <td>{summary?.resolution?.width || 0} x {summary?.resolution?.height || 0}</td>
              </tr>
              <tr>
                <th>Format</th>
                <td>{summary?.format || 'Unknown'}</td>
              </tr>
              <tr>
                <th>Frame Count</th>
                <td>{summary?.frame_count || 0}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {analysisOptions.multimodal_analysis && multimodal_summary && (
          <div className="summary-section">
            <h4>Multimodal Analysis</h4>
            {multimodal_summary.content_summary && (
              <>
                <h5>Content Summary</h5>
                <p>{multimodal_summary.content_summary}</p>
              </>
            )}
            
            {multimodal_summary.key_topics && (
              <>
                <h5>Key Topics</h5>
                <ul className="topics-list">
                  {multimodal_summary.key_topics.map((topic, idx) => (
                    <li key={idx} className="topic-item">{topic}</li>
                  ))}
                </ul>
              </>
            )}
            
            {multimodal_summary.sentiment && (
              <>
                <h5>Content Sentiment</h5>
                <div className="sentiment-meter">
                  <div className="sentiment-score" style={{
                    left: `${(multimodal_summary.sentiment + 1) * 50}%`
                  }}></div>
                  <div className="sentiment-labels">
                    <span>Negative</span>
                    <span>Neutral</span>
                    <span>Positive</span>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
        
        <div className="summary-section">
          <h4>Detected Objects</h4>
          {renderObjectSummary()}
        </div>
        
        {analysisOptions.scene_detection && (
          <div className="summary-section">
            <h4>Scene Detection</h4>
            <p>Detected {analysisResults.scenes?.length || 0} distinct scenes</p>
          </div>
        )}
      </div>
    );
  };

  const renderObjectSummary = () => {
    if (!analysisResults || !analysisResults.objects) {
      return <p>No objects detected</p>;
    }
    
    const objectCounts = {};
    
    // Count object occurrences
    Object.entries(analysisResults.objects).forEach(([className, instances]) => {
      objectCounts[className] = instances.length;
    });
    
    // Sort by count (descending)
    const sortedObjects = Object.entries(objectCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10); // Top 10
    
    return (
      <div className="object-summary">
        <div className="object-counts">
          {sortedObjects.map(([className, count]) => (
            <div key={className} className="object-count-item">
              <span className="object-class">{className}</span>
              <span className="object-count">{count}</span>
              <div className="count-bar" style={{ width: `${Math.min(count / 2, 100)}%` }}></div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  return (
    <div className="video-analysis-panel">
      <div className="panel-header">
        <h2>Video Analysis</h2>
        {error && <div className="error-message">{error}</div>}
      </div>
      
      <div className="panel-body">
        {!jobId && renderForm()}
        
        {jobId && (
          <>
            {renderJobStatus()}
            {jobStatus === 'completed' && renderResults()}
          </>
        )}
      </div>
    </div>
  );
};

export default VideoAnalysisPanel;
