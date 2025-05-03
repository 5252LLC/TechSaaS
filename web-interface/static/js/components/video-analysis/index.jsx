import React from 'react';
import ReactDOM from 'react-dom';
import VideoAnalysisPanel from './VideoAnalysisPanel';
import './styles.css';

// Check if the container element exists before rendering
const container = document.getElementById('video-analysis-react-root');
if (container) {
  ReactDOM.render(<VideoAnalysisPanel />, container);
} else {
  console.error('Video analysis container not found in the DOM');
}
