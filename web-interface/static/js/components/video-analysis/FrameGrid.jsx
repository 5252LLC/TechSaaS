import React, { useState, useEffect } from 'react';
import { videoAnalysisApi } from '../../services/api-client';

/**
 * FrameGrid component for displaying video frames with analysis
 * 
 * @param {Object} props
 * @param {Array} props.frames - Array of frame objects with metadata
 * @param {String} props.jobId - Job ID for loading individual frames
 * @param {Boolean} props.autoLoadFrames - Whether to automatically load frame images
 */
const FrameGrid = ({ frames, jobId, autoLoadFrames = true }) => {
  const [selectedFrame, setSelectedFrame] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredFrames, setFilteredFrames] = useState([]);
  const [filterKey, setFilterKey] = useState('all');
  const [sortOrder, setSortOrder] = useState('asc');
  const [loadedFrames, setLoadedFrames] = useState({});

  useEffect(() => {
    if (!frames || frames.length === 0) {
      setFilteredFrames([]);
      return;
    }
    
    // Reset loaded frames when new frames array is received
    if (autoLoadFrames) {
      setLoadedFrames({});
    }
    
    let result = [...frames];
    
    // Apply search filter if search query exists
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(frame => {
        const description = (frame.text || frame.description || '').toLowerCase();
        const timestamp = (frame.timestamp_str || '').toLowerCase();
        return description.includes(query) || timestamp.includes(query);
      });
    }
    
    // Apply key-based filtering
    if (filterKey !== 'all') {
      if (filterKey === 'has_text') {
        result = result.filter(frame => frame.text || frame.description);
      } else if (filterKey === 'has_objects') {
        result = result.filter(frame => frame.objects && frame.objects.length > 0);
      } else if (filterKey === 'key_frames') {
        result = result.filter(frame => frame.is_key_frame);
      }
    }
    
    // Apply sorting
    result.sort((a, b) => {
      const aTime = a.timestamp || a.frame_number || 0;
      const bTime = b.timestamp || b.frame_number || 0;
      return sortOrder === 'asc' ? aTime - bTime : bTime - aTime;
    });
    
    setFilteredFrames(result);
  }, [frames, searchQuery, filterKey, sortOrder, autoLoadFrames]);

  // Load frame image data when a frame is selected or when in autoload mode
  useEffect(() => {
    const loadFrameData = async (frameIndex) => {
      try {
        if (!jobId || loadedFrames[frameIndex]) return;
        
        const frameData = await videoAnalysisApi.getFrame(jobId, frameIndex);
        
        if (frameData && frameData.image_data) {
          setLoadedFrames(prev => ({
            ...prev,
            [frameIndex]: frameData.image_data
          }));
        }
      } catch (error) {
        console.error(`Failed to load frame ${frameIndex}:`, error);
      }
    };
    
    // Load selected frame if it exists and isn't loaded yet
    if (selectedFrame !== null && !loadedFrames[selectedFrame.frame_index]) {
      loadFrameData(selectedFrame.frame_index);
    }
    
    // In autoload mode, load the first few visible frames
    if (autoLoadFrames && filteredFrames.length > 0) {
      const framesToPreload = filteredFrames.slice(0, 6); // Preload first 6 frames
      framesToPreload.forEach(frame => {
        if (!loadedFrames[frame.frame_index]) {
          loadFrameData(frame.frame_index);
        }
      });
    }
  }, [selectedFrame, filteredFrames, jobId, loadedFrames, autoLoadFrames]);

  if (!frames || frames.length === 0) {
    return <div className="empty-state">No frames available</div>;
  }

  const handleFrameClick = (frame) => {
    setSelectedFrame(frame);
  };

  const getFrameImageSrc = (frame) => {
    // Use loaded frame data if available, otherwise return placeholder or frame.image_data
    if (loadedFrames[frame.frame_index]) {
      return loadedFrames[frame.frame_index];
    }
    
    return frame.image_data || 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiB2aWV3Qm94PSIwIDAgMjAwIDE1MCIgZmlsbD0ibm9uZSI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIxNTAiIGZpbGw9IiNlZWVlZWUiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTRweCIgZmlsbD0iIzU1NSI+TG9hZGluZy4uLjwvdGV4dD48L3N2Zz4=';
  };

  const getFrameText = (frame) => {
    return frame.text || frame.description || 'No analysis available';
  };

  const renderFrameObjects = (frame) => {
    if (!frame.objects || frame.objects.length === 0) {
      return null;
    }
    
    // Group objects by class
    const objectsByClass = {};
    frame.objects.forEach(obj => {
      if (!objectsByClass[obj.class]) {
        objectsByClass[obj.class] = [];
      }
      objectsByClass[obj.class].push(obj);
    });
    
    return (
      <div className="frame-objects">
        <h5>Detected Objects</h5>
        <ul className="object-list">
          {Object.entries(objectsByClass).map(([className, objects]) => (
            <li key={className}>
              {className}: {objects.length} 
              {objects.length === 1 ? ' instance' : ' instances'}
              {objects[0].confidence && 
                ` (${(objects[0].confidence * 100).toFixed(0)}%)`
              }
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const renderFilterControls = () => {
    return (
      <div className="frame-grid-controls">
        <div className="search-filter">
          <input
            type="text"
            placeholder="Search in frame descriptions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="filter-options">
          <select
            value={filterKey}
            onChange={(e) => setFilterKey(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Frames</option>
            <option value="has_text">Frames with Text</option>
            <option value="has_objects">Frames with Objects</option>
            <option value="key_frames">Key Frames</option>
          </select>
          
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            className="sort-select"
          >
            <option value="asc">Oldest First</option>
            <option value="desc">Newest First</option>
          </select>
        </div>
      </div>
    );
  };

  return (
    <div className="frame-grid-container">
      {renderFilterControls()}
      
      <div className="frame-count-info">
        Showing {filteredFrames.length} of {frames.length} frames
        {searchQuery && ` matching "${searchQuery}"`}
      </div>
      
      {selectedFrame !== null ? (
        <div className="frame-detail">
          <div className="frame-detail-header">
            <h4>Frame {selectedFrame.frame_number || selectedFrame.frame_index + 1} - {selectedFrame.timestamp_str}</h4>
            <button 
              className="btn btn-outline btn-small" 
              onClick={() => setSelectedFrame(null)}
            >
              Back to Grid
            </button>
          </div>
          
          <div className="frame-detail-content">
            <div className="frame-image-large">
              <img 
                src={`data:image/jpeg;base64,${getFrameImageSrc(selectedFrame)}`} 
                alt={`Frame ${selectedFrame.frame_index + 1}`} 
              />
            </div>
            
            <div className="frame-analysis-panel">
              <div className="frame-analysis-text">
                <h5>Analysis</h5>
                <p>{getFrameText(selectedFrame)}</p>
              </div>
              
              {renderFrameObjects(selectedFrame)}
              
              {selectedFrame.metadata && (
                <div className="frame-metadata">
                  <h5>Metadata</h5>
                  <ul className="metadata-list">
                    {Object.entries(selectedFrame.metadata).map(([key, value]) => (
                      <li key={key}>
                        <strong>{key}:</strong> {value}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="frame-grid">
          {filteredFrames.length === 0 ? (
            <div className="empty-state">
              No frames match your current filters
            </div>
          ) : (
            filteredFrames.map((frame, index) => (
              <div 
                key={index} 
                className={`frame-card ${frame.is_key_frame ? 'key-frame' : ''}`}
                onClick={() => handleFrameClick(frame)}
              >
                <div className="frame-image">
                  <img 
                    src={`data:image/jpeg;base64,${getFrameImageSrc(frame)}`} 
                    alt={`Frame ${frame.frame_number || index + 1}`} 
                  />
                  {frame.is_key_frame && (
                    <div className="key-frame-badge">Key</div>
                  )}
                </div>
                <div className="frame-info">
                  <div className="frame-number">
                    Frame {frame.frame_number || index + 1}
                  </div>
                  <div className="frame-timestamp">
                    {frame.timestamp_str || ''}
                  </div>
                  {frame.objects && frame.objects.length > 0 && (
                    <div className="frame-object-count">
                      {frame.objects.length} object{frame.objects.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default FrameGrid;
