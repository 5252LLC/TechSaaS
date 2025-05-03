/**
 * API Client for TechSaaS Video Analysis
 * 
 * This module provides a standardized interface for communicating with the 
 * TechSaaS backend API services, with specific focus on video analysis.
 */

import axios from 'axios';

// Base configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Request interceptor for API calls
apiClient.interceptors.request.use(
  (config) => {
    // Add authorization header if user is logged in
    const userToken = localStorage.getItem('user-token');
    if (userToken) {
      config.headers['Authorization'] = `Bearer ${userToken}`;
    }
    
    // Add request ID for tracking and auditing
    config.headers['X-Request-ID'] = generateRequestId();
    
    // Add security headers
    config.headers['X-Content-Type-Options'] = 'nosniff';
    config.headers['X-XSS-Protection'] = '1; mode=block';
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for API calls
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Handle specific error scenarios
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      if (error.response.status === 401 && !originalRequest._retry) {
        // Handle authentication errors (token refresh, redirect to login, etc.)
        console.log('Authentication error - redirecting to login');
      } else if (error.response.status === 403) {
        // Handle permission errors
        console.log('Permission denied');
      } else if (error.response.status === 429) {
        // Handle rate limiting
        console.log('Rate limit exceeded. Please try again later.');
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.log('Network error - No response received');
    } else {
      // Something happened in setting up the request that triggered an Error
      console.log('Error', error.message);
    }
    
    return Promise.reject(error);
  }
);

/**
 * Generate a unique request ID for tracking
 * @returns {string} - UUID v4 string
 */
function generateRequestId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Video Analysis API methods
 */
const videoAnalysisApi = {
  /**
   * Submit a video for analysis
   * 
   * @param {FormData|Object} data - Video data (FormData for file upload, Object for URL)
   * @param {Object} options - Additional options for analysis
   * @returns {Promise} - Promise containing job information
   */
  submitAnalysisJob: async (data, options = {}) => {
    try {
      // If data is FormData, use multipart/form-data, otherwise use JSON
      const headers = data instanceof FormData 
        ? { 'Content-Type': 'multipart/form-data' } 
        : { 'Content-Type': 'application/json' };
      
      // Add options to FormData if needed
      if (data instanceof FormData && options) {
        Object.entries(options).forEach(([key, value]) => {
          if (typeof value === 'boolean' || typeof value === 'string' || typeof value === 'number') {
            data.append(key, value.toString());
          }
        });
      }
      
      // For URL-based analysis
      if (!(data instanceof FormData)) {
        data = { ...data, ...options };
      }
      
      const response = await apiClient.post('/video/analyze', data, { headers });
      return response.data;
    } catch (error) {
      console.error('Error submitting analysis job:', error);
      throw error;
    }
  },
  
  /**
   * Check the status of a video analysis job
   * 
   * @param {string} jobId - The ID of the job to check
   * @returns {Promise} - Promise containing job status information
   */
  checkJobStatus: async (jobId) => {
    try {
      const response = await apiClient.get(`/video/job-status/${jobId}`);
      return response.data;
    } catch (error) {
      console.error(`Error checking job status for job ${jobId}:`, error);
      throw error;
    }
  },
  
  /**
   * Get the results of a completed video analysis job
   * 
   * @param {string} jobId - The ID of the job to get results for
   * @returns {Promise} - Promise containing job results
   */
  getJobResults: async (jobId) => {
    try {
      const response = await apiClient.get(`/video/results/${jobId}`);
      return response.data;
    } catch (error) {
      console.error(`Error getting job results for job ${jobId}:`, error);
      throw error;
    }
  },
  
  /**
   * Get a specific frame from a video analysis job
   * 
   * @param {string} jobId - The ID of the job
   * @param {number} frameIndex - The index of the frame to retrieve
   * @returns {Promise} - Promise containing frame data
   */
  getFrame: async (jobId, frameIndex) => {
    try {
      const response = await apiClient.get(`/video/frame/${jobId}/${frameIndex}`);
      return response.data;
    } catch (error) {
      console.error(`Error getting frame ${frameIndex} for job ${jobId}:`, error);
      throw error;
    }
  },
  
  /**
   * Cancel a running analysis job
   * 
   * @param {string} jobId - The ID of the job to cancel
   * @returns {Promise} - Promise containing cancellation result
   */
  cancelJob: async (jobId) => {
    try {
      const response = await apiClient.post(`/video/cancel/${jobId}`);
      return response.data;
    } catch (error) {
      console.error(`Error canceling job ${jobId}:`, error);
      throw error;
    }
  },
  
  /**
   * Export analysis results in various formats
   * 
   * @param {string} jobId - The ID of the job
   * @param {string} format - Export format (json, csv, pdf)
   * @returns {Promise} - Promise containing exported data or download URL
   */
  exportResults: async (jobId, format = 'json') => {
    try {
      const response = await apiClient.get(`/video/export/${jobId}`, {
        params: { format },
        responseType: format === 'pdf' ? 'blob' : 'json'
      });
      
      if (format === 'pdf') {
        // For binary responses like PDFs, create a download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `video-analysis-${jobId}.${format}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        return { success: true };
      }
      
      return response.data;
    } catch (error) {
      console.error(`Error exporting results for job ${jobId}:`, error);
      throw error;
    }
  }
};

// Export both the API client and specific API interfaces
export { apiClient, videoAnalysisApi };
export default apiClient;
