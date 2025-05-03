import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import './styles.css';

/**
 * HeatmapVisualization Component
 * 
 * Provides a spatial analysis of object detections in video frames as a heatmap.
 * Visualizes where objects appear most frequently in the video frame space.
 * 
 * @param {Object} props
 * @param {Object} props.analysisResults - The video analysis results
 * @param {String} props.selectedObjectClass - Currently selected object class to visualize
 * @param {Number} props.resolution - Resolution/intensity of the heatmap (1-10)
 * @param {Object} props.dimensions - Dimensions for the visualization canvas
 */
const HeatmapVisualization = ({
  analysisResults,
  selectedObjectClass = null,
  resolution = 5,
  dimensions = { width: 640, height: 360 }
}) => {
  const canvasRef = useRef(null);
  const [objectClasses, setObjectClasses] = useState([]);
  const [heatmapData, setHeatmapData] = useState(null);
  const [maxDensity, setMaxDensity] = useState(1);
  const [showLabels, setShowLabels] = useState(true);
  const [normalizeByFrame, setNormalizeByFrame] = useState(true);
  const [colorScheme, setColorScheme] = useState('thermal');
  
  // Extract object detection data from analysis results
  useEffect(() => {
    if (!analysisResults || !analysisResults.objects) {
      setObjectClasses([]);
      setHeatmapData(null);
      return;
    }
    
    const objects = analysisResults.objects;
    setObjectClasses(Object.keys(objects).sort());
    
    // Generate heatmap data from object detections
    generateHeatmapData(objects, selectedObjectClass, resolution);
  }, [analysisResults, selectedObjectClass, resolution]);
  
  // Generate heatmap data from object detections
  const generateHeatmapData = (objects, selectedClass, res) => {
    const relevantClasses = selectedClass ? [selectedClass] : Object.keys(objects);
    const frameCount = analysisResults.frames?.length || 0;
    
    if (frameCount === 0) {
      setHeatmapData(null);
      return;
    }
    
    // Create a grid based on resolution
    const cellSize = 10 - res + 1; // Resolution 1 = large cells, 10 = small cells
    const gridWidth = Math.ceil(dimensions.width / cellSize);
    const gridHeight = Math.ceil(dimensions.height / cellSize);
    
    // Initialize grid with zeros
    const grid = Array(gridHeight).fill().map(() => Array(gridWidth).fill(0));
    
    // Count detections in each grid cell
    let maxCount = 0;
    let totalDetections = 0;
    
    relevantClasses.forEach(objectClass => {
      if (!objects[objectClass]) return;
      
      objects[objectClass].forEach(detection => {
        // Skip if no bounding box
        if (!detection.bbox) return;
        
        totalDetections++;
        
        // Get bounding box coordinates, normalized to [0,1]
        const [x1, y1, x2, y2] = detection.bbox;
        
        // Convert normalized coordinates to pixel coordinates
        const pixelX1 = Math.floor(x1 * dimensions.width);
        const pixelY1 = Math.floor(y1 * dimensions.height);
        const pixelX2 = Math.floor(x2 * dimensions.width);
        const pixelY2 = Math.floor(y2 * dimensions.height);
        
        // Map pixel coordinates to grid coordinates
        const gridX1 = Math.floor(pixelX1 / cellSize);
        const gridY1 = Math.floor(pixelY1 / cellSize);
        const gridX2 = Math.floor(pixelX2 / cellSize);
        const gridY2 = Math.floor(pixelY2 / cellSize);
        
        // Increment all cells that overlap with this bounding box
        for (let y = gridY1; y <= gridY2 && y < gridHeight; y++) {
          for (let x = gridX1; x <= gridX2 && x < gridWidth; x++) {
            // Weight the detection by its confidence score
            const weight = detection.confidence || 1;
            grid[y][x] += weight;
            
            maxCount = Math.max(maxCount, grid[y][x]);
          }
        }
      });
    });
    
    if (normalizeByFrame && frameCount > 0) {
      // Normalize by the number of frames
      for (let y = 0; y < gridHeight; y++) {
        for (let x = 0; x < gridWidth; x++) {
          grid[y][x] = grid[y][x] / frameCount;
        }
      }
      maxCount = maxCount / frameCount;
    }
    
    setHeatmapData({
      grid,
      cellSize,
      gridWidth,
      gridHeight,
      totalDetections
    });
    
    setMaxDensity(maxCount || 1); // Avoid division by zero
  };
  
  // Draw the heatmap on the canvas
  useEffect(() => {
    if (!canvasRef.current || !heatmapData) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw background
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid cells
    const { grid, cellSize } = heatmapData;
    
    for (let y = 0; y < grid.length; y++) {
      for (let x = 0; x < grid[y].length; x++) {
        const density = grid[y][x] / maxDensity;
        if (density > 0) {
          const color = getHeatmapColor(density, colorScheme);
          ctx.fillStyle = color;
          ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
        }
      }
    }
    
    // Draw frame outline
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, dimensions.width, dimensions.height);
    
    // Draw scale legend
    drawScaleLegend(ctx, dimensions.width, dimensions.height, colorScheme);
    
    // Draw labels if enabled
    if (showLabels) {
      drawLabels(ctx, dimensions.width, dimensions.height);
    }
    
  }, [heatmapData, maxDensity, dimensions, colorScheme, showLabels]);
  
  // Get color for heatmap based on density value (0-1)
  const getHeatmapColor = (value, scheme) => {
    if (value <= 0) return 'rgba(0, 0, 0, 0)';
    
    // Apply non-linear scaling to make low values more visible
    value = Math.pow(value, 0.7);
    
    switch (scheme) {
      case 'thermal':
        // Blue (cold) to Red (hot)
        const h = (1 - value) * 240; // Hue: 240 (blue) to 0 (red)
        const s = 100; // Full saturation
        const l = 50; // Medium lightness
        return `hsla(${h}, ${s}%, ${l}%, ${Math.min(0.9, value + 0.2)})`;
        
      case 'viridis':
        // Scientific color map (blue-green-yellow)
        const colors = [
          [68, 1, 84],    // Dark purple
          [59, 82, 139],  // Blue
          [33, 144, 141], // Teal
          [93, 201, 99],  // Green
          [253, 231, 37]  // Yellow
        ];
        return interpolateColor(colors, value, Math.min(0.9, value + 0.2));
        
      case 'binary':
        // Simple black and white
        return `rgba(0, 0, 0, ${Math.min(0.9, value)})`;
        
      default:
        return `rgba(255, 0, 0, ${Math.min(0.9, value)})`;
    }
  };
  
  // Interpolate between a set of colors based on value (0-1)
  const interpolateColor = (colors, value, alpha) => {
    if (value >= 1) return `rgba(${colors[colors.length - 1].join(',')}, ${alpha})`;
    if (value <= 0) return `rgba(${colors[0].join(',')}, ${alpha})`;
    
    const segment = 1 / (colors.length - 1);
    const index = Math.min(colors.length - 2, Math.floor(value / segment));
    const remainder = (value - index * segment) / segment;
    
    const c1 = colors[index];
    const c2 = colors[index + 1];
    
    const r = Math.round(c1[0] + remainder * (c2[0] - c1[0]));
    const g = Math.round(c1[1] + remainder * (c2[1] - c1[1]));
    const b = Math.round(c1[2] + remainder * (c2[2] - c1[2]));
    
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };
  
  // Draw scale legend
  const drawScaleLegend = (ctx, width, height, scheme) => {
    const legendWidth = 20;
    const legendHeight = 200;
    const legendX = width - legendWidth - 20;
    const legendY = (height - legendHeight) / 2;
    
    // Draw gradient
    const steps = 100;
    const stepHeight = legendHeight / steps;
    
    for (let i = 0; i < steps; i++) {
      const value = 1 - (i / steps);
      ctx.fillStyle = getHeatmapColor(value, scheme);
      ctx.fillRect(legendX, legendY + i * stepHeight, legendWidth, stepHeight + 1);
    }
    
    // Draw border
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.strokeRect(legendX, legendY, legendWidth, legendHeight);
    
    // Draw labels
    ctx.fillStyle = '#000';
    ctx.font = '12px Arial';
    ctx.textAlign = 'right';
    
    ctx.fillText('High', legendX - 5, legendY + 12);
    ctx.fillText('Low', legendX - 5, legendY + legendHeight);
    
    // Draw title
    ctx.save();
    ctx.translate(legendX + legendWidth + 15, legendY + legendHeight / 2);
    ctx.rotate(Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText('Density', 0, 0);
    ctx.restore();
  };
  
  // Draw labels on the heatmap
  const drawLabels = (ctx, width, height) => {
    // Draw title
    if (selectedObjectClass) {
      ctx.fillStyle = '#000';
      ctx.font = 'bold 16px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(`${selectedObjectClass} Detections`, width / 2, 25);
    } else {
      ctx.fillStyle = '#000';
      ctx.font = 'bold 16px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('All Object Detections', width / 2, 25);
    }
    
    // Draw detection count
    if (heatmapData) {
      ctx.font = '14px Arial';
      ctx.textAlign = 'left';
      ctx.fillText(`Total detections: ${heatmapData.totalDetections}`, 20, height - 15);
    }
  };
  
  // Handle object class selection
  const handleObjectClassChange = (e) => {
    const newClass = e.target.value === 'all' ? null : e.target.value;
    if (newClass !== selectedObjectClass) {
      generateHeatmapData(analysisResults.objects, newClass, resolution);
    }
  };
  
  // Handle resolution change
  const handleResolutionChange = (e) => {
    const newResolution = parseInt(e.target.value, 10);
    if (newResolution !== resolution && analysisResults?.objects) {
      generateHeatmapData(analysisResults.objects, selectedObjectClass, newResolution);
    }
  };
  
  return (
    <div className="heatmap-visualization">
      <div className="heatmap-controls">
        <div className="control-group">
          <label>Object Class:</label>
          <select 
            value={selectedObjectClass || 'all'} 
            onChange={handleObjectClassChange}
            disabled={!objectClasses.length}
          >
            <option value="all">All Objects</option>
            {objectClasses.map(cls => (
              <option key={cls} value={cls}>{cls}</option>
            ))}
          </select>
        </div>
        
        <div className="control-group">
          <label>Resolution:</label>
          <input 
            type="range" 
            min="1" 
            max="10" 
            value={resolution} 
            onChange={handleResolutionChange}
            disabled={!heatmapData}
          />
          <span>{resolution}</span>
        </div>
        
        <div className="control-group">
          <label>Color Scheme:</label>
          <select 
            value={colorScheme} 
            onChange={(e) => setColorScheme(e.target.value)}
            disabled={!heatmapData}
          >
            <option value="thermal">Thermal</option>
            <option value="viridis">Viridis</option>
            <option value="binary">Binary</option>
          </select>
        </div>
        
        <div className="control-group checkbox">
          <label>
            <input 
              type="checkbox" 
              checked={normalizeByFrame} 
              onChange={(e) => {
                setNormalizeByFrame(e.target.checked);
                if (analysisResults?.objects) {
                  generateHeatmapData(analysisResults.objects, selectedObjectClass, resolution);
                }
              }}
              disabled={!heatmapData}
            />
            Normalize by frame count
          </label>
        </div>
        
        <div className="control-group checkbox">
          <label>
            <input 
              type="checkbox" 
              checked={showLabels} 
              onChange={(e) => setShowLabels(e.target.checked)}
              disabled={!heatmapData}
            />
            Show labels
          </label>
        </div>
      </div>
      
      <div className="heatmap-canvas-container">
        {!analysisResults || !heatmapData ? (
          <div className="empty-state">
            <p>No object detection data available for heatmap visualization.</p>
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            width={dimensions.width}
            height={dimensions.height}
            className="heatmap-canvas"
          />
        )}
      </div>
      
      <div className="heatmap-explanation">
        <h4>About Heatmap Visualization</h4>
        <p>
          The heatmap displays the spatial distribution of object detections across the video.
          Areas with higher density of detections are shown in warmer colors (red/yellow),
          while areas with fewer detections are shown in cooler colors (blue/purple).
        </p>
        <p>
          Use the controls above to filter by object class, adjust the resolution,
          or change the color scheme to better analyze the data.
        </p>
      </div>
    </div>
  );
};

HeatmapVisualization.propTypes = {
  analysisResults: PropTypes.object.isRequired,
  selectedObjectClass: PropTypes.string,
  resolution: PropTypes.number,
  dimensions: PropTypes.shape({
    width: PropTypes.number,
    height: PropTypes.number
  })
};

export default HeatmapVisualization;
