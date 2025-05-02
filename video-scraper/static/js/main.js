/**
 * TechSaaS Platform - Video Scraper JavaScript
 * Handles form submission, job tracking, and UI updates for the video scraper
 */

// Track active jobs
let activeJobs = new Map();
let pollInterval;

// DOM Elements

/**
 * Initialize the application
 */
function init() {
    console.log('Initializing TechSaaS Video Scraper...');
    
    // Set up initial tab state
    const urlTab = document.getElementById('url-tab');
    if (urlTab && !document.querySelector('.tab-container .tab.active')) {
        showTab('url-tab');
    }
    
    // Show results container if we have jobs
    if (document.querySelectorAll('.job-item').length > 0) {
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.classList.remove('hidden');
            resultsContainer.style.display = 'block';
        }
    }
    
    // Add event listeners
    // Theme toggling
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('change', toggleTheme);
        
        // Check for saved theme preference
        if (localStorage.getItem('theme') === 'dark') {
            document.body.classList.add('dark-theme');
            themeToggle.checked = true;
        }
    }
    
    // Single URL extraction
    const extractBtn = document.getElementById('extract-btn');
    if (extractBtn) {
        extractBtn.addEventListener('click', handleSingleExtraction);
    }
    
    // Batch extraction
    const batchExtractBtn = document.getElementById('batch-extract-btn');
    if (batchExtractBtn) {
        batchExtractBtn.addEventListener('click', handleBatchExtraction);
    } else {
        console.error('Batch extract button not found');
    }
    
    // Search form
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearch);
    }
    
    // Search button as fallback
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }
    
    // Set up tab switching for main tabs
    const tabs = document.querySelectorAll('.tab-container .tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.id;
            showTab(tabId);
        });
    });
    
    // Set up main navigation tabs
    const navTabs = document.querySelectorAll('.tabs a.tab');
    navTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            // Only handle Downloads tab specially
            if (tab.innerText !== 'Downloads') return;
            
            // Prevent default only for Downloads tab
            e.preventDefault();
            
            // Show downloads section
            showDownloadsTab();
        });
    });
    
    // Clear results button
    const clearResultsBtn = document.getElementById('clear-results');
    if (clearResultsBtn) {
        clearResultsBtn.addEventListener('click', clearResults);
    }
    
    // Check for initial downloads
    fetchAvailableDownloads();
    
    // Add CSS for search results styling
    addSearchResultsStyle();
    
    // Add CSS for highlighting elements
    addHighlightStyle();
    
    console.log('Video Scraper initialized successfully');
}

// Initialize the application
init();

/**
 * Show downloads tab functionality
 */
function showDownloadsTab() {
    // First ensure the results are visible
    const resultsContainer = document.getElementById('results-container');
    if (resultsContainer) {
        resultsContainer.classList.remove('hidden');
        resultsContainer.style.display = 'block';
        
        // Scroll to the results container
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
        
        // Add a flash effect to highlight it
        resultsContainer.classList.add('highlight-flash');
        setTimeout(() => {
            resultsContainer.classList.remove('highlight-flash');
        }, 1000);
    }
    
    // Show a notification explaining what to do
    showNotification('Your downloaded videos appear in the Results section below', 'info', 5000);
}

/**
 * Clear all results from the results list
 */
function clearResults() {
    const resultsList = document.getElementById('results-list');
    if (resultsList) {
        resultsList.innerHTML = '';
        
        // Hide the results container if empty
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
        
        showNotification('Results cleared', 'success');
    }
}

/**
 * Add a CSS class for highlighting/flashing elements
 */
function addHighlightStyle() {
    // Check if style already exists
    if (!document.getElementById('highlight-style')) {
        const style = document.createElement('style');
        style.id = 'highlight-style';
        style.textContent = `
            .highlight-flash {
                animation: flash-animation 1s;
            }
            @keyframes flash-animation {
                0% { background-color: transparent; }
                50% { background-color: rgba(59, 130, 246, 0.2); }
                100% { background-color: transparent; }
            }
            .btn {
                position: relative;
                overflow: hidden;
                transition: all 0.3s ease;
            }
            .btn:active {
                transform: scale(0.95);
            }
            .btn:after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 5px;
                height: 5px;
                background: rgba(255, 255, 255, 0.5);
                opacity: 0;
                border-radius: 100%;
                transform: scale(1, 1) translate(-50%);
                transform-origin: 50% 50%;
            }
            .btn:focus:not(:active)::after {
                animation: ripple 1s ease-out;
            }
            @keyframes ripple {
                0% {
                    transform: scale(0, 0);
                    opacity: 0.5;
                }
                20% {
                    transform: scale(25, 25);
                    opacity: 0.3;
                }
                100% {
                    opacity: 0;
                    transform: scale(40, 40);
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Switch between tabs in the interface
 */
function showTab(tabId) {
    // Get all tabs and content
    const tabs = document.querySelectorAll('.tab-container .tab');
    const contents = document.querySelectorAll('.tab-content');
    
    // Hide all content
    contents.forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    tabs.forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab content
    document.getElementById(tabId).classList.add('active');
    
    // Determine which content to show based on tab
    let contentId;
    if (tabId === 'url-tab') {
        contentId = 'url-content';
    } else if (tabId === 'search-tab') {
        contentId = 'search-content';
    } else if (tabId === 'batch-tab') {
        contentId = 'batch-content';
    }
    
    // Show the appropriate content
    if (contentId) {
        const content = document.getElementById(contentId);
        if (content) {
            content.classList.add('active');
        }
    }
    
    // Update batch/single video preview visibility based on selected tab
    const previewContainer = document.getElementById('preview-container');
    const batchPreviewContainer = document.getElementById('batch-preview-container');
    
    if (tabId === 'batch-tab') {
        if (previewContainer) previewContainer.classList.add('hidden');
        if (batchPreviewContainer && document.querySelector('.preview-thumbnail')) {
            batchPreviewContainer.classList.remove('hidden');
        }
    } else {
        if (batchPreviewContainer) batchPreviewContainer.classList.add('hidden');
        if (previewContainer && document.getElementById('video-preview').src) {
            previewContainer.classList.remove('hidden');
        }
    }
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    
    // Save theme preference
    if (document.body.classList.contains('dark-theme')) {
        localStorage.setItem('theme', 'dark');
    } else {
        localStorage.setItem('theme', 'light');
    }
}

/**
 * Handle single URL extraction
 */
function handleSingleExtraction(e) {
    if (e) e.preventDefault();
    
    const url = document.getElementById('video-url').value.trim();
    const quality = document.getElementById('quality').value;
    
    if (!url) {
        showNotification('Please enter a URL', 'error');
        return;
    }
    
    extractVideo(url, quality);
}

/**
 * Handle batch extraction of multiple URLs
 */
function handleBatchExtraction(e) {
    if (e) e.preventDefault();
    
    // Get batch URLs from textarea
    const batchUrlsInput = document.getElementById('url-list');
    if (!batchUrlsInput) {
        showNotification('URL list textarea not found', 'error');
        return;
    }
    
    const batchUrls = batchUrlsInput.value.split('\n').filter(url => url.trim() !== '');
    
    // Quality setting
    const quality = document.getElementById('batch-quality').value || 'best';
    
    if (batchUrls.length === 0) {
        showNotification('Please enter at least one URL', 'error');
        return;
    }
    
    // Show results container
    showResults();
    
    // Add batch info to results
    addResultItem(`Processing ${batchUrls.length} URLs in batch mode`, 'info');
    
    // Start processing URLs one by one
    processBatchUrls(batchUrls, quality);
}

/**
 * Process a batch of URLs sequentially to avoid overwhelming the server
 */
function processBatchUrls(urls, quality, startIndex = 0) {
    if (startIndex >= urls.length) {
        showNotification('Batch processing complete!', 'success');
        return;
    }
    
    const url = urls[startIndex].trim();
    
    if (!url) {
        // Skip empty lines
        processBatchUrls(urls, quality, startIndex + 1);
        return;
    }
    
    if (!isValidUrl(url)) {
        // Add error for invalid URL
        addResultItem(`Error for URL #${startIndex + 1}: Invalid URL format`, 'error');
        processBatchUrls(urls, quality, startIndex + 1);
        return;
    }
    
    // Show extraction in progress message
    addResultItem(`Processing URL #${startIndex + 1}: ${url}`, 'info');
    
    // Extract the video
    fetch('/api/extract', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url: url,
            quality: quality
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // If we have a job_id, track the job
        if (data.job_id) {
            trackJob(data.job_id);
            
            // Update batch item with job ID link
            updateBatchItemStatus(startIndex, 'pending', `Job started: ${data.job_id}`);
            
            // Proceed to next URL after a short delay to prevent overwhelming the server
            setTimeout(() => {
                processBatchUrls(urls, quality, startIndex + 1);
            }, 500);
        } else {
            updateBatchItemStatus(startIndex, 'error', 'No job ID returned');
            // Continue anyway
            setTimeout(() => {
                processBatchUrls(urls, quality, startIndex + 1);
            }, 500);
        }
    })
    .catch(error => {
        console.error('Error in batch extraction:', error);
        updateBatchItemStatus(startIndex, 'error', error.message);
        
        // Continue with next URL despite error
        setTimeout(() => {
            processBatchUrls(urls, quality, startIndex + 1);
        }, 500);
    });
}

/**
 * Validate URL format
 */
function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === "http:" || url.protocol === "https:";
    } catch (_) {
        return false;
    }
}

/**
 * Extract a video from a URL
 */
async function extractVideo(url, quality = 'best') {
    if (!isValidUrl(url)) {
        showNotification('Please enter a valid URL', 'error');
        return false;
    }
    
    showLoading(true);
    
    fetch('/api/extract', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url: url,
            quality: quality
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // If we have a job_id, track the job
        if (data.job_id) {
            trackJob(data.job_id);
            showResults();
        } else {
            processCompletedJob(Date.now(), data);
            showLoading(false);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification(`Error: ${error.message}`, 'error');
        showLoading(false);
    });
    
    return true;
}

/**
 * Process a completed job
 */
function processCompletedJob(jobId, data) {
    console.log(`Processing completed job ${jobId}:`, data);
    
    // Check for video info in various possible locations in the response
    let videoInfo = null;
    
    if (data.info) {
        videoInfo = data.info;
    } else if (data.result && data.result.info) {
        videoInfo = data.result.info;
    } else if (data.video_info) {
        videoInfo = data.video_info;
    }
    
    // If we have video info, display it
    if (videoInfo) {
        displayVideoInfo(jobId, videoInfo);
        showNotification('Video extracted successfully!', 'success');
    } 
    // If we have a result with a filename but no info, add download button
    else if (data.result && data.result.filename) {
        addDownloadButton(jobId, data.result);
        showNotification('Download ready!', 'success');
    } 
    // No video info found
    else {
        // Update job item to show "No video information available"
        const jobItem = document.getElementById(`job-${jobId}`);
        if (jobItem) {
            const jobInfo = jobItem.querySelector('.job-info');
            if (jobInfo) {
                // Add error message if not already present
                let errorMsg = jobItem.querySelector('.error-message');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'error-message';
                    jobInfo.appendChild(errorMsg);
                }
                errorMsg.textContent = 'Error: No video information available';
            }
        }
    }
}

/**
 * Add a download button to completed job
 */
function addDownloadButton(jobId, result) {
    if (!result || !result.filename) {
        console.error('No filename for download button', result);
        return;
    }
    
    const jobItem = document.getElementById(`job-${jobId}`);
    if (!jobItem) {
        console.error(`Job item not found: ${jobId}`);
        return;
    }
    
    // Check if button already exists
    if (jobItem.querySelector('.download-btn')) {
        return;
    }
    
    const jobActions = jobItem.querySelector('.job-actions');
    
    // Create download button
    const downloadBtn = document.createElement('a');
    downloadBtn.className = 'btn btn-primary download-btn';
    downloadBtn.textContent = 'Download Video';
    
    // If we have the full path, use just the filename portion
    let filename = result.filename;
    if (filename.includes('/')) {
        filename = filename.split('/').pop();
    }
    
    // Ensure we have a proper extension for the file
    if (!filename.includes('.')) {
        filename = `${filename}.mp4`;
    }
    
    // Set download links directly to this specific file first
    const directPath = `/api/video-scraper/download-file/${filename}`;
    downloadBtn.href = directPath;
    downloadBtn.download = filename;
    downloadBtn.dataset.jobId = jobId;
    
    // Add click handler for download that first checks if the file exists
    downloadBtn.addEventListener('click', function(e) {
        e.preventDefault(); // Prevent immediate download
        
        // Show loading state
        downloadBtn.textContent = 'Preparing...';
        downloadBtn.classList.add('downloading');
        
        // First try to check if the specific file for this job exists
        fetch(`/api/video-scraper/check-file/${filename}`)
            .then(response => response.json())
            .then(data => {
                if (data.exists) {
                    // The exact file exists, so use it
                    console.log(`Found exact job file: ${data.filename}`);
                    downloadBtn.href = `/api/video-scraper/download-file/${data.filename}`;
                    downloadBtn.download = data.filename;
                    showNotification('Download starting!', 'success');
                    
                    // Trigger the download
                    window.location.href = downloadBtn.href;
                    downloadBtn.textContent = 'Download Video';
                    downloadBtn.classList.remove('downloading');
                    return;
                }
                
                // If specific file not found, look for any file with matching job ID
                if (filename.includes(jobId)) {
                    // Try to find any file containing the job ID
                    fetch('/api/video-scraper/list-downloads')
                        .then(response => response.json())
                        .then(data => {
                            // Reset button state
                            downloadBtn.textContent = 'Download Video';
                            downloadBtn.classList.remove('downloading');
                            
                            if (data.files && data.files.length > 0) {
                                // Try to find a match using different strategies
                                let matchedFile = null;
                                
                                // 1. Look for any file containing the job ID
                                matchedFile = data.files.find(f => f.includes(jobId));
                                
                                // 2. If no match with job ID, use most recent file as a last resort
                                if (!matchedFile && data.files.length > 0) {
                                    matchedFile = data.files[0]; // First file is the most recent
                                }
                                
                                if (matchedFile) {
                                    // Update the download link with the matched file
                                    const newPath = `/api/video-scraper/download-file/${matchedFile}`;
                                    downloadBtn.href = newPath;
                                    downloadBtn.download = matchedFile;
                                    
                                    console.log(`Found matching file: ${matchedFile}`);
                                    showNotification('Download starting!', 'success');
                                    
                                    // Trigger the download
                                    window.location.href = newPath;
                                } else {
                                    showNotification('No matching file found. Try extracting again.', 'error');
                                }
                            } else {
                                showNotification('No downloads available. Try extracting a video first.', 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error fetching available downloads:', error);
                            downloadBtn.textContent = 'Download Video';
                            downloadBtn.classList.remove('downloading');
                            showNotification('Error finding download file. Try extracting again.', 'error');
                        });
                } else {
                    downloadBtn.textContent = 'Download Video';
                    downloadBtn.classList.remove('downloading');
                    showNotification('File not found. Try extracting again.', 'error');
                }
            })
            .catch(error => {
                console.error('Error checking file:', error);
                downloadBtn.textContent = 'Download Video';
                downloadBtn.classList.remove('downloading');
                showNotification('Error checking file. Try extracting again.', 'error');
            });
    });
    
    // Add button to job actions
    jobActions.appendChild(downloadBtn);
}

/**
 * Poll server for job status updates
 */
function pollActiveJobs() {
    // Skip if no active jobs
    if (activeJobs.size === 0) {
        return;
    }
    
    console.log(`Polling ${activeJobs.size} active jobs...`);
    
    // Check each job
    activeJobs.forEach((data, jobId) => {
        fetch(`/api/job/${jobId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(`Job ${jobId} status: ${data.status}`);
                
                // Update job status in UI
                updateJobItem(jobId, data);
                
                // Process complete jobs
                if (data.status === 'complete' || data.status === 'completed') {
                    // Process job that is completed
                    processCompletedJob(jobId, data);
                    
                    // Remove from active jobs
                    activeJobs.delete(jobId);
                    console.log(`Removed completed job ${jobId} from tracking`);
                    
                    // Stop polling if no active jobs
                    if (activeJobs.size === 0) {
                        clearInterval(pollInterval);
                        pollInterval = null;
                        console.log('All jobs complete, stopped polling');
                    }
                }
                // Process failed jobs
                else if (data.status === 'failed' || data.status === 'error') {
                    // Show error
                    showNotification(`Job failed: ${data.error || 'Unknown error'}`, 'error');
                    
                    // Remove from active jobs
                    activeJobs.delete(jobId);
                    
                    // Stop polling if no active jobs
                    if (activeJobs.size === 0) {
                        clearInterval(pollInterval);
                        pollInterval = null;
                        console.log('No active jobs, stopped polling');
                    }
                }
            })
            .catch(error => {
                console.error(`Error polling job ${jobId}:`, error);
            });
    });
    
    // Schedule next poll if we still have active jobs
    if (activeJobs.size > 0 && !pollInterval) {
        pollInterval = setInterval(pollActiveJobs, 1000);
    }
}

/**
 * Show results container
 */
function showResults() {
    const resultsContainer = document.getElementById('results-container');
    if (resultsContainer) {
        resultsContainer.classList.remove('hidden');
        resultsContainer.style.display = 'block'; // Override the inline style
    }
}

/**
 * Track job progress and update UI
 */
function trackJob(jobId) {
    // Add to active jobs map
    activeJobs.set(jobId, { status: 'pending', progress: 0 });
    
    // Add job item to UI
    addJobItem(jobId);
    
    // Start polling interval if not already running
    if (!pollInterval) {
        // Poll every second for updates
        pollInterval = setInterval(pollActiveJobs, 1000);
        // Also poll immediately
        pollActiveJobs();
    }
}

/**
 * Add a job item to the results list
 */
function addJobItem(jobId) {
    showResults();
    
    const resultsContainer = document.getElementById('results-list');
    
    const jobItem = document.createElement('div');
    jobItem.id = `job-${jobId}`;
    jobItem.className = 'result-item job-item';
    
    jobItem.innerHTML = `
        <div class="job-info">
            <h3>Job ID: ${jobId}</h3>
            <div class="job-status">Status: <span class="status-label pending">Pending</span></div>
            <div class="progress-container">
                <div class="progress-bar" style="width: 0%"></div>
                <div class="progress-text">0%</div>
            </div>
        </div>
        <div class="job-content"></div>
        <div class="job-actions">
            <button class="btn btn-outline cancel-btn" data-job-id="${jobId}">Cancel</button>
        </div>
    `;
    
    // Add event listener for cancel button
    const cancelBtn = jobItem.querySelector('.cancel-btn');
    cancelBtn.addEventListener('click', () => cancelJob(jobId));
    
    resultsContainer.appendChild(jobItem);
}

/**
 * Update job item in the results list
 */
function updateJobItem(jobId, data) {
    const jobItem = document.getElementById(`job-${jobId}`);
    if (!jobItem) {
        console.error(`Job item not found: ${jobId}`);
        return;
    }
    
    console.log(`Updating job ${jobId} with data:`, data);
    
    const statusElement = jobItem.querySelector('.status-label');
    const progressBar = jobItem.querySelector('.progress-bar');
    const progressText = jobItem.querySelector('.progress-text');
    const jobContent = jobItem.querySelector('.job-content');
    const jobInfo = jobItem.querySelector('.job-info');
    
    // Update progress
    if (progressBar && progressText) {
        const progress = data.progress || 0;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${Math.round(progress)}%`;
    }
    
    // If job completed successfully, show the video information or download button
    if (data.status === 'complete' || data.status === 'completed') {
        // Update status
        if (statusElement) {
            statusElement.textContent = 'Complete';
            statusElement.className = 'status-label complete';
        }
        
        // Remove any error messages that might exist
        const errorMsg = jobInfo.querySelector('.error-message');
        if (errorMsg) {
            errorMsg.remove();
        }
        
        // If we have a result with a filename, add download button
        if (data.result && data.result.filename) {
            // Create a basic video info display if we don't have detailed info
            if (jobContent) {
                const videoInfoContainer = document.createElement('div');
                videoInfoContainer.className = 'video-info-container basic-info';
                
                // Create a simplified info view
                videoInfoContainer.innerHTML = `
                    <div class="video-metadata">
                        <h3 class="video-title">Video Ready for Download</h3>
                        <p>Filename: ${data.result.filename}</p>
                        ${data.info ? '' : '<p class="info-note">Detailed video information not available</p>'}
                    </div>
                    <button class="btn btn-primary download-btn" data-job-id="${jobId}">Download Video</button>
                `;
                
                // Add click handler for download button
                const downloadBtn = videoInfoContainer.querySelector('.download-btn');
                if (downloadBtn) {
                    downloadBtn.addEventListener('click', () => {
                        const downloadPath = `/api/video-scraper/download-file/${data.result.filename}`;
                        window.open(downloadPath, '_blank');
                    });
                }
                
                // Clear any existing content and add our new content
                jobContent.innerHTML = '';
                jobContent.appendChild(videoInfoContainer);
            }
        }
        
        // Hide the cancel button
        const cancelBtn = jobItem.querySelector('.cancel-btn');
        if (cancelBtn) {
            cancelBtn.classList.add('hidden');
        }
    }
    // If job is still in progress
    else if (data.status === 'pending' || data.status === 'processing') {
        // Update status
        if (statusElement) {
            statusElement.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
            statusElement.className = `status-label ${data.status}`;
        }
    }
    // If job failed, show error message
    else if (data.status === 'failed' || data.status === 'error') {
        // Update status
        if (statusElement) {
            statusElement.textContent = 'Failed';
            statusElement.className = 'status-label failed';
        }
        
        // Check if error message already exists
        let errorMsg = jobInfo.querySelector('.error-message');
        if (!errorMsg && jobInfo) {
            errorMsg = document.createElement('div');
            errorMsg.className = 'error-message';
            jobInfo.appendChild(errorMsg);
        }
        
        if (errorMsg) {
            errorMsg.textContent = `Error: ${data.error || 'An error occurred during processing'}`;
        }
        
        // Hide the cancel button
        const cancelBtn = jobItem.querySelector('.cancel-btn');
        if (cancelBtn) {
            cancelBtn.classList.add('hidden');
        }
    }
    else {
        // Update status for other states
        if (statusElement) {
            statusElement.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
            statusElement.className = `status-label ${data.status}`;
        }
    }
}

/**
 * Cancel a job
 */
async function cancelJob(jobId) {
    try {
        const response = await fetch(`/api/job/${jobId}/cancel`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Update job in tracking map
            const job = activeJobs.get(jobId);
            if (job) {
                job.status = 'cancelled';
                updateJobItem(jobId, { status: 'cancelled', progress: job.progress });
            }
            
            showNotification(`Job ${jobId} cancelled successfully`, 'success');
        } else {
            showNotification(`Error cancelling job: ${data.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    }
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        if (show) {
            loadingOverlay.classList.remove('hidden');
        } else {
            loadingOverlay.classList.add('hidden');
        }
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', timeout = 3000) {
    // Check if notification container exists, create if not
    let notificationContainer = document.getElementById('notification-container');
    
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        document.body.appendChild(notificationContainer);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="message">${message}</span>
        </div>
        <button class="close-btn">&times;</button>
    `;
    
    // Add close button functionality
    const closeBtn = notification.querySelector('.close-btn');
    closeBtn.addEventListener('click', () => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            notification.remove();
        }, 300);
    });
    
    // Auto-remove after specified timeout
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, timeout);
    
    // Add to container
    notificationContainer.appendChild(notification);
    
    // Add fade-in animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
}

/**
 * Handle video search
 */
function handleSearch(e) {
    if (e) e.preventDefault();
    
    console.log('Search function called');
    
    const query = document.getElementById('search-query')?.value;
    if (!query || !query.trim()) {
        showNotification('Please enter a search query', 'error');
        return;
    }
    
    const platform = document.getElementById('search-platform')?.value || 'youtube';
    
    const searchResultsContainer = document.getElementById('search-results');
    if (!searchResultsContainer) {
        console.error('Search results container not found');
        return;
    }
    
    // Show loading indicator
    searchResultsContainer.innerHTML = '<div class="loading"><div class="spinner"></div><p>Searching...</p></div>';
    searchResultsContainer.style.display = 'block';
    
    // Build search URL
    const searchUrl = `/api/video-scraper/search?q=${encodeURIComponent(query)}&platform=${platform}`;
    console.log('Searching with URL:', searchUrl);
    
    // Call search API
    fetch(searchUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Search request failed with status ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Search results:', data);
            
            // Clear loading indicator
            searchResultsContainer.innerHTML = '';
            
            if (!data.results || data.results.length === 0) {
                searchResultsContainer.innerHTML = '<div class="no-results">No videos found. Try a different search term.</div>';
                return;
            }
            
            // Create results header
            const resultsHeader = document.createElement('div');
            resultsHeader.className = 'results-header';
            resultsHeader.innerHTML = `<h3>Search Results for "${query}"</h3>`;
            searchResultsContainer.appendChild(resultsHeader);
            
            // Create results grid
            const resultsGrid = document.createElement('div');
            resultsGrid.className = 'search-results-grid';
            
            // Add each result to the grid
            data.results.forEach(video => {
                const resultCard = document.createElement('div');
                resultCard.className = 'search-result-card';
                resultCard.dataset.url = video.url;
                
                // Create thumbnail
                const thumbnail = document.createElement('div');
                thumbnail.className = 'search-result-thumbnail';
                if (video.thumbnail) {
                    thumbnail.innerHTML = `<img src="${video.thumbnail}" alt="${video.title}" onerror="this.src='/static/images/default-thumbnail.png';">`;
                } else {
                    thumbnail.innerHTML = '<div class="no-thumbnail">No Thumbnail</div>';
                }
                
                // Create info section
                const info = document.createElement('div');
                info.className = 'search-result-info';
                
                // Create title and metadata
                const title = document.createElement('h4');
                title.className = 'search-result-title';
                title.textContent = video.title || 'Untitled Video';
                
                const metadata = document.createElement('div');
                metadata.className = 'search-result-metadata';
                
                let metadataContent = '';
                if (video.uploader) {
                    metadataContent += `<span class="uploader">${video.uploader}</span>`;
                }
                if (video.duration) {
                    metadataContent += `<span class="duration">${video.duration}</span>`;
                }
                if (video.platform) {
                    metadataContent += `<span class="platform">${video.platform}</span>`;
                }
                
                metadata.innerHTML = metadataContent;
                
                // Create action buttons
                const actions = document.createElement('div');
                actions.className = 'search-result-actions';
                
                const extractBtn = document.createElement('button');
                extractBtn.className = 'btn btn-primary btn-sm';
                extractBtn.textContent = 'Extract';
                extractBtn.addEventListener('click', function() {
                    extractVideo(video.url);
                    // Switch to URL tab to show progress
                    showTab('url-tab');
                });
                
                actions.appendChild(extractBtn);
                
                // Assemble everything
                info.appendChild(title);
                info.appendChild(metadata);
                info.appendChild(actions);
                
                resultCard.appendChild(thumbnail);
                resultCard.appendChild(info);
                
                resultsGrid.appendChild(resultCard);
            });
            
            searchResultsContainer.appendChild(resultsGrid);
        })
        .catch(error => {
            console.error('Search error:', error);
            searchResultsContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        });
}

/**
 * Add CSS for search results styling
 */
function addSearchResultsStyle() {
    // Check if style already exists
    if (!document.getElementById('search-results-style')) {
        const style = document.createElement('style');
        style.id = 'search-results-style';
        style.textContent = `
            .search-results {
                margin-top: 20px;
                border-top: 1px solid var(--border-color);
                padding-top: 15px;
            }
            .search-results-header {
                margin-bottom: 15px;
            }
            .search-results-header h3 {
                font-size: 16px;
                font-weight: 500;
            }
            .search-result-card {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                margin-bottom: 10px;
                border-radius: 8px;
                background-color: var(--card-bg);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            .search-result-thumbnail {
                width: 120px;
                height: 90px;
                margin-right: 15px;
                border-radius: 8px;
                overflow: hidden;
            }
            .search-result-thumbnail img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            .search-result-info {
                flex: 1;
            }
            .search-result-title {
                margin: 0 0 5px 0;
                font-size: 15px;
            }
            .search-result-metadata {
                margin: 0;
                font-size: 13px;
                color: var(--text-secondary);
            }
            .search-result-actions {
                display: flex;
                gap: 8px;
            }
            .no-results, .loading, .error {
                padding: 15px;
                text-align: center;
                color: var(--text-secondary);
            }
            .error {
                color: var(--error);
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Display video extraction results in a more visually appealing way
 */
function displayVideoInfo(jobId, videoInfo) {
    console.log(`Displaying video info for job ${jobId}:`, videoInfo);
    
    // Find job item by ID
    const jobItem = document.getElementById(`job-${jobId}`);
    
    if (!jobItem) {
        console.error(`Job item not found for ID: ${jobId}`);
        return;
    }
    
    // Create info container
    const infoContainer = document.createElement('div');
    infoContainer.className = 'video-info-container';
    
    // Add thumbnail if available
    if (videoInfo.thumbnail) {
        const thumbnail = document.createElement('img');
        thumbnail.src = videoInfo.thumbnail;
        thumbnail.alt = videoInfo.title || 'Video thumbnail';
        thumbnail.className = 'video-thumbnail';
        thumbnail.onerror = function() {
            this.src = '/static/images/default-thumbnail.png';
            this.alt = 'Thumbnail unavailable';
        };
        infoContainer.appendChild(thumbnail);
    }
    
    // Add title and metadata
    const metadataDiv = document.createElement('div');
    metadataDiv.className = 'video-metadata';
    
    const title = document.createElement('h3');
    title.textContent = videoInfo.title || 'Untitled Video';
    title.className = 'video-title';
    metadataDiv.appendChild(title);
    
    if (videoInfo.uploader) {
        const uploader = document.createElement('p');
        uploader.className = 'video-uploader';
        uploader.textContent = `Uploader: ${videoInfo.uploader}`;
        metadataDiv.appendChild(uploader);
    }
    
    infoContainer.appendChild(metadataDiv);
    
    // Add download button
    const downloadBtn = document.createElement('button');
    downloadBtn.className = 'btn btn-primary download-btn';
    downloadBtn.textContent = 'Download Video';
    downloadBtn.dataset.jobId = jobId;
    downloadBtn.addEventListener('click', handleDownload);
    
    infoContainer.appendChild(downloadBtn);
    
    // Find the job-content div and replace its content
    const contentDiv = jobItem.querySelector('.job-content');
    if (contentDiv) {
        contentDiv.innerHTML = '';
        contentDiv.appendChild(infoContainer);
    } else {
        console.error('No .job-content div found in job item');
    }
    
    // Remove any error messages that might have been added
    const errorMsg = jobItem.querySelector('.error-message');
    if (errorMsg) {
        errorMsg.remove();
    }
    
    // Update job status to show success
    const statusElement = jobItem.querySelector('.status-label');
    if (statusElement) {
        statusElement.textContent = 'Complete';
        statusElement.className = 'status-label complete';
    }
    
    // Show the results container
    showResults();
}

/**
 * Handle download button click
 */
function handleDownload(e) {
    const jobId = e.target.dataset.jobId;
    const formatSelector = document.querySelector(`.format-selector[data-job-id="${jobId}"]`);
    const formatId = formatSelector ? formatSelector.value : 'best';
    
    const jobItem = document.querySelector(`.job-item[data-job-id="${jobId}"]`);
    const jobContent = jobItem.querySelector('.job-content');
    const videoUrl = jobItem.dataset.url;
    
    if (!videoUrl) {
        showNotification('Error: Video URL not found', 'error');
        return;
    }
    
    // Show loading state
    jobContent.innerHTML = '<div class="loading-spinner"></div><p>Starting download...</p>';
    
    // Call API to start download
    fetch('/api/video-scraper/download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url: videoUrl,
            format_id: formatId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Store the download ID
        jobItem.dataset.downloadId = data.download_id;
        
        // Start polling for download progress
        pollDownloadProgress(jobItem, data.download_id);
        
        showNotification('Download started', 'success');
    })
    .catch(error => {
        jobContent.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
        showNotification(`Failed to start download: ${error.message}`, 'error');
    });
}

/**
 * Poll for download progress
 */
function pollDownloadProgress(jobItem, downloadId) {
    const jobContent = jobItem.querySelector('.job-content');
    const progressInterval = setInterval(() => {
        fetch(`/api/video-scraper/status/${downloadId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'completed') {
                    clearInterval(progressInterval);
                    
                    // Create download link
                    const downloadLink = document.createElement('a');
                    downloadLink.href = `/api/video-scraper/download/${data.filename}`;
                    downloadLink.className = 'btn btn-success';
                    downloadLink.textContent = 'Download File';
                    downloadLink.download = data.filename;
                    
                    jobContent.innerHTML = '<div class="success-message">Download complete!</div>';
                    jobContent.appendChild(downloadLink);
                    
                    showNotification('Download completed successfully', 'success');
                } 
                else if (data.status === 'failed') {
                    clearInterval(progressInterval);
                    jobContent.innerHTML = `<div class="error-message">Download failed: ${data.error || 'Unknown error'}</div>`;
                    showNotification(`Download failed: ${data.error || 'Unknown error'}`, 'error');
                }
                else if (data.progress) {
                    // Update progress bar
                    const progressPercent = Math.round(data.progress * 100);
                    jobContent.innerHTML = `
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progressPercent}%"></div>
                        </div>
                        <p>${progressPercent}% - ${data.status_message || 'Downloading...'}</p>
                    `;
                }
            })
            .catch(error => {
                console.error('Error checking download status:', error);
            });
    }, 1000);
    
    // Store the interval ID to cancel if needed
    jobItem.dataset.progressInterval = progressInterval;
}

/**
 * Enhanced function to process job completion with better display
 */
function processCompletedJob(jobId, data) {
    if (data.video_info) {
        displayVideoInfo(jobId, data.video_info);
    } else {
        updateJobItem(jobId, {
            status: 'failed',
            error: 'No video information available'
        });
    }
}

/**
 * Add a result item to the results list
 */
function addResultItem(message, type) {
    const resultsList = document.getElementById('results-list');
    const resultItem = document.createElement('div');
    resultItem.className = `result-item ${type}`;
    resultItem.innerHTML = `<p>${message}</p>`;
    resultsList.appendChild(resultItem);
}

/**
 * Update batch item status in results list
 */
function updateBatchItemStatus(index, status, message) {
    const resultItems = document.querySelectorAll('#results-list .result-item');
    if (index < resultItems.length) {
        const item = resultItems[index];
        
        // Add status class
        item.classList.add(status);
        
        // Update message
        if (message) {
            const p = item.querySelector('p');
            if (p) {
                p.innerHTML += ` <span class="status ${status}">${message}</span>`;
            }
        }
    }
}

/**
 * Fetch available downloads from the API
 */
function fetchAvailableDownloads() {
    fetch('/api/video-scraper/downloads')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Available downloads:', data);
            
            const downloadsContainer = document.getElementById('downloads-container');
            if (downloadsContainer) {
                // Clear existing content
                downloadsContainer.innerHTML = '';
                
                if (!data || !data.files || data.files.length === 0) {
                    downloadsContainer.innerHTML = '<div class="no-downloads">No downloads available</div>';
                    return;
                }
                
                // Create downloads header
                const downloadsHeader = document.createElement('div');
                downloadsHeader.className = 'downloads-header';
                downloadsHeader.innerHTML = `<h3>Available Downloads (${data.files.length})</h3>`;
                downloadsContainer.appendChild(downloadsHeader);
                
                // Create downloads list
                const downloadsList = document.createElement('div');
                downloadsList.className = 'downloads-list';
                
                // Add each download item
                data.files.forEach(file => {
                    // Skip files that don't exist on the server
                    if (!file.exists) {
                        return;
                    }
                    
                    const downloadItem = document.createElement('div');
                    downloadItem.className = 'download-item';
                    
                    // Format size
                    let sizeText = 'Unknown size';
                    if (file.size) {
                        const sizeInMB = (file.size / 1024 / 1024).toFixed(2);
                        sizeText = `${sizeInMB} MB`;
                    }
                    
                    // Format date
                    let dateText = 'Unknown date';
                    if (file.date) {
                        const date = new Date(file.date);
                        dateText = date.toLocaleString();
                    }
                    
                    downloadItem.innerHTML = `
                        <div class="download-info">
                            <h4>${file.filename}</h4>
                            <p>${sizeText} • ${dateText}</p>
                        </div>
                        <div class="download-actions">
                            <a href="/api/video-scraper/download-file/${file.filename}" class="btn btn-primary btn-sm" download>Download</a>
                        </div>
                    `;
                    
                    downloadsList.appendChild(downloadItem);
                });
                
                downloadsContainer.appendChild(downloadsList);
            }
        })
        .catch(error => {
            console.error('Error fetching downloads:', error);
            const downloadsContainer = document.getElementById('downloads-container');
            if (downloadsContainer) {
                downloadsContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            }
        });
}
