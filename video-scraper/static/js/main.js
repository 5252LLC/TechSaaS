/**
 * TechSaaS Platform - Video Scraper JavaScript
 * Handles form submission, job tracking, and UI updates for the video scraper
 */

// Track active jobs
let activeJobs = new Map();
let pollInterval;

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
    // Tab switching logic
    const tabs = document.querySelectorAll('.tab-container .tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
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
    
    // Extract button click handler
    const extractBtn = document.getElementById('extract-btn');
    if (extractBtn) {
        extractBtn.addEventListener('click', handleExtractVideo);
    }
    
    // Batch extract button click handler
    const batchExtractBtn = document.getElementById('batch-extract-btn');
    if (batchExtractBtn) {
        batchExtractBtn.addEventListener('click', handleBatchExtract);
    }
    
    // Search button click handler
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }
    
    // Clear results button click handler
    const clearResultsBtn = document.getElementById('clear-results');
    if (clearResultsBtn) {
        clearResultsBtn.addEventListener('click', clearResults);
    }
});

/**
 * Switch between tabs in the interface
 */
function showTab(tabId) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.tab-container .tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab content
    document.getElementById(tabId).classList.add('active');
    const contentId = tabId.replace('-tab', '-content');
    document.getElementById(contentId).classList.add('active');
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
 * Handle the video extraction form submission
 */
async function handleExtractVideo() {
    const videoUrl = document.getElementById('video-url').value.trim();
    if (!videoUrl) {
        showNotification('Please enter a valid URL', 'error');
        return;
    }
    
    const quality = document.getElementById('quality').value;
    const outputDir = document.getElementById('output-dir').value;
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: videoUrl,
                quality: quality,
                output_dir: outputDir
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Start tracking the job
            trackJob(data.job_id);
            showNotification(`Video extraction started (Job ID: ${data.job_id})`, 'success');
        } else {
            showNotification(`Error: ${data.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Handle batch video extraction
 */
async function handleBatchExtract() {
    const urlList = document.getElementById('url-list').value.trim();
    if (!urlList) {
        showNotification('Please enter at least one URL', 'error');
        return;
    }
    
    const urls = urlList.split('\n').filter(url => url.trim() !== '');
    if (urls.length === 0) {
        showNotification('Please enter at least one valid URL', 'error');
        return;
    }
    
    const quality = document.getElementById('batch-quality').value;
    const outputDir = document.getElementById('output-dir').value || 'downloads';
    
    showLoading(true);
    
    try {
        // Process each URL sequentially
        for (const url of urls) {
            if (!url.trim()) continue;
            
            const response = await fetch('/api/extract', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url.trim(),
                    quality: quality,
                    output_dir: outputDir
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Start tracking the job
                trackJob(data.job_id);
                addResultItem(`Started extraction for: ${url} (Job ID: ${data.job_id})`, 'info');
            } else {
                addResultItem(`Failed to extract ${url}: ${data.error || 'Unknown error'}`, 'error');
            }
        }
        
        showNotification(`Batch extraction started for ${urls.length} URLs`, 'success');
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Handle search form submission
 */
async function handleSearch() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) {
        showNotification('Please enter a search query', 'error');
        return;
    }
    
    const platform = document.getElementById('platform').value;
    
    showLoading(true);
    
    try {
        // This is a placeholder for actual search API
        // Simulate search results
        setTimeout(() => {
            // Mock search results
            const results = [
                { title: 'Sample Video 1', url: 'https://example.com/video1', thumbnail: 'https://via.placeholder.com/150', duration: '3:45' },
                { title: 'Sample Video 2', url: 'https://example.com/video2', thumbnail: 'https://via.placeholder.com/150', duration: '2:30' },
                { title: 'Sample Video 3', url: 'https://example.com/video3', thumbnail: 'https://via.placeholder.com/150', duration: '1:15' }
            ];
            
            // Display results
            showResults();
            results.forEach(result => {
                addSearchResult(result);
            });
            
            showNotification(`Found ${results.length} results for "${query}"`, 'success');
            showLoading(false);
        }, 1500);
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
        showLoading(false);
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
 * Poll server for job status updates
 */
async function pollActiveJobs() {
    const jobIds = Array.from(activeJobs.keys());
    
    if (jobIds.length === 0) {
        // No active jobs, clear interval
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
        return;
    }
    
    // Check each job's status
    for (const jobId of jobIds) {
        try {
            const job = activeJobs.get(jobId);
            
            // Skip jobs that are already complete or failed
            if (job && (job.status === 'complete' || job.status === 'completed' || 
                job.status === 'failed' || job.status === 'cancelled')) {
                // Remove job from active jobs
                activeJobs.delete(jobId);
                continue;
            }
            
            const response = await fetch(`/api/job/${jobId}`);
            
            if (response.ok) {
                const data = await response.json();
                
                // Update job in tracking map
                activeJobs.set(jobId, data);
                
                // Update UI
                updateJobItem(jobId, data);
                
                // If job is complete, process result
                if (data.status === 'complete' || data.status === 'completed') {
                    processCompletedJob(jobId, data);
                    // Remove job from active jobs
                    activeJobs.delete(jobId);
                }
                
                // If job failed or was cancelled, remove from active jobs
                if (data.status === 'failed' || data.status === 'cancelled') {
                    activeJobs.delete(jobId);
                }
            } else {
                console.error(`Error fetching job status: ${response.status}`);
                // Remove job after error (optional, can also keep trying)
                activeJobs.delete(jobId);
            }
        } catch (error) {
            console.error(`Error polling job ${jobId}:`, error);
            // Remove job after error (optional, can also keep trying)
            activeJobs.delete(jobId);
        }
    }
    
    // If no more active jobs, clear the interval
    if (activeJobs.size === 0 && pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
        console.log('All jobs completed, polling stopped');
    }
}

/**
 * Process a completed job
 */
function processCompletedJob(jobId, data) {
    // Check if the job has a result with a filename
    if (data.result && data.result.filename) {
        addDownloadButton(jobId, data.result);
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
        progressText.textContent = `${progress}%`;
    }
    
    // Handle completed job (check for both 'completed' and 'complete' status)
    if (data.status === 'complete' || data.status === 'completed') {
        // Add download button if result is available
        if (data.result && data.result.filename) {
            addDownloadButton(jobId, data.result);
        }
        
        // Hide cancel button
        const cancelBtn = jobItem.querySelector('.cancel-btn');
        if (cancelBtn) {
            cancelBtn.style.display = 'none';
        }
    }
    
    // Hide cancel button if job is failed or cancelled
    if (data.status === 'failed' || data.status === 'cancelled') {
        const cancelBtn = jobItem.querySelector('.cancel-btn');
        if (cancelBtn) {
            cancelBtn.style.display = 'none';
        }
    }
    
    // Show error message if job failed
    if (data.status === 'failed' && data.error) {
        const jobInfo = jobItem.querySelector('.job-info');
        
        // Check if error message already exists
        if (!jobItem.querySelector('.error-message')) {
            const errorElement = document.createElement('div');
            errorElement.className = 'error-message';
            errorElement.textContent = `Error: ${data.error}`;
            jobInfo.appendChild(errorElement);
        }
    }
}

/**
 * Add download button to a completed job
 */
function addDownloadButton(jobId, result) {
    const jobElement = document.getElementById(`job-${jobId}`);
    if (!jobElement) return;
    
    // Check if download button already exists
    if (jobElement.querySelector('.download-btn')) return;
    
    const downloadUrl = `/downloads/${result.filename}`;
    
    // Create download button
    const downloadLink = document.createElement('a');
    downloadLink.href = downloadUrl;
    downloadLink.className = 'btn btn-primary download-btn';
    downloadLink.textContent = '⬇️ Download Video';
    downloadLink.download = result.filename;
    downloadLink.style.display = 'block';
    downloadLink.style.margin = '10px 0';
    downloadLink.style.fontWeight = 'bold';
    
    // Find or create actions div
    let actionsDiv = jobElement.querySelector('.job-actions');
    if (!actionsDiv) {
        actionsDiv = document.createElement('div');
        actionsDiv.className = 'job-actions';
        jobElement.appendChild(actionsDiv);
    }
    
    // Clear any existing content in actions div
    actionsDiv.innerHTML = '';
    
    // Add download button
    actionsDiv.appendChild(downloadLink);
    
    // Add a notification
    showNotification(`Video download ready! Click the download button to save.`, 'success');
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
 * Add a search result to the results list
 */
function addSearchResult(result) {
    showResults();
    
    const resultsContainer = document.getElementById('results-list');
    
    const resultItem = document.createElement('div');
    resultItem.className = 'result-item search-result';
    
    resultItem.innerHTML = `
        <div class="search-result-content">
            <div class="thumbnail">
                <img src="${result.thumbnail}" alt="${result.title}">
                <span class="duration">${result.duration}</span>
            </div>
            <div class="result-info">
                <h3>${result.title}</h3>
                <p class="result-url">${result.url}</p>
            </div>
        </div>
        <div class="result-actions">
            <button class="btn btn-primary extract-btn" data-url="${result.url}">Extract</button>
        </div>
    `;
    
    // Add event listener for extract button
    const extractBtn = resultItem.querySelector('.extract-btn');
    extractBtn.addEventListener('click', () => {
        document.getElementById('video-url').value = result.url;
        showTab('url-tab');
        handleExtractVideo();
    });
    
    resultsContainer.appendChild(resultItem);
}

/**
 * Add a generic result item to the results list
 */
function addResultItem(message, type = 'info') {
    showResults();
    
    const resultsContainer = document.getElementById('results-list');
    
    const resultItem = document.createElement('div');
    resultItem.className = `result-item ${type}-item`;
    resultItem.innerHTML = `<p>${message}</p>`;
    
    resultsContainer.appendChild(resultItem);
}

/**
 * Show results container
 */
function showResults() {
    const resultsContainer = document.getElementById('results-container');
    if (resultsContainer) {
        resultsContainer.style.display = 'block';
    }
}

/**
 * Clear all results
 */
function clearResults() {
    const resultsContainer = document.getElementById('results-list');
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
        document.getElementById('results-container').style.display = 'none';
    }
    
    // Clear active jobs too (except those in progress)
    for (const [jobId, job] of activeJobs.entries()) {
        if (job.status !== 'processing') {
            activeJobs.delete(jobId);
        }
    }
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
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
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, 5000);
    
    // Add to container
    notificationContainer.appendChild(notification);
    
    // Add fade-in animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
}
