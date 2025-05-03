import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { videoAnalysisApi } from '../../services/api-client';

/**
 * MultimodalVisualization Component
 * 
 * Visualizes multimodal analysis results combining video, text, and audio analysis
 * Provides an interactive interface for exploring relationships between
 * different modalities of content.
 */
const MultimodalVisualization = ({ analysisResults, jobId }) => {
  const [selectedFrame, setSelectedFrame] = useState(0);
  const [activeSection, setActiveSection] = useState('cross-modal');
  const [frameImage, setFrameImage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const canvasRef = useRef(null);
  const timelineRef = useRef(null);

  // Extract multimodal data from analysis results
  const multimodalData = analysisResults?.multimodal_data || {};
  const videoMetadata = analysisResults?.summary || {};
  const audioData = multimodalData?.audio_analysis || {};
  const textData = multimodalData?.text_analysis || {};
  const crossModalData = multimodalData?.cross_modal_analysis || {};
  const totalFrames = videoMetadata?.frame_count || 0;
  const duration = videoMetadata?.duration || 0;

  // Load frame image when selected frame changes
  useEffect(() => {
    const loadFrameImage = async () => {
      if (!jobId) return;
      
      setIsLoading(true);
      try {
        const response = await videoAnalysisApi.getFrame(jobId, selectedFrame);
        if (response && response.data && response.data.imageData) {
          setFrameImage(response.data.imageData);
        }
      } catch (error) {
        console.error('Error loading frame:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadFrameImage();
  }, [jobId, selectedFrame]);

  // Draw timeline visualization when data or canvas changes
  useEffect(() => {
    if (!timelineRef.current || !crossModalData.alignments) return;
    
    const canvas = timelineRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw background
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(0, 0, width, height);
    
    // Draw timeline axis
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(50, height - 30);
    ctx.lineTo(width - 20, height - 30);
    ctx.stroke();
    
    // Draw tick marks
    const tickCount = Math.min(10, Math.floor(duration));
    for (let i = 0; i <= tickCount; i++) {
      const x = 50 + (i / tickCount) * (width - 70);
      ctx.beginPath();
      ctx.moveTo(x, height - 30);
      ctx.lineTo(x, height - 25);
      ctx.stroke();
      
      // Draw tick labels
      ctx.fillStyle = '#333';
      ctx.font = '12px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(formatTime(i * duration / tickCount), x, height - 10);
    }
    
    // Draw multimodal events
    if (crossModalData.alignments) {
      const alignments = crossModalData.alignments;
      
      alignments.forEach(alignment => {
        const startX = 50 + (alignment.timestamp / duration) * (width - 70);
        
        // Draw marker
        ctx.fillStyle = getModalityColor(alignment.modality);
        ctx.beginPath();
        ctx.arc(startX, height - 50, 6, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw connection to related events if available
        if (alignment.related_events) {
          alignment.related_events.forEach(related => {
            const relatedX = 50 + (related.timestamp / duration) * (width - 70);
            
            // Draw connection line
            ctx.strokeStyle = 'rgba(100, 100, 100, 0.4)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(startX, height - 50);
            ctx.lineTo(relatedX, height - 70);
            ctx.stroke();
            
            // Draw related marker
            ctx.fillStyle = getModalityColor(related.modality);
            ctx.beginPath();
            ctx.arc(relatedX, height - 70, 4, 0, Math.PI * 2);
            ctx.fill();
          });
        }
      });
    }
    
  }, [crossModalData, timelineRef.current]);

  // Handle timeline click to select frame/timestamp
  const handleTimelineClick = (e) => {
    if (!timelineRef.current || !duration) return;
    
    const canvas = timelineRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const width = canvas.width;
    
    // Calculate timestamp based on click position
    const clickPosition = (x - 50) / (width - 70);
    const timestamp = Math.max(0, Math.min(duration, clickPosition * duration));
    
    // Find nearest frame to this timestamp
    const frameRate = totalFrames / duration;
    const nearestFrame = Math.round(timestamp * frameRate);
    
    setSelectedFrame(Math.min(nearestFrame, totalFrames - 1));
  };

  // Render the current frame with annotations
  const renderAnnotatedFrame = () => {
    if (!frameImage) {
      return (
        <div className="frame-placeholder">
          {isLoading ? 'Loading frame...' : 'Select a frame to view'}
        </div>
      );
    }
    
    // Find annotations for the current frame
    const frameAnnotations = crossModalData.frame_annotations?.[selectedFrame] || [];
    
    return (
      <div className="annotated-frame">
        <div className="frame-container">
          <img 
            src={frameImage} 
            alt={`Frame ${selectedFrame}`} 
            className="frame-image"
          />
          
          {/* Overlay annotations */}
          {frameAnnotations.map((annotation, idx) => {
            if (!annotation.bbox) return null;
            
            const [x, y, width, height] = annotation.bbox;
            
            return (
              <div 
                key={idx}
                className="frame-annotation"
                style={{
                  left: `${x * 100}%`,
                  top: `${y * 100}%`,
                  width: `${width * 100}%`,
                  height: `${height * 100}%`,
                  borderColor: getModalityColor(annotation.type)
                }}
              >
                <span className="annotation-label">{annotation.label}</span>
              </div>
            );
          })}
        </div>
        
        <div className="frame-info">
          <div className="frame-metadata">
            <span>Frame: {selectedFrame}</span>
            <span>Time: {formatTime(selectedFrame / (totalFrames / duration))}</span>
          </div>
        </div>
      </div>
    );
  };

  // Render cross-modal connections
  const renderCrossModalConnections = () => {
    const timelineConnections = crossModalData.content_connections || [];
    
    return (
      <div className="cross-modal-connections">
        <div className="timeline-container">
          <h4>Cross-Modal Timeline</h4>
          <canvas 
            ref={timelineRef} 
            width="800" 
            height="180" 
            className="multimodal-timeline"
            onClick={handleTimelineClick}
          />
        </div>
        
        <div className="connection-list">
          <h4>Modal Connections</h4>
          {timelineConnections.length > 0 ? (
            <ul className="connections">
              {timelineConnections.map((connection, idx) => (
                <li key={idx} className="connection-item">
                  <div className="connection-header">
                    <span className={`modality-indicator ${connection.primary_modality}`}>
                      {formatModality(connection.primary_modality)}
                    </span>
                    <span className="connection-time">{formatTime(connection.timestamp)}</span>
                  </div>
                  <div className="connection-content">{connection.description}</div>
                  {connection.related_modalities && (
                    <div className="related-modalities">
                      {connection.related_modalities.map((related, ridx) => (
                        <span 
                          key={ridx}
                          className={`related-modality ${related.type}`}
                          onClick={() => setSelectedFrame(frameForTimestamp(related.timestamp))}
                        >
                          {formatModality(related.type)} @ {formatTime(related.timestamp)}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">No cross-modal connections found</div>
          )}
        </div>
      </div>
    );
  };

  // Render natural language understanding of video
  const renderNLU = () => {
    const textualContent = textData.extracted_text || [];
    const contentUnderstanding = crossModalData.content_understanding || {};
    
    return (
      <div className="nlu-section">
        <div className="content-summary">
          <h4>Content Understanding</h4>
          
          {contentUnderstanding.summary ? (
            <div className="content-summary-text">{contentUnderstanding.summary}</div>
          ) : (
            <div className="empty-state">No content summary available</div>
          )}
          
          {contentUnderstanding.key_entities && contentUnderstanding.key_entities.length > 0 && (
            <div className="key-entities">
              <h5>Key Entities</h5>
              <div className="entity-tags">
                {contentUnderstanding.key_entities.map((entity, idx) => (
                  <span 
                    key={idx} 
                    className={`entity-tag ${entity.type}`}
                    title={`${entity.type}: ${entity.description || ''}`}
                  >
                    {entity.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className="extracted-text">
          <h4>Extracted Text</h4>
          {textualContent.length > 0 ? (
            <div className="text-segments">
              {textualContent.map((segment, idx) => (
                <div key={idx} className="text-segment">
                  <div className="segment-time">{formatTime(segment.timestamp)}</div>
                  <div className="segment-text">{segment.text}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No text extracted from video</div>
          )}
        </div>
      </div>
    );
  };

  // Render audio analysis section
  const renderAudioAnalysis = () => {
    const audioSegments = audioData.segments || [];
    const speechSegments = audioData.speech_segments || [];
    
    return (
      <div className="audio-analysis">
        <div className="audio-waveform">
          <h4>Audio Analysis</h4>
          {audioData.waveform ? (
            <canvas ref={canvasRef} width="800" height="100" className="waveform-canvas" />
          ) : (
            <div className="waveform-placeholder">
              Audio waveform visualization not available
            </div>
          )}
        </div>
        
        <div className="audio-segments">
          <h4>Audio Segments</h4>
          {audioSegments.length > 0 ? (
            <div className="segment-timeline">
              {audioSegments.map((segment, idx) => (
                <div 
                  key={idx}
                  className="audio-segment"
                  style={{
                    left: `${(segment.start_time / duration) * 100}%`,
                    width: `${((segment.end_time - segment.start_time) / duration) * 100}%`,
                    backgroundColor: getSoundTypeColor(segment.type)
                  }}
                  onClick={() => setSelectedFrame(frameForTimestamp(segment.start_time))}
                >
                  <span className="segment-label">{segment.type}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No audio segments identified</div>
          )}
        </div>
        
        <div className="speech-analysis">
          <h4>Speech Transcription</h4>
          {speechSegments.length > 0 ? (
            <div className="speech-segments">
              {speechSegments.map((segment, idx) => (
                <div key={idx} className="speech-segment">
                  <div className="speech-time">
                    {formatTime(segment.start_time)} - {formatTime(segment.end_time)}
                  </div>
                  <div className="speech-text">{segment.text}</div>
                  {segment.speaker && (
                    <div className="speech-speaker">Speaker: {segment.speaker}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No speech detected in this video</div>
          )}
        </div>
      </div>
    );
  };

  // Helper function to format time
  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Helper function to get color for modality
  const getModalityColor = (modality) => {
    const colors = {
      'visual': '#3498db',
      'audio': '#e74c3c',
      'text': '#2ecc71',
      'object': '#9b59b6',
      'scene': '#f1c40f',
      'speech': '#e67e22',
      'default': '#95a5a6'
    };
    
    return colors[modality] || colors.default;
  };

  // Helper function to get color for sound types
  const getSoundTypeColor = (type) => {
    const colors = {
      'speech': 'rgba(46, 204, 113, 0.3)',
      'music': 'rgba(155, 89, 182, 0.3)',
      'noise': 'rgba(231, 76, 60, 0.3)',
      'silence': 'rgba(149, 165, 166, 0.2)',
      'default': 'rgba(52, 152, 219, 0.3)'
    };
    
    return colors[type] || colors.default;
  };

  // Helper function to format modality names
  const formatModality = (modality) => {
    const modalityNames = {
      'visual': 'Visual',
      'audio': 'Audio',
      'text': 'Text',
      'object': 'Object',
      'scene': 'Scene',
      'speech': 'Speech',
      'default': 'Unknown'
    };
    
    return modalityNames[modality] || modalityNames.default;
  };

  // Helper function to find frame number for a timestamp
  const frameForTimestamp = (timestamp) => {
    if (!duration || !totalFrames) return 0;
    const frameRate = totalFrames / duration;
    return Math.min(Math.floor(timestamp * frameRate), totalFrames - 1);
  };

  // If no multimodal data is available, show a message
  if (!multimodalData || Object.keys(multimodalData).length === 0) {
    return (
      <div className="multimodal-visualization empty">
        <div className="empty-message">
          <h3>No Multimodal Analysis Data Available</h3>
          <p>
            Multimodal analysis was not enabled for this video or no multimodal data was found.
            Please submit a new analysis job with multimodal analysis enabled.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="multimodal-visualization">
      <div className="visualization-header">
        <h3>Multimodal Analysis</h3>
        <div className="section-tabs">
          <button 
            className={`section-tab ${activeSection === 'cross-modal' ? 'active' : ''}`}
            onClick={() => setActiveSection('cross-modal')}
          >
            Cross-Modal Connections
          </button>
          <button 
            className={`section-tab ${activeSection === 'nlu' ? 'active' : ''}`}
            onClick={() => setActiveSection('nlu')}
          >
            Content Understanding
          </button>
          <button 
            className={`section-tab ${activeSection === 'audio' ? 'active' : ''}`}
            onClick={() => setActiveSection('audio')}
          >
            Audio Analysis
          </button>
        </div>
      </div>
      
      <div className="visualization-content">
        <div className="content-main">
          {activeSection === 'cross-modal' && renderCrossModalConnections()}
          {activeSection === 'nlu' && renderNLU()}
          {activeSection === 'audio' && renderAudioAnalysis()}
        </div>
        
        <div className="content-sidebar">
          <h4>Current Frame</h4>
          {renderAnnotatedFrame()}
          
          <div className="frame-navigation">
            <button 
              onClick={() => setSelectedFrame(Math.max(0, selectedFrame - 1))}
              disabled={selectedFrame === 0 || isLoading}
            >
              Previous
            </button>
            <button 
              onClick={() => setSelectedFrame(Math.min(totalFrames - 1, selectedFrame + 1))}
              disabled={selectedFrame === totalFrames - 1 || isLoading}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

MultimodalVisualization.propTypes = {
  analysisResults: PropTypes.object.isRequired,
  jobId: PropTypes.string.isRequired
};

export default MultimodalVisualization;
