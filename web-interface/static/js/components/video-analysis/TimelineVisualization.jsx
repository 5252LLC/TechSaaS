import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import './styles.css';

/**
 * TimelineVisualization Component
 * 
 * Renders a timeline visualization of video analysis results, including:
 * - Scene changes
 * - Object detections over time
 * - Key frames
 * - Custom markers
 * 
 * @param {Object} props
 * @param {Object} props.analysisResults - The video analysis results object
 * @param {String} props.jobId - The job ID for API interactions
 * @param {Function} props.onTimeSelect - Callback when a time point is selected
 * @param {Number} props.currentTime - Current playback time (if video is playing)
 * @param {Number} props.duration - Total video duration in seconds
 */
const TimelineVisualization = ({ 
  analysisResults, 
  jobId,
  onTimeSelect, 
  currentTime = 0,
  duration = 0
}) => {
  const [timelineMode, setTimelineMode] = useState('scenes'); // scenes, objects, keyframes
  const [highlightedObject, setHighlightedObject] = useState(null);
  const [timelineWidth, setTimelineWidth] = useState(0);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [timelineOffset, setTimelineOffset] = useState(0);
  const timelineRef = useRef(null);
  
  // Parse analysis results
  const scenes = analysisResults?.scenes || [];
  const objects = analysisResults?.objects || {};
  const keyFrames = analysisResults?.key_frames || [];
  const actualDuration = analysisResults?.duration || duration || 0;

  // Get frame timestamps from analysis results
  const frames = analysisResults?.frames || [];
  const frameTimestamps = frames.map(frame => frame.timestamp || 0);

  // Calculate timeline markers based on selected mode
  const calculateTimelineMarkers = () => {
    switch (timelineMode) {
      case 'scenes':
        return scenes.map((scene, index) => ({
          id: `scene-${index}`,
          type: 'scene',
          startTime: scene.start_time,
          endTime: scene.end_time || (index < scenes.length - 1 ? scenes[index + 1].start_time : actualDuration),
          label: `Scene ${index + 1}`,
          description: scene.description || '',
          color: getSceneColor(index)
        }));
      
      case 'objects':
        // Flatten object detections into timeline events
        const objectEvents = [];
        Object.entries(objects).forEach(([objectClass, detections]) => {
          detections.forEach((detection, idx) => {
            objectEvents.push({
              id: `${objectClass}-${idx}`,
              type: 'object',
              startTime: detection.timestamp,
              endTime: detection.timestamp + 0.5, // Approximate duration for visualization
              label: objectClass,
              confidence: detection.confidence,
              frameIndex: detection.frame_index,
              bbox: detection.bbox,
              color: getObjectColor(objectClass),
              highlighted: highlightedObject === objectClass
            });
          });
        });
        return objectEvents;
      
      case 'keyframes':
        return keyFrames.map((frameIndex, idx) => {
          const frame = frames[frameIndex];
          return {
            id: `keyframe-${idx}`,
            type: 'keyframe',
            startTime: frame?.timestamp || 0,
            endTime: frame?.timestamp || 0,
            frameIndex: frameIndex,
            label: `Key ${idx + 1}`,
            color: '#FFD700', // Gold color for key frames
          };
        });
        
      default:
        return [];
    }
  };
  
  // Timeline markers based on selected mode
  const timelineMarkers = calculateTimelineMarkers();
  
  // Update timeline width on window resize
  useEffect(() => {
    const updateTimelineWidth = () => {
      if (timelineRef.current) {
        setTimelineWidth(timelineRef.current.offsetWidth);
      }
    };
    
    updateTimelineWidth();
    window.addEventListener('resize', updateTimelineWidth);
    
    return () => {
      window.removeEventListener('resize', updateTimelineWidth);
    };
  }, []);
  
  // Convert time to position on the timeline
  const timeToPosition = (time) => {
    if (!actualDuration) return 0;
    const position = (time / actualDuration) * timelineWidth * zoomLevel;
    return position - timelineOffset;
  };
  
  // Convert position to time on the timeline
  const positionToTime = (position) => {
    if (!timelineWidth || !actualDuration) return 0;
    const adjustedPosition = position + timelineOffset;
    return (adjustedPosition / (timelineWidth * zoomLevel)) * actualDuration;
  };
  
  // Handle timeline click to navigate to time
  const handleTimelineClick = (e) => {
    if (!timelineRef.current || !actualDuration) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const time = positionToTime(clickX);
    
    if (onTimeSelect && time >= 0 && time <= actualDuration) {
      onTimeSelect(time);
    }
  };
  
  // Handle zoom controls
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev * 1.5, 10)); // Max zoom 10x
  };
  
  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev / 1.5, 1)); // Min zoom 1x
  };
  
  const handleZoomReset = () => {
    setZoomLevel(1);
    setTimelineOffset(0);
  };
  
  // Handle panning the timeline
  const [isPanning, setIsPanning] = useState(false);
  const [panStartX, setPanStartX] = useState(0);
  
  const handlePanStart = (e) => {
    setIsPanning(true);
    setPanStartX(e.clientX);
  };
  
  const handlePanMove = (e) => {
    if (!isPanning) return;
    
    const deltaX = e.clientX - panStartX;
    setTimelineOffset(prev => {
      // Constrain offset to prevent scrolling beyond timeline bounds
      const maxOffset = Math.max(0, (timelineWidth * zoomLevel) - timelineWidth);
      return Math.max(0, Math.min(prev - deltaX, maxOffset));
    });
    setPanStartX(e.clientX);
  };
  
  const handlePanEnd = () => {
    setIsPanning(false);
  };
  
  // Get color for a scene based on index
  const getSceneColor = (index) => {
    const colors = [
      '#4285F4', '#34A853', '#FBBC05', '#EA4335',
      '#8AB4F8', '#7BCB8A', '#FDE293', '#F28B82'
    ];
    return colors[index % colors.length];
  };
  
  // Get color for an object class
  const getObjectColor = (objectClass) => {
    // Simple string hashing for consistent colors
    let hash = 0;
    for (let i = 0; i < objectClass.length; i++) {
      hash = objectClass.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const c = (hash & 0x00FFFFFF)
      .toString(16)
      .toUpperCase()
      .padStart(6, '0');
    
    return `#${c}`;
  };
  
  // Object class list for filtering
  const objectClasses = Object.keys(objects).sort();
  
  return (
    <div className="timeline-visualization">
      <div className="timeline-controls">
        <div className="timeline-mode-selector">
          <button 
            className={`mode-btn ${timelineMode === 'scenes' ? 'active' : ''}`}
            onClick={() => setTimelineMode('scenes')}
          >
            Scenes
          </button>
          <button 
            className={`mode-btn ${timelineMode === 'objects' ? 'active' : ''}`}
            onClick={() => setTimelineMode('objects')}
          >
            Objects
          </button>
          <button 
            className={`mode-btn ${timelineMode === 'keyframes' ? 'active' : ''}`}
            onClick={() => setTimelineMode('keyframes')}
          >
            Key Frames
          </button>
        </div>
        
        <div className="timeline-zoom-controls">
          <button 
            className="zoom-btn" 
            onClick={handleZoomOut}
            disabled={zoomLevel <= 1}
          >
            -
          </button>
          <button 
            className="zoom-btn reset" 
            onClick={handleZoomReset}
          >
            Reset
          </button>
          <button 
            className="zoom-btn" 
            onClick={handleZoomIn}
            disabled={zoomLevel >= 10}
          >
            +
          </button>
        </div>
      </div>
      
      {timelineMode === 'objects' && (
        <div className="object-filter-toolbar">
          <span className="filter-label">Filter objects:</span>
          <div className="object-filter-buttons">
            <button 
              className={`object-filter-btn ${highlightedObject === null ? 'active' : ''}`}
              onClick={() => setHighlightedObject(null)}
            >
              All
            </button>
            {objectClasses.map(objClass => (
              <button 
                key={objClass}
                className={`object-filter-btn ${highlightedObject === objClass ? 'active' : ''}`}
                onClick={() => setHighlightedObject(objClass === highlightedObject ? null : objClass)}
                style={{borderLeft: `4px solid ${getObjectColor(objClass)}`}}
              >
                {objClass}
              </button>
            ))}
          </div>
        </div>
      )}
      
      <div 
        className="timeline-container"
        ref={timelineRef}
        onClick={handleTimelineClick}
        onMouseDown={handlePanStart}
        onMouseMove={handlePanMove}
        onMouseUp={handlePanEnd}
        onMouseLeave={handlePanEnd}
      >
        {/* Timeline ruler with time markers */}
        <div className="timeline-ruler">
          {[...Array(Math.ceil(actualDuration / 5) + 1)].map((_, i) => {
            const time = i * 5; // 5-second intervals
            if (time > actualDuration) return null;
            
            const position = timeToPosition(time);
            if (position < -50 || position > timelineWidth + 50) return null; // Skip off-screen markers
            
            return (
              <div 
                key={`marker-${i}`}
                className="timeline-marker"
                style={{left: `${position}px`}}
              >
                <div className="marker-line"></div>
                <div className="marker-label">{formatTime(time)}</div>
              </div>
            );
          })}
        </div>
        
        {/* Timeline events visualization */}
        <div className="timeline-events" style={{width: `${timelineWidth}px`}}>
          {/* Render background segments for scenes */}
          {timelineMode === 'scenes' && timelineMarkers.map(marker => {
            const startPos = timeToPosition(marker.startTime);
            const endPos = timeToPosition(marker.endTime);
            const width = Math.max(2, endPos - startPos);
            
            if (endPos < 0 || startPos > timelineWidth) return null; // Skip off-screen markers
            
            return (
              <div 
                key={marker.id}
                className="timeline-segment scene-segment"
                style={{
                  left: `${startPos}px`, 
                  width: `${width}px`,
                  backgroundColor: `${marker.color}40` // Color with transparency
                }}
                title={`${marker.label}: ${marker.description || 'No description'}`}
              >
                {width > 50 && (
                  <div className="segment-label">{marker.label}</div>
                )}
              </div>
            );
          })}
          
          {/* Render object events */}
          {timelineMode === 'objects' && timelineMarkers.map(marker => {
            if (highlightedObject && marker.label !== highlightedObject) return null;
            
            const position = timeToPosition(marker.startTime);
            
            if (position < -10 || position > timelineWidth + 10) return null; // Skip off-screen markers
            
            return (
              <div 
                key={marker.id}
                className={`timeline-event object-event ${marker.highlighted ? 'highlighted' : ''}`}
                style={{
                  left: `${position}px`,
                  backgroundColor: marker.color
                }}
                title={`${marker.label} (Confidence: ${(marker.confidence * 100).toFixed(0)}%)`}
              />
            );
          })}
          
          {/* Render key frame markers */}
          {timelineMode === 'keyframes' && timelineMarkers.map(marker => {
            const position = timeToPosition(marker.startTime);
            
            if (position < -10 || position > timelineWidth + 10) return null; // Skip off-screen markers
            
            return (
              <div 
                key={marker.id}
                className="timeline-event keyframe-event"
                style={{
                  left: `${position}px`,
                  backgroundColor: marker.color
                }}
                title={`${marker.label} (${formatTime(marker.startTime)})`}
              />
            );
          })}
          
          {/* Current time indicator */}
          {currentTime > 0 && (
            <div 
              className="current-time-indicator"
              style={{left: `${timeToPosition(currentTime)}px`}}
            />
          )}
        </div>
      </div>
      
      {/* Additional information area */}
      <div className="timeline-info-panel">
        <h4>Timeline Information</h4>
        {timelineMode === 'scenes' && scenes.length > 0 && (
          <div className="info-content">
            <p>Total scenes: {scenes.length}</p>
            <div className="scene-list">
              {scenes.map((scene, index) => (
                <div 
                  key={`scene-info-${index}`}
                  className="scene-item"
                  onClick={() => onTimeSelect && onTimeSelect(scene.start_time)}
                >
                  <div 
                    className="scene-color-indicator" 
                    style={{backgroundColor: getSceneColor(index)}}
                  />
                  <div className="scene-info">
                    <div className="scene-title">Scene {index + 1}</div>
                    <div className="scene-time">
                      {formatTime(scene.start_time)} - {formatTime(scene.end_time || (index < scenes.length - 1 ? scenes[index + 1].start_time : actualDuration))}
                    </div>
                    {scene.description && (
                      <div className="scene-description">{scene.description}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {timelineMode === 'objects' && (
          <div className="info-content">
            <p>Object detections: {calculateTotalDetections(objects)}</p>
            <div className="object-summary">
              {objectClasses.map(objClass => (
                <div 
                  key={`obj-info-${objClass}`}
                  className={`object-summary-item ${highlightedObject === objClass ? 'highlighted' : ''}`}
                  onClick={() => setHighlightedObject(objClass === highlightedObject ? null : objClass)}
                >
                  <div 
                    className="object-color-indicator" 
                    style={{backgroundColor: getObjectColor(objClass)}}
                  />
                  <div className="object-name">{objClass}</div>
                  <div className="object-count">{objects[objClass]?.length || 0}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {timelineMode === 'keyframes' && keyFrames.length > 0 && (
          <div className="info-content">
            <p>Key frames: {keyFrames.length}</p>
            <div className="keyframe-thumbnails">
              {keyFrames.slice(0, 5).map((frameIndex, idx) => {
                return (
                  <div 
                    key={`keyframe-thumb-${idx}`}
                    className="keyframe-thumbnail"
                    onClick={() => {
                      const frame = frames[frameIndex];
                      onTimeSelect && frame && onTimeSelect(frame.timestamp || 0);
                    }}
                  >
                    <img 
                      src={jobId ? `${API_BASE_URL}/video/frame/${jobId}/${frameIndex}` : '#'} 
                      alt={`Key Frame ${idx + 1}`}
                      onError={(e) => {
                        e.target.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNlZWVlZWUiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTRweCIgZmlsbD0iIzU1NSI+RXJyb3IgbG9hZGluZyBpbWFnZTwvdGV4dD48L3N2Zz4=';
                      }}
                    />
                    <div className="keyframe-time">
                      {formatTime(frames[frameIndex]?.timestamp || 0)}
                    </div>
                  </div>
                );
              })}
              
              {keyFrames.length > 5 && (
                <div className="more-keyframes">
                  +{keyFrames.length - 5} more
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Calculate total detections across all object classes
function calculateTotalDetections(objects) {
  return Object.values(objects).reduce((sum, detections) => sum + detections.length, 0);
}

// Format time in MM:SS format
function formatTime(seconds) {
  if (isNaN(seconds)) return '00:00';
  
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Define API base URL
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

TimelineVisualization.propTypes = {
  analysisResults: PropTypes.object.isRequired,
  jobId: PropTypes.string,
  onTimeSelect: PropTypes.func,
  currentTime: PropTypes.number,
  duration: PropTypes.number
};

export default TimelineVisualization;
