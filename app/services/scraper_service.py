"""
Scraper Service for TechSaaS

This module provides web scraping functionality with ban avoidance techniques including:
- Proxy rotation
- User-agent rotation
- Rate limiting
- Request throttling
- Header randomization
"""
import os
import time
import random
import logging
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from flask import current_app

from app import db
from app.models.scraped_data.scraped_data import ScrapedData

# Configure logging
logger = logging.getLogger(__name__)

# User-Agent list for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36 Edg/93.0.961.52',
    'Mozilla/5.0 (X11; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:92.0) Gecko/20100101 Firefox/92.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
]

# Default headers
DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
}

# Proxy configuration
def get_proxies():
    """
    Get a list of proxies for rotation.
    Returns:
        List of proxy configurations or None if no proxies are configured
    """
    # Check if Firecrawl API key is configured
    firecrawl_api_key = current_app.config.get('FIRECRAWL_API_KEY')
    if firecrawl_api_key:
        return get_firecrawl_proxies(firecrawl_api_key)
    
    # Check if Bright Data proxies are configured
    bright_data_username = current_app.config.get('BRIGHT_DATA_USERNAME')
    bright_data_password = current_app.config.get('BRIGHT_DATA_PASSWORD')
    if bright_data_username and bright_data_password:
        return get_bright_data_proxies(bright_data_username, bright_data_password)
    
    # Use manually configured proxies if available
    manual_proxies = current_app.config.get('PROXIES')
    if manual_proxies:
        return manual_proxies
    
    # Return None if no proxies are configured
    return None

def get_firecrawl_proxies(api_key):
    """
    Get proxies from Firecrawl API.
    Args:
        api_key: The Firecrawl API key
    Returns:
        List of proxy configurations
    """
    try:
        response = requests.get(
            'https://api.firecrawl.co/proxies',
            headers={'Authorization': f'Bearer {api_key}'}
        )
        if response.status_code == 200:
            data = response.json()
            proxies = []
            for proxy in data.get('proxies', []):
                proxy_string = f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                proxies.append({'http': proxy_string, 'https': proxy_string})
            return proxies
        else:
            logger.error(f"Failed to get proxies from Firecrawl: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting proxies from Firecrawl: {str(e)}")
        return None

def get_bright_data_proxies(username, password):
    """
    Configure Bright Data proxies.
    Args:
        username: Bright Data username
        password: Bright Data password
    Returns:
        List of proxy configurations
    """
    proxy_list = []
    zones = ['residential', 'datacenter', 'mobile']
    for zone in zones:
        proxy_string = f"http://{username}-zone-{zone}:{password}@brd.superproxy.io:22225"
        proxy_list.append({
            'http': proxy_string,
            'https': proxy_string
        })
    return proxy_list

# Rate limiting
class RateLimiter:
    """
    Rate limiter for domains to prevent being banned.
    """
    def __init__(self):
        self.domains = {}
        self.default_interval = 5  # Default 5-second interval between requests
    
    def add_domain(self, domain, interval=None):
        """
        Add a domain to track with custom interval.
        """
        if domain not in self.domains:
            self.domains[domain] = {
                'last_request': 0,
                'interval': interval or self.default_interval
            }
    
    def wait_if_needed(self, url):
        """
        Wait if needed to respect rate limits.
        """
        domain = urlparse(url).netloc
        if not domain:
            return
        
        # Add domain if it doesn't exist
        if domain not in self.domains:
            self.add_domain(domain)
        
        domain_info = self.domains[domain]
        elapsed = time.time() - domain_info['last_request']
        
        if elapsed < domain_info['interval']:
            wait_time = domain_info['interval'] - elapsed
            logger.info(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
            time.sleep(wait_time)
        
        # Update last request time
        self.domains[domain]['last_request'] = time.time()

# Initialize rate limiter
rate_limiter = RateLimiter()

def scrape_url(url, user_id=None, depth=0, max_depth=1, proxy_enabled=True, custom_headers=None, 
              respect_robots=True, use_cache=True, cache_duration=3600):
    """
    Scrape content from a URL with ban avoidance techniques.
    
    Args:
        url: The URL to scrape
        user_id: User ID for data ownership
        depth: Current recursion depth
        max_depth: Maximum recursion depth for following links
        proxy_enabled: Whether to use proxy rotation
        custom_headers: Custom headers to include
        respect_robots: Whether to respect robots.txt
        use_cache: Whether to use cached results
        cache_duration: How long to keep cached results (seconds)
        
    Returns:
        ScrapedData object with the scraped content
    """
    logger.info(f"Scraping URL: {url}")
    
    # Check cache if enabled
    if use_cache:
        cached_data = ScrapedData.query.filter_by(url=url).first()
        if cached_data and ((time.time() - cached_data.updated_at.timestamp()) < cache_duration):
            logger.info(f"Using cached data for {url}")
            return cached_data
    
    # Respect rate limits
    rate_limiter.wait_if_needed(url)
    
    # Prepare request headers
    headers = DEFAULT_HEADERS.copy()
    headers['User-Agent'] = random.choice(USER_AGENTS)
    
    # Add custom headers if provided
    if custom_headers:
        headers.update(custom_headers)
    
    # Get proxies if enabled
    proxies = get_proxies() if proxy_enabled else None
    
    try:
        # Make the request
        if proxies:
            proxy = random.choice(proxies)
            logger.info(f"Using proxy for {url}")
            response = requests.get(url, headers=headers, proxies=proxy, timeout=30)
        else:
            response = requests.get(url, headers=headers, timeout=30)
        
        # Check if successful
        response.raise_for_status()
        
        # Parse the HTML content
        html_content = response.text
        
        # Create or update ScrapedData
        scraped_data = ScrapedData.query.filter_by(url=url).first()
        if not scraped_data:
            scraped_data = ScrapedData(
                url=url,
                html_content=html_content,
                # Make user_id optional for testing
                user_id=user_id if user_id else None
            )
            db.session.add(scraped_data)
        else:
            scraped_data.html_content = html_content
            scraped_data.updated_at = db.func.current_timestamp()
        
        # Extract and save data
        scraped_data.extract_text()
        scraped_data.extract_links()
        scraped_data.extract_images()
        scraped_data.extract_tables()
        
        # Save to database
        db.session.commit()
        
        # Follow links recursively if depth allows
        if depth < max_depth:
            soup = BeautifulSoup(html_content, 'html.parser')
            for link in soup.find_all('a', href=True):
                if link['href'].startswith('http'):
                    child_url = link['href']
                    try:
                        scrape_url(
                            url=child_url,
                            user_id=user_id,
                            depth=depth+1,
                            max_depth=max_depth,
                            proxy_enabled=proxy_enabled,
                            custom_headers=custom_headers,
                            respect_robots=respect_robots,
                            use_cache=use_cache,
                            cache_duration=cache_duration
                        )
                    except Exception as e:
                        logger.error(f"Error scraping child URL {child_url}: {str(e)}")
        
        return scraped_data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        raise
