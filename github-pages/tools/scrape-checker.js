/**
 * TechSaaS Web Scraping Readiness Checker
 * Client-side tool to analyze websites for scraping feasibility
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const urlInput = document.getElementById('urlInput');
    const checkButton = document.getElementById('checkButton');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultsContainer = document.getElementById('resultsContainer');
    const scoreCircle = document.getElementById('scoreCircle');
    const scoreValue = document.getElementById('scoreValue');
    const scoreTitle = document.getElementById('scoreTitle');
    const scoreSummary = document.getElementById('scoreSummary');
    const factorsGrid = document.getElementById('factorsGrid');
    const recommendationsList = document.getElementById('recommendationsList');
    const methodsGrid = document.getElementById('methodsGrid');
    const sampleLinks = document.querySelectorAll('.sample-link');

    // Add SVG gradient (needs to be added dynamically for Safari compatibility)
    const svg = document.querySelector('.score-chart');
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const gradient = document.createElementNS("http://www.w3.org/2000/svg", "linearGradient");
    gradient.setAttribute("id", "scoreGradient");
    gradient.setAttribute("x1", "0%");
    gradient.setAttribute("y1", "0%");
    gradient.setAttribute("x2", "100%");
    gradient.setAttribute("y2", "0%");
    
    const stop1 = document.createElementNS("http://www.w3.org/2000/svg", "stop");
    stop1.setAttribute("offset", "0%");
    stop1.setAttribute("stop-color", "#3b82f6");
    
    const stop2 = document.createElementNS("http://www.w3.org/2000/svg", "stop");
    stop2.setAttribute("offset", "100%");
    stop2.setAttribute("stop-color", "#60a5fa");
    
    gradient.appendChild(stop1);
    gradient.appendChild(stop2);
    defs.appendChild(gradient);
    svg.prepend(defs);

    // Sample data for demonstration purposes
    const sampleData = {
        'https://news.ycombinator.com': {
            score: 85,
            title: 'Highly Scrapable',
            summary: 'Hacker News has a clean, minimal HTML structure that makes it relatively easy to scrape. The site doesn\'t use much JavaScript for content rendering and provides a consistent DOM structure.',
            factors: [
                { name: 'Static Content', status: 'green', description: 'Minimal JavaScript, mostly static HTML' },
                { name: 'Clean Structure', status: 'green', description: 'Simple, consistent DOM hierarchy' },
                { name: 'Robot.txt', status: 'yellow', description: 'Some restrictions for certain crawlers' },
                { name: 'Rate Limiting', status: 'yellow', description: 'Moderate rate limiting detected' },
                { name: 'Anti-Bot Measures', status: 'green', description: 'No significant anti-bot measures detected' },
                { name: 'AJAX Content', status: 'green', description: 'No dynamic content loading' }
            ],
            recommendations: [
                'Implement a modest delay (2-3 seconds) between requests to avoid triggering rate limits',
                'Respect the robots.txt directives that may apply to your crawler',
                'Use CSS selectors for extraction as the DOM structure is consistent',
                'Consider implementing user-agent rotation as a precaution'
            ],
            methods: [
                { name: 'Beautiful Soup', icon: 'fa-brands fa-python', rating: 5, description: 'Ideal for this static HTML structure' },
                { name: 'Newspaper3k', icon: 'fa-solid fa-newspaper', rating: 4, description: 'Good for article extraction' },
                { name: 'Requests-HTML', icon: 'fa-solid fa-code', rating: 4, description: 'Simple parsing with Python' },
                { name: 'Scrapy', icon: 'fa-solid fa-spider', rating: 5, description: 'Efficient for structured data' }
            ]
        },
        'https://reddit.com': {
            score: 45,
            title: 'Moderately Challenging',
            summary: 'Reddit relies heavily on JavaScript for content rendering, uses infinite scrolling, and has some anti-scraping measures in place. However, their official API provides a better alternative for data collection.',
            factors: [
                { name: 'Static Content', status: 'red', description: 'Highly dynamic, JavaScript-rendered content' },
                { name: 'Clean Structure', status: 'yellow', description: 'Complex but consistent DOM structure' },
                { name: 'Robot.txt', status: 'yellow', description: 'Restrictive for some sections' },
                { name: 'Rate Limiting', status: 'red', description: 'Aggressive rate limiting detected' },
                { name: 'Anti-Bot Measures', status: 'red', description: 'CAPTCHA and other protection mechanisms' },
                { name: 'AJAX Content', status: 'red', description: 'Extensive dynamic content loading' }
            ],
            recommendations: [
                'Consider using the official Reddit API instead of scraping the website directly',
                'If scraping is necessary, use a headless browser like Playwright or Puppeteer',
                'Implement significant delays between requests (5+ seconds)',
                'Rotate IPs and user agents to reduce the risk of being blocked',
                'Handle CAPTCHAs and login requirements carefully'
            ],
            methods: [
                { name: 'Playwright', icon: 'fa-solid fa-theater-masks', rating: 4, description: 'Handles dynamic JavaScript content' },
                { name: 'Puppeteer', icon: 'fa-solid fa-ghost', rating: 4, description: 'Good for rendering JS content' },
                { name: 'Reddit API', icon: 'fa-brands fa-reddit-alien', rating: 5, description: 'Official API - recommended' },
                { name: 'Selenium', icon: 'fa-solid fa-robot', rating: 3, description: 'Can work but slower' }
            ]
        },
        'https://github.com': {
            score: 65,
            title: 'Conditionally Scrapable',
            summary: 'GitHub has a well-structured HTML layout with some JavaScript enhancements. While the site has rate limiting and authentication requirements for certain areas, public repositories and profiles can be scraped with proper techniques.',
            factors: [
                { name: 'Static Content', status: 'yellow', description: 'Mix of static and dynamic content' },
                { name: 'Clean Structure', status: 'green', description: 'Well-structured, semantic HTML' },
                { name: 'Robot.txt', status: 'yellow', description: 'Some sections are disallowed' },
                { name: 'Rate Limiting', status: 'yellow', description: 'Moderate rate limiting for anonymous access' },
                { name: 'Anti-Bot Measures', status: 'yellow', description: 'Some protection mechanisms in place' },
                { name: 'AJAX Content', status: 'yellow', description: 'Portions of content load dynamically' }
            ],
            recommendations: [
                'Use the official GitHub API for production applications instead of scraping',
                'If scraping is needed, authenticate requests to increase rate limits',
                'Implement a delay of 3-5 seconds between requests',
                'Use conditional requests with If-Modified-Since to reduce bandwidth',
                'Respect robots.txt directives, especially for private areas'
            ],
            methods: [
                { name: 'GitHub API', icon: 'fa-brands fa-github', rating: 5, description: 'Official API - recommended' },
                { name: 'Requests + BS4', icon: 'fa-solid fa-code', rating: 4, description: 'Good for public pages' },
                { name: 'Playwright', icon: 'fa-solid fa-theater-masks', rating: 3, description: 'For JavaScript-heavy pages' },
                { name: 'Scrapy', icon: 'fa-solid fa-spider', rating: 3, description: 'Useful for repository scraping' }
            ]
        }
    };

    // Demo websites for quick testing
    sampleLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('data-url');
            urlInput.value = url;
            analyzeWebsite(url);
        });
    });

    // Analyze button click handler
    checkButton.addEventListener('click', function() {
        const url = urlInput.value.trim();
        if (isValidURL(url)) {
            analyzeWebsite(url);
        } else {
            alert('Please enter a valid URL (e.g., https://example.com)');
        }
    });

    // URL input - listen for Enter key
    urlInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const url = urlInput.value.trim();
            if (isValidURL(url)) {
                analyzeWebsite(url);
            } else {
                alert('Please enter a valid URL (e.g., https://example.com)');
            }
        }
    });

    // Main analysis function
    function analyzeWebsite(url) {
        // Reset previous results
        factorsGrid.innerHTML = '';
        recommendationsList.innerHTML = '';
        methodsGrid.innerHTML = '';
        
        // Show loading indicator
        resultsContainer.classList.add('hidden');
        loadingIndicator.classList.remove('hidden');
        
        // For demonstration purposes, we'll use predefined sample data
        // In a real implementation, this would make API calls or analyze on the client side
        
        setTimeout(() => {
            // Hide loading indicator
            loadingIndicator.classList.add('hidden');
            
            // Get sample data or generate random data if URL not in samples
            let data;
            
            if (sampleData[url]) {
                data = sampleData[url];
            } else {
                // Generate random data for demonstration
                data = generateRandomData(url);
            }
            
            // Update score
            updateScore(data.score);
            scoreTitle.textContent = data.title;
            scoreSummary.textContent = data.summary;
            
            // Populate factors
            data.factors.forEach(factor => {
                factorsGrid.appendChild(createFactorElement(factor));
            });
            
            // Populate recommendations
            data.recommendations.forEach(recommendation => {
                recommendationsList.appendChild(createRecommendationElement(recommendation));
            });
            
            // Populate methods
            data.methods.forEach(method => {
                methodsGrid.appendChild(createMethodElement(method));
            });
            
            // Show results
            resultsContainer.classList.remove('hidden');
            
            // Scroll to results with smooth animation
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 2000); // Simulated 2-second analysis time
    }

    // Update score circle with animation
    function updateScore(score) {
        // Update score text
        scoreValue.textContent = score;
        
        // Update circle progress (using CSS variable)
        scoreCircle.style.setProperty('--percent', score);
        
        // Set color class based on score
        if (score >= 70) {
            scoreValue.setAttribute('fill', '#10b981'); // green
        } else if (score >= 40) {
            scoreValue.setAttribute('fill', '#f59e0b'); // yellow
        } else {
            scoreValue.setAttribute('fill', '#ef4444'); // red
        }
    }

    // Create a factor element
    function createFactorElement(factor) {
        const factorItem = document.createElement('div');
        factorItem.className = 'factor-item';
        
        factorItem.innerHTML = `
            <div class="factor-icon ${factor.status}">
                <i class="fas ${
                    factor.status === 'green' ? 'fa-check' : 
                    factor.status === 'yellow' ? 'fa-exclamation' : 
                    'fa-times'
                }"></i>
            </div>
            <div class="factor-content">
                <h4>${factor.name}</h4>
                <p>${factor.description}</p>
            </div>
        `;
        
        return factorItem;
    }

    // Create a recommendation element
    function createRecommendationElement(recommendation) {
        const recommendationItem = document.createElement('div');
        recommendationItem.className = 'recommendation-item';
        
        recommendationItem.innerHTML = `
            <div class="recommendation-icon">
                <i class="fas fa-check-circle"></i>
            </div>
            <div class="recommendation-text">${recommendation}</div>
        `;
        
        return recommendationItem;
    }

    // Create a method element
    function createMethodElement(method) {
        const methodCard = document.createElement('div');
        methodCard.className = 'method-card';
        
        // Create stars based on rating
        let stars = '';
        for (let i = 0; i < 5; i++) {
            if (i < method.rating) {
                stars += '<i class="fas fa-star star"></i>';
            } else {
                stars += '<i class="far fa-star star"></i>';
            }
        }
        
        methodCard.innerHTML = `
            <div class="method-icon">
                <i class="${method.icon}"></i>
            </div>
            <div class="method-name">${method.name}</div>
            <div class="method-rating">${stars}</div>
            <div class="method-info">${method.description}</div>
        `;
        
        return methodCard;
    }

    // Generate random analysis data for demo purposes
    function generateRandomData(url) {
        const hostname = new URL(url).hostname;
        
        // Random score between 30 and 90
        const score = Math.floor(Math.random() * 61) + 30;
        
        // Determine title and summary based on score
        let title, summary;
        if (score >= 70) {
            title = 'Highly Scrapable';
            summary = `${hostname} appears to have a favorable structure for web scraping with minimal protections in place.`;
        } else if (score >= 40) {
            title = 'Moderately Challenging';
            summary = `${hostname} has some anti-scraping measures and may require advanced techniques for reliable data extraction.`;
        } else {
            title = 'Difficult to Scrape';
            summary = `${hostname} employs significant anti-scraping measures that make data extraction challenging without specialized tools.`;
        }
        
        // Generate random factors
        const staticStatus = randomStatus();
        const structureStatus = randomStatus();
        const robotStatus = randomStatus();
        const rateStatus = randomStatus();
        const antiStatus = randomStatus();
        const ajaxStatus = randomStatus();
        
        return {
            score: score,
            title: title,
            summary: summary,
            factors: [
                { name: 'Static Content', status: staticStatus, description: staticStatus === 'green' ? 'Mostly static HTML content' : staticStatus === 'yellow' ? 'Mix of static and dynamic content' : 'Highly dynamic, JavaScript-rendered content' },
                { name: 'Clean Structure', status: structureStatus, description: structureStatus === 'green' ? 'Clean, consistent DOM structure' : structureStatus === 'yellow' ? 'Moderately complex DOM structure' : 'Complex, inconsistent DOM structure' },
                { name: 'Robot.txt', status: robotStatus, description: robotStatus === 'green' ? 'No significant restrictions' : robotStatus === 'yellow' ? 'Some sections restricted' : 'Highly restrictive robots.txt' },
                { name: 'Rate Limiting', status: rateStatus, description: rateStatus === 'green' ? 'No apparent rate limiting' : rateStatus === 'yellow' ? 'Moderate rate limiting detected' : 'Aggressive rate limiting detected' },
                { name: 'Anti-Bot Measures', status: antiStatus, description: antiStatus === 'green' ? 'Minimal anti-bot protection' : antiStatus === 'yellow' ? 'Some anti-bot measures' : 'Strong anti-bot protection (CAPTCHA, etc.)' },
                { name: 'AJAX Content', status: ajaxStatus, description: ajaxStatus === 'green' ? 'No reliance on AJAX for content' : ajaxStatus === 'yellow' ? 'Some content loaded via AJAX' : 'Heavy reliance on AJAX for content loading' }
            ],
            recommendations: generateRecommendations(staticStatus, robotStatus, rateStatus, antiStatus, ajaxStatus),
            methods: generateMethods(staticStatus, ajaxStatus)
        };
    }

    // Generate random status (green, yellow, red)
    function randomStatus() {
        const statuses = ['green', 'yellow', 'red'];
        return statuses[Math.floor(Math.random() * statuses.length)];
    }

    // Generate recommendations based on factors
    function generateRecommendations(staticStatus, robotStatus, rateStatus, antiStatus, ajaxStatus) {
        const recommendations = [];
        
        if (rateStatus === 'yellow' || rateStatus === 'red') {
            recommendations.push('Implement a delay between requests to avoid triggering rate limits' + (rateStatus === 'red' ? ' (5+ seconds recommended)' : ' (2-3 seconds recommended)'));
        }
        
        if (robotStatus === 'yellow' || robotStatus === 'red') {
            recommendations.push('Carefully check and respect the robots.txt directives for this website');
        }
        
        if (staticStatus === 'yellow' || staticStatus === 'red') {
            recommendations.push('Use a JavaScript-capable scraper like Playwright or Puppeteer to handle dynamic content');
        }
        
        if (antiStatus === 'yellow' || antiStatus === 'red') {
            recommendations.push('Implement user-agent and IP rotation to reduce the risk of being blocked');
        }
        
        if (ajaxStatus === 'yellow' || ajaxStatus === 'red') {
            recommendations.push('Configure appropriate wait times for AJAX content to fully load before extracting data');
        }
        
        // Add general recommendations
        recommendations.push('Verify the website\'s terms of service regarding automated access before scraping');
        
        if (recommendations.length < 3) {
            recommendations.push('Consider using CSS selectors for extraction as they\'re generally more resilient to minor HTML changes');
        }
        
        return recommendations;
    }

    // Generate recommended methods based on factors
    function generateMethods(staticStatus, ajaxStatus) {
        const methods = [];
        
        if (staticStatus === 'green') {
            methods.push({ name: 'Beautiful Soup', icon: 'fa-brands fa-python', rating: 5, description: 'Perfect for static HTML content' });
            methods.push({ name: 'Scrapy', icon: 'fa-solid fa-spider', rating: 4, description: 'Efficient for structured data' });
        }
        
        if (staticStatus === 'yellow' || ajaxStatus === 'yellow') {
            methods.push({ name: 'Requests-HTML', icon: 'fa-solid fa-code', rating: 4, description: 'Handles basic JavaScript' });
            methods.push({ name: 'Scrapy + Splash', icon: 'fa-solid fa-spider', rating: 3, description: 'Scrapy with JS rendering' });
        }
        
        if (staticStatus === 'red' || ajaxStatus === 'red') {
            methods.push({ name: 'Playwright', icon: 'fa-solid fa-theater-masks', rating: 5, description: 'Excellent for dynamic content' });
            methods.push({ name: 'Puppeteer', icon: 'fa-solid fa-ghost', rating: 4, description: 'Good for JavaScript-heavy sites' });
        }
        
        // Always add Selenium as a general purpose tool
        methods.push({ name: 'Selenium', icon: 'fa-solid fa-robot', rating: staticStatus === 'red' ? 4 : 3, description: 'Versatile but slower option' });
        
        // Add a random specialized tool
        const specializedTools = [
            { name: 'Newspaper3k', icon: 'fa-solid fa-newspaper', rating: 4, description: 'Optimized for news articles' },
            { name: 'ParseHub', icon: 'fa-solid fa-cloud-download-alt', rating: 4, description: 'Visual scraping tool' },
            { name: 'Octoparse', icon: 'fa-solid fa-table', rating: 3, description: 'No-code scraping solution' },
            { name: 'Diffbot', icon: 'fa-solid fa-brain', rating: 5, description: 'AI-powered data extraction' }
        ];
        
        methods.push(specializedTools[Math.floor(Math.random() * specializedTools.length)]);
        
        return methods;
    }

    // Validate URL
    function isValidURL(url) {
        try {
            new URL(url);
            return true;
        } catch (err) {
            return false;
        }
    }
});
