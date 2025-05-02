/**
 * TechSaaS Platform - Video Scraper JavaScript
 * Handles form submission, job tracking, and UI updates for the video scraper
 */

// Track active jobs
let activeJobs = new Map();
let pollInterval;

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
    init();
});

/**
 * Initialize the application
 */
function init() {
    // Attach event listeners
    document.getElementById('extract-btn')?.addEventListener('click', handleSingleExtraction);
    document.getElementById('batch-extract-btn')?.addEventListener('click', handleBatchExtraction);
    
    // Set up tab switching
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
            // Only handle normal tabs, not the Downloads tab
            if (tab.innerText !== 'Downloads') return;
            
            // Prevent default only for Downloads tab
            e.preventDefault();
            
            // Show downloads section
            showDownloadsTab();
        });
    });
    
    // Set up clear results button
    const clearResultsBtn = document.getElementById('clear-results');
    if (clearResultsBtn) {
        clearResultsBtn.addEventListener('click', clearResults);
    }
    
    // Show results container if we have jobs
    if (document.querySelectorAll('.job-item').length > 0) {
        document.getElementById('results-container').classList.remove('hidden');
        document.getElementById('results-container').style.display = 'block';
    }
    
    // Initial tab setup - show URL tab by default
    const urlTab = document.getElementById('url-tab');
    if (urlTab && !document.querySelector('.tab-container .tab.active')) {
        showTab('url-tab');
    }
    
    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('change', toggleTheme);
        // Check for saved theme preference
        if (localStorage.getItem('theme') === 'dark') {
            document.body.classList.add('dark-theme');
            themeToggle.checked = true;
        }
    }
    
    // Search button click handler
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }
    
    // Add the highlight style on load
    addHighlightStyle();
}

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
async function handleBatchExtraction(e) {
    e.preventDefault();
    
    // Get batch textarea content
    const batchUrlsTextarea = document.getElementById('url-list');
    if (!batchUrlsTextarea) {
        showNotification('Batch textarea not found', 'error');
        return;
    }
    
    const batchText = batchUrlsTextarea.value.trim();
    if (!batchText) {
        showNotification('Please enter at least one URL', 'error');
        return;
    }
    
    // Split by newlines or commas
    const urlList = batchText.split(/[\n,]+/).map(url => url.trim()).filter(url => url);
    
    if (urlList.length === 0) {
        showNotification('No valid URLs found', 'error');
        return;
    }
    
    // Get quality selection
    const qualitySelect = document.getElementById('batch-quality');
    const quality = qualitySelect ? qualitySelect.value : 'best';
    
    // Show batch preview grid
    const batchPreviewContainer = document.getElementById('batch-preview-container');
    if (batchPreviewContainer) {
        batchPreviewContainer.classList.remove('hidden');
    }
    
    // Show loading indicator
    showLoading(true);
    
    // Clear the preview grid
    const previewGrid = document.getElementById('preview-grid');
    if (previewGrid) {
        previewGrid.innerHTML = '';
    }
    
    // Process URLs
    await processBatchUrls(urlList, quality);
    
    // Hide loading indicator
    showLoading(false);
}

/**
 * Process a batch of URLs sequentially to avoid overwhelming the server
 */
async function processBatchUrls(urls, quality, startIndex = 0) {
    if (startIndex >= urls.length) {
        showNotification('Batch processing complete!', 'success');
        return;
    }
    
    const url = urls[startIndex];
    if (!url) {
        // Skip empty URLs
        processBatchUrls(urls, quality, startIndex + 1);
        return;
    }
    
    // Validate URL before sending
    if (!isValidUrl(url)) {
        console.log(`Skipping invalid URL: ${url}`);
        showNotification(`Skipped invalid URL: ${url}`, 'warning');
        // Add an error item to the results list
        addResultItem(`Invalid URL format: ${url}`, 'error');
        // Continue with next URL
        await processBatchUrls(urls, quality, startIndex + 1);
        return;
    }
    
    try {
        console.log(`Processing batch URL ${startIndex + 1}/${urls.length}: ${url}`);
        
        // Extract video
        const result = await extractVideo(url, quality);
        
        // If extraction failed, add an error result item
        if (!result) {
            addResultItem(`Failed to extract: ${url}`, 'error');
        }
        
        // Delay before processing next URL to avoid rate limiting
        setTimeout(() => {
            processBatchUrls(urls, quality, startIndex + 1);
        }, 1000);
    } catch (error) {
        console.error(`Error processing URL ${url}:`, error);
        addResultItem(`Error processing: ${url} - ${error.message}`, 'error');
        
        // Continue with next URL
        setTimeout(() => {
            processBatchUrls(urls, quality, startIndex + 1);
        }, 1000);
    }
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
    // Show loading state
    showLoading(true);
    
    try {
        // Basic validation
        if (!url || !url.trim()) {
            showNotification('Please enter a valid URL', 'error');
            showLoading(false);
            return false;
        }
        
        console.log(`Extracting video from URL: ${url}`);
        
        // Call extraction API
        const response = await fetch('/api/video-scraper/info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url, quality })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showNotification(`Error: ${data.error || 'Unknown error'}`, 'error');
            console.error('API Error:', data);
            return false;
        }
        
        if (data.job_id) {
            // Add job to tracking list
            trackJob(data.job_id);
            
            // Show results section
            showResults();
            
            // Show success notification
            showNotification('Video extraction started!', 'success');
            return true;
        } else {
            showNotification('No job ID returned from server', 'error');
            return false;
        }
    } catch (error) {
        console.error('Error extracting video:', error);
        showNotification(`Error: ${error.message || 'Unknown error'}`, 'error');
        return false;
    } finally {
        // Hide loading state
        showLoading(false);
    }
}

/**
 * Process a completed job
 */
function processCompletedJob(jobId, data) {
    console.log(`Processing completed job ${jobId}:`, data);
    
    // Add download button if we have a result
    if (data.result && data.result.filename) {
        addDownloadButton(jobId, data.result);
    }
}

/**
 * Add download button to completed job
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
    if (!jobItem) return;
    
    const statusElement = jobItem.querySelector('.status-label');
    const progressBar = jobItem.querySelector('.progress-bar');
    const progressText = jobItem.querySelector('.progress-text');
    
    // Update status
    if (statusElement) {
        statusElement.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        statusElement.className = `status-label ${data.status}`;
    }
    
    // Update progress
    if (progressBar && progressText) {
        const progress = data.progress || 0;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${Math.round(data.progress)}%`;
    }
    
    // If job completed successfully or failed, hide the cancel button
    if (data.status === 'complete' || data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
        const cancelBtn = jobItem.querySelector('.cancel-btn');
        if (cancelBtn) {
            cancelBtn.classList.add('hidden');
        }
        
        // Add error message if failed
        if (data.status === 'failed' && data.error) {
            const jobInfo = jobItem.querySelector('.job-info');
            
            // Check if error message already exists
            let errorMsg = jobItem.querySelector('.error-message');
            if (!errorMsg && jobInfo) {
                errorMsg = document.createElement('div');
                errorMsg.className = 'error-message';
                jobInfo.appendChild(errorMsg);
            }
            
            if (errorMsg) {
                errorMsg.textContent = `Error: ${data.error}`;
            }
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
    
    const query = document.getElementById('search-query').value.trim();
    const platform = document.getElementById('platform').value;
    
    if (!query) {
        showNotification('Please enter a search query', 'error');
        return;
    }
    
    // Show loading state
    showLoading(true);
    
    // Prepare search URL based on platform
    let searchUrl = '';
    switch(platform) {
        case 'youtube':
            searchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
            break;
        case 'vimeo':
            searchUrl = `https://vimeo.com/search?q=${encodeURIComponent(query)}`;
            break;
        case 'dailymotion':
            searchUrl = `https://www.dailymotion.com/search/${encodeURIComponent(query)}`;
            break;
        case 'all':
            // For all platforms, default to YouTube but show results for others too
            searchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
            break;
        default:
            searchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
    }
    
    // Create search results container if doesn't exist
    let searchResultsContainer = document.getElementById('search-results');
    if (!searchResultsContainer) {
        searchResultsContainer = document.createElement('div');
        searchResultsContainer.id = 'search-results';
        searchResultsContainer.className = 'search-results';
        document.getElementById('search-content').appendChild(searchResultsContainer);
    }
    
    // Clear previous search results
    searchResultsContainer.innerHTML = '';
    
    // Show search in progress
    searchResultsContainer.innerHTML = '<div class="loading-message">Searching videos...</div>';
    
    // For demonstration purposes, get search results from YouTube
    const xhr = new XMLHttpRequest();
    xhr.open('GET', `/api/video-scraper/search?q=${encodeURIComponent(query)}&platform=${platform}`, true);
    xhr.onload = function() {
        // Hide loading state
        showLoading(false);
        
        if (xhr.status === 200) {
            try {
                const data = JSON.parse(xhr.responseText);
                
                // Clear loading message
                searchResultsContainer.innerHTML = '';
                
                // Show results count
                const resultsHeader = document.createElement('div');
                resultsHeader.className = 'search-results-header';
                resultsHeader.innerHTML = `<h3>Found ${data.results.length} videos</h3>`;
                searchResultsContainer.appendChild(resultsHeader);
                
                // Add each result
                if (data.results.length === 0) {
                    searchResultsContainer.innerHTML += '<div class="no-results">No videos found. Try a different search term.</div>';
                } else {
                    data.results.forEach(result => {
                        const resultItem = document.createElement('div');
                        resultItem.className = 'search-result-item';
                        resultItem.innerHTML = `
                            <div class="result-info">
                                <h4>${result.title}</h4>
                                <p>${result.platform} • ${result.duration || 'Unknown duration'}</p>
                            </div>
                            <div class="result-actions">
                                <button class="btn btn-primary extract-btn" data-url="${result.url}">Extract</button>
                            </div>
                        `;
                        searchResultsContainer.appendChild(resultItem);
                        
                        // Add click handler for extract button
                        const extractBtn = resultItem.querySelector('.extract-btn');
                        extractBtn.addEventListener('click', function() {
                            const url = this.getAttribute('data-url');
                            extractVideo(url, 'best');
                        });
                    });
                }
            } catch (error) {
                console.error('Error parsing search results:', error);
                searchResultsContainer.innerHTML = '<div class="error-message">Error retrieving search results. Please try again.</div>';
            }
        } else {
            // Show mock results for demonstration if API not implemented
            searchResultsContainer.innerHTML = '';
            
            const mockResults = [
                { 
                    title: `${query} - YouTube Video 1`, 
                    platform: 'YouTube', 
                    duration: '5:23', 
                    // Use a known working YouTube video link instead of search results page
                    url: `https://www.youtube.com/watch?v=dQw4w9WgXcQ` 
                },
                { 
                    title: `${query} - ${platform} Video 2`, 
                    platform: platform, 
                    duration: '3:45', 
                    // Use another known working YouTube video
                    url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' 
                }
            ];
            
            // Show results count
            const resultsHeader = document.createElement('div');
            resultsHeader.className = 'search-results-header';
            resultsHeader.innerHTML = `<h3>Found ${mockResults.length} videos on ${platform}</h3>`;
            searchResultsContainer.appendChild(resultsHeader);
            
            // Add mock results
            mockResults.forEach(result => {
                const resultItem = document.createElement('div');
                resultItem.className = 'search-result-item';
                resultItem.innerHTML = `
                    <div class="result-info">
                        <h4>${result.title}</h4>
                        <p>${result.platform} • ${result.duration}</p>
                    </div>
                    <div class="result-actions">
                        <button class="btn btn-primary extract-btn" data-url="${result.url}">Extract</button>
                    </div>
                `;
                searchResultsContainer.appendChild(resultItem);
                
                // Add click handler for extract button
                const extractBtn = resultItem.querySelector('.extract-btn');
                extractBtn.addEventListener('click', function() {
                    const url = this.getAttribute('data-url');
                    // Switch to URL input tab first
                    showTab('url-tab');
                    // Set the URL in the input field
                    document.getElementById('video-url').value = url;
                    // Extract the video
                    extractVideo(url, 'best');
                });
            });
            
            // Add CSS for search results
            addSearchResultsStyle();
        }
    };
    xhr.onerror = function() {
        showLoading(false);
        searchResultsContainer.innerHTML = '<div class="error-message">Error connecting to search service. Please try again.</div>';
    };
    xhr.send();
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
            .search-result-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                margin-bottom: 10px;
                border-radius: 8px;
                background-color: var(--card-bg);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            .result-info {
                flex: 1;
            }
            .result-info h4 {
                margin: 0 0 5px 0;
                font-size: 15px;
            }
            .result-info p {
                margin: 0;
                font-size: 13px;
                color: var(--text-secondary);
            }
            .result-actions {
                display: flex;
                gap: 8px;
            }
            .no-results, .loading-message, .error-message {
                padding: 15px;
                text-align: center;
                color: var(--text-secondary);
            }
            .error-message {
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
    const resultsList = document.getElementById('results-list');
    const resultItem = document.querySelector(`.job-item[data-job-id="${jobId}"]`);
    
    if (!resultItem) return;
    
    // Clear loading state
    resultItem.classList.remove('loading');
    
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
            this.src = '/static/images/no-thumbnail.png';
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
    
    if (videoInfo.duration) {
        const duration = document.createElement('p');
        duration.className = 'video-duration';
        // Convert seconds to MM:SS format
        const minutes = Math.floor(videoInfo.duration / 60);
        const seconds = Math.floor(videoInfo.duration % 60);
        duration.textContent = `Duration: ${minutes}:${seconds.toString().padStart(2, '0')}`;
        metadataDiv.appendChild(duration);
    }
    
    infoContainer.appendChild(metadataDiv);
    
    // Add format selector if formats are available
    if (videoInfo.formats && videoInfo.formats.length > 0) {
        const formatSelector = document.createElement('select');
        formatSelector.className = 'format-selector';
        formatSelector.dataset.jobId = jobId;
        
        videoInfo.formats.forEach(format => {
            const option = document.createElement('option');
            option.value = format.format_id;
            
            // Create descriptive label
            let label = `${format.format_note || format.format || 'Unknown'}`;
            if (format.filesize) {
                // Convert to MB and round to 1 decimal place
                const sizeMB = (format.filesize / 1024 / 1024).toFixed(1);
                label += ` - ${sizeMB} MB`;
            }
            if (format.ext) {
                label += ` (.${format.ext})`;
            }
            
            option.textContent = label;
            formatSelector.appendChild(option);
        });
        
        const formatDiv = document.createElement('div');
        formatDiv.className = 'format-selection';
        
        const label = document.createElement('label');
        label.textContent = 'Select Format:';
        label.htmlFor = `format-select-${jobId}`;
        formatSelector.id = `format-select-${jobId}`;
        
        formatDiv.appendChild(label);
        formatDiv.appendChild(formatSelector);
        
        infoContainer.appendChild(formatDiv);
    }
    
    // Add download button
    const downloadBtn = document.createElement('button');
    downloadBtn.className = 'btn btn-primary download-btn';
    downloadBtn.textContent = 'Download Video';
    downloadBtn.dataset.jobId = jobId;
    downloadBtn.addEventListener('click', handleDownload);
    
    infoContainer.appendChild(downloadBtn);
    
    // Replace content in result item
    const contentDiv = resultItem.querySelector('.job-content');
    if (contentDiv) {
        contentDiv.innerHTML = '';
        contentDiv.appendChild(infoContainer);
    }
    
    // Store the video URL in the job item for later use
    resultItem.dataset.url = videoInfo.webpage_url || videoInfo.url;
    
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
