import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import './styles.css';

/**
 * ObjectTrackingVisualization Component
 * 
 * Visualizes object movement and trajectories across video frames.
 * 
 * @param {Object} props
 * @param {Object} props.analysisResults - The video analysis results
 * @param {String} props.jobId - Job ID for API access to frames
 * @param {Boolean} props.showTrajectories - Whether to show object movement paths
 */
const ObjectTrackingVisualization = ({
  analysisResults,
  jobId,
  showTrajectories = true
}) => {
  const canvasRef = useRef(null);
  const [selectedFrame, setSelectedFrame] = useState(0);
  const [selectedObjectClass, setSelectedObjectClass] = useState(null);
  const [trackData, setTrackData] = useState(null);
  const [objectClasses, setObjectClasses] = useState([]);
  const [playbackActive, setPlaybackActive] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  const frames = analysisResults?.frames || [];
  const objects = analysisResults?.objects || {};
  
  // Extract tracked object data and setup
  useEffect(() => {
    if (!analysisResults || !analysisResults.objects) {
      setObjectClasses([]);
      setTrackData(null);
      return;
    }
    
    // Get sorted list of object classes
    const classes = Object.keys(objects).sort();
    setObjectClasses(classes);
    
    // Process tracking data
    generateTrackingData(objects, selectedObjectClass);
  }, [analysisResults, selectedObjectClass]);

  // Generate object tracking data
  const generateTrackingData = (objects, selectedClass) => {
    const relevantClasses = selectedClass ? [selectedClass] : Object.keys(objects);
    const tracks = {};
    
    // Group detections by "track" (approximated by object class and similar positions)
    relevantClasses.forEach(objClass => {
      if (!objects[objClass]) return;
      
      // Sort detections by timestamp
      const sortedDetections = [...objects[objClass]].sort((a, b) => 
        (a.timestamp || 0) - (b.timestamp || 0)
      );
      
      // Simple tracking algorithm - in a real app, use more sophisticated tracking
      sortedDetections.forEach((detection) => {
        if (!detection.bbox || detection.frame_index === undefined) return;
        
        const frameIdx = detection.frame_index;
        const [x1, y1, x2, y2] = detection.bbox;
        const centerX = (x1 + x2) / 2;
        const centerY = (y1 + y2) / 2;
        
        // Initialize track list for this class if not exists
        if (!tracks[objClass]) {
          tracks[objClass] = [];
        }
        
        // Try to find an existing track for this object
        let trackAssigned = false;
        for (let i = 0; i < tracks[objClass].length; i++) {
          const track = tracks[objClass][i];
          const lastPos = track.positions[track.positions.length - 1];
          
          // Skip if this track already has a detection in this frame
          if (lastPos.frameIndex === frameIdx) continue;
          
          // If the previous detection was in the previous frame and position is close enough
          if (lastPos.frameIndex === frameIdx - 1) {
            const distance = Math.sqrt(
              Math.pow(centerX - lastPos.x, 2) + 
              Math.pow(centerY - lastPos.y, 2)
            );
            
            // If close enough, consider it the same object
            if (distance < 0.2) { // 20% of frame width/height max movement
              track.positions.push({
                frameIndex: frameIdx,
                x: centerX,
                y: centerY,
                width: x2 - x1,
                height: y2 - y1,
                confidence: detection.confidence || 1,
                timestamp: detection.timestamp || 0
              });
              trackAssigned = true;
              break;
            }
          }
        }
        
        // If no existing track matched, create a new one
        if (!trackAssigned) {
          tracks[objClass].push({
            id: `${objClass}-track-${tracks[objClass].length + 1}`,
            class: objClass,
            positions: [{
              frameIndex: frameIdx,
              x: centerX,
              y: centerY,
              width: x2 - x1,
              height: y2 - y1,
              confidence: detection.confidence || 1,
              timestamp: detection.timestamp || 0
            }]
          });
        }
      });
    });
    
    setTrackData(tracks);
  };

  // Draw the visualization on the canvas
  useEffect(() => {
    if (!canvasRef.current || !trackData || frames.length === 0) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw frame image as background
    drawFrameBackground(ctx, canvas.width, canvas.height);
    
    // Draw object tracks
    drawObjectTracks(ctx, canvas.width, canvas.height);
    
    // Draw labels and info
    drawLabels(ctx, canvas.width, canvas.height);
    
  }, [trackData, selectedFrame, showTrajectories, frames]);

  // Handle playback controls
  useEffect(() => {
    let playbackTimer = null;
    
    if (playbackActive && frames.length > 0) {
      playbackTimer = setInterval(() => {
        setSelectedFrame(prev => {
          const next = prev + 1;
          if (next >= frames.length) {
            setPlaybackActive(false);
            return prev;
          }
          return next;
        });
      }, 1000 / (playbackSpeed * 5)); // Adjust for reasonable playback speed
    }
    
    return () => {
      if (playbackTimer) {
        clearInterval(playbackTimer);
      }
    };
  }, [playbackActive, playbackSpeed, frames]);

  // Draw frame background image
  const drawFrameBackground = (ctx, width, height) => {
    // Draw frame placeholder
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, width, height);
    
    // Load and draw the actual frame image if available
    if (frames.length > 0) {
      const frameIndex = Math.min(selectedFrame, frames.length - 1);
      const frameImage = new Image();
      
      if (jobId) {
        // Load from API
        frameImage.src = `${API_BASE_URL}/video/frame/${jobId}/${frameIndex}`;
        frameImage.onload = () => {
          ctx.drawImage(frameImage, 0, 0, width, height);
          // Re-draw tracks and labels on top of the image
          drawObjectTracks(ctx, width, height);
          drawLabels(ctx, width, height);
        };
        
        // Handle error loading image
        frameImage.onerror = () => {
          ctx.fillStyle = '#ccc';
          ctx.fillRect(0, 0, width, height);
          ctx.fillStyle = '#333';
          ctx.font = '16px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Error loading frame image', width / 2, height / 2);
        };
      } else if (frames[frameIndex].image_data) {
        // Use base64 image data if available
        frameImage.src = `data:image/jpeg;base64,${frames[frameIndex].image_data}`;
        frameImage.onload = () => {
          ctx.drawImage(frameImage, 0, 0, width, height);
          // Re-draw tracks and labels on top of the image
          drawObjectTracks(ctx, width, height);
          drawLabels(ctx, width, height);
        };
      }
    }
  };

  // Draw object tracks and bounding boxes
  const drawObjectTracks = (ctx, width, height) => {
    if (!trackData) return;
    
    Object.entries(trackData).forEach(([objClass, tracks]) => {
      // Skip if filtering by class and this isn't the selected class
      if (selectedObjectClass && objClass !== selectedObjectClass) return;
      
      const color = getObjectColor(objClass);
      
      tracks.forEach(track => {
        // Find position at the selected frame
        const currentPosition = track.positions.find(p => p.frameIndex === selectedFrame);
        
        // Draw trajectory if enabled
        if (showTrajectories) {
          // Draw full path up to current frame
          ctx.beginPath();
          let firstPoint = true;
          
          track.positions.forEach(pos => {
            if (pos.frameIndex > selectedFrame) return;
            
            const x = pos.x * width;
            const y = pos.y * height;
            
            if (firstPoint) {
              ctx.moveTo(x, y);
              firstPoint = false;
            } else {
              ctx.lineTo(x, y);
            }
          });
          
          ctx.strokeStyle = `${color}99`; // Semi-transparent
          ctx.lineWidth = 2;
          ctx.stroke();
        }
        
        // Draw current position if in this frame
        if (currentPosition) {
          const x = currentPosition.x * width;
          const y = currentPosition.y * height;
          const w = currentPosition.width * width;
          const h = currentPosition.height * height;
          
          // Draw bounding box
          ctx.strokeStyle = color;
          ctx.lineWidth = 2;
          ctx.strokeRect(x - w/2, y - h/2, w, h);
          
          // Draw label
          ctx.fillStyle = color;
          ctx.font = '14px Arial';
          ctx.textAlign = 'center';
          const confidence = Math.round(currentPosition.confidence * 100);
          ctx.fillText(`${objClass} ${confidence}%`, x, y - h/2 - 5);
          
          // Draw center point
          ctx.beginPath();
          ctx.arc(x, y, 4, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
        }
      });
    });
  };

  // Draw labels and information
  const drawLabels = (ctx, width, height) => {
    // Draw frame info
    if (frames.length > 0) {
      const frameIndex = Math.min(selectedFrame, frames.length - 1);
      const frame = frames[frameIndex];
      
      ctx.fillStyle = '#000';
      ctx.font = '14px Arial';
      ctx.textAlign = 'left';
      ctx.fillText(`Frame: ${frameIndex + 1}/${frames.length}`, 10, 20);
      
      if (frame.timestamp !== undefined) {
        ctx.fillText(`Time: ${formatTime(frame.timestamp)}`, 10, 40);
      }
    }
    
    // Draw object counts
    if (trackData) {
      let y = 70;
      ctx.font = '14px Arial';
      ctx.textAlign = 'left';
      
      Object.entries(trackData).forEach(([objClass, tracks]) => {
        if (selectedObjectClass && objClass !== selectedObjectClass) return;
        
        const color = getObjectColor(objClass);
        const activeTracks = tracks.filter(track => 
          track.positions.some(p => p.frameIndex === selectedFrame)
        );
        
        ctx.fillStyle = color;
        ctx.fillText(`${objClass}: ${activeTracks.length} visible`, 10, y);
        y += 20;
      });
    }
  };

  // Get a color for an object class
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

  // Format time in MM:SS format
  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '00:00';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Handle frame selection change
  const handleFrameChange = (e) => {
    const newFrame = parseInt(e.target.value, 10);
    setSelectedFrame(newFrame);
  };

  // Toggle playback state
  const togglePlayback = () => {
    setPlaybackActive(!playbackActive);
  };

  return (
    <div className="object-tracking-visualization">
      <div className="visualization-controls">
        <div className="control-group">
          <label>Object Class:</label>
          <select 
            value={selectedObjectClass || 'all'} 
            onChange={(e) => setSelectedObjectClass(e.target.value === 'all' ? null : e.target.value)}
            disabled={!objectClasses.length}
          >
            <option value="all">All Objects</option>
            {objectClasses.map(cls => (
              <option key={cls} value={cls}>{cls}</option>
            ))}
          </select>
        </div>
        
        <div className="control-group checkbox">
          <label>
            <input 
              type="checkbox" 
              checked={showTrajectories} 
              onChange={(e) => setShowTrajectories(e.target.checked)}
            />
            Show Trajectories
          </label>
        </div>
      </div>
      
      <div className="tracking-canvas-container">
        {!analysisResults || frames.length === 0 ? (
          <div className="empty-state">
            <p>No frame data available for object tracking visualization.</p>
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            width={640}
            height={360}
            className="tracking-canvas"
          />
        )}
      </div>
      
      <div className="playback-controls">
        <button 
          className={`playback-btn ${playbackActive ? 'pause' : 'play'}`}
          onClick={togglePlayback}
          disabled={!frames.length}
        >
          {playbackActive ? 'Pause' : 'Play'}
        </button>
        
        <input
          type="range"
          min="0"
          max={Math.max(0, frames.length - 1)}
          value={selectedFrame}
          onChange={handleFrameChange}
          disabled={!frames.length}
          className="frame-slider"
        />
        
        <span className="frame-counter">
          Frame {selectedFrame + 1} / {frames.length}
        </span>
        
        <div className="speed-control">
          <label>Speed:</label>
          <select 
            value={playbackSpeed} 
            onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
            disabled={!frames.length}
          >
            <option value="0.25">0.25x</option>
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="1.5">1.5x</option>
            <option value="2">2x</option>
          </select>
        </div>
      </div>
      
      <div className="tracking-info-panel">
        <h4>Object Tracking Information</h4>
        {!trackData ? (
          <p>No tracking data available.</p>
        ) : (
          <div className="tracking-stats">
            {Object.entries(trackData).map(([objClass, tracks]) => {
              if (selectedObjectClass && objClass !== selectedObjectClass) return null;
              
              const totalDetections = tracks.reduce((sum, track) => sum + track.positions.length, 0);
              const uniqueTracks = tracks.length;
              
              return (
                <div key={objClass} className="object-class-stats">
                  <h5 style={{color: getObjectColor(objClass)}}>{objClass}</h5>
                  <div className="stats-grid">
                    <div>Tracked Objects:</div>
                    <div>{uniqueTracks}</div>
                    <div>Total Detections:</div>
                    <div>{totalDetections}</div>
                    <div>Avg. Detections per Track:</div>
                    <div>{uniqueTracks > 0 ? (totalDetections / uniqueTracks).toFixed(1) : 0}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

// Define API base URL
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

ObjectTrackingVisualization.propTypes = {
  analysisResults: PropTypes.object.isRequired,
  jobId: PropTypes.string,
  showTrajectories: PropTypes.bool
};

export default ObjectTrackingVisualization;
