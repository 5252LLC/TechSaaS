"""
Video Extraction Service for TechSaaS

This module provides functionality to extract videos from webpages including:
- Embedded YouTube videos
- Embedded Vimeo videos
- HTML5 video elements
- Other common video platforms
"""
import re
import logging
import json
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

from app.services.scraper_service import scrape_url

# Configure logging
logger = logging.getLogger(__name__)

class VideoExtractor:
    """Service for extracting videos from websites."""
    
    def __init__(self):
        """Initialize the video extractor."""
        # Regex patterns for video detection
        self.youtube_pattern = re.compile(r'(?:https?:)?(?:\/\/)?(?:[0-9A-Z-]+\.)?(?:youtu\.be\/|youtube(?:-nocookie)?\.com\S*?[^\w\s-])([\w-]{11})(?=[^\w-]|$)(?![?=&+%\w.-]*(?:[\'"][^<>]*>|<\/a>))', re.IGNORECASE)
        self.vimeo_pattern = re.compile(r'(?:https?:)?(?:\/\/)?(?:www\.)?vimeo\.com\/(?:channels\/(?:\w+\/)?|groups\/(?:[^\/]*)\/videos\/|album\/(?:\d+)\/video\/|)(\d+)(?:[a-zA-Z0-9_-]+)?', re.IGNORECASE)
        self.html5_video_pattern = re.compile(r'<video[^>]+>.*?<\/video>', re.DOTALL | re.IGNORECASE)
        
    def extract_from_url(self, url, proxy_enabled=True):
        """
        Extract videos from a URL.
        
        Args:
            url: URL to extract videos from
            proxy_enabled: Whether to use proxy rotation
            
        Returns:
            List of extracted videos with metadata
        """
        try:
            # Use the scraper service to get HTML content
            scraped_data = scrape_url(url, proxy_enabled=proxy_enabled)
            
            if not scraped_data or not scraped_data.html_content:
                logger.error(f"Failed to retrieve content from {url}")
                return []
            
            # For news sites like CNN, look for specific patterns
            is_news_site = any(site in url for site in ['cnn.com', 'bbc.com', 'nytimes.com', 'reuters.com', 'washingtonpost.com'])
            
            # Extract videos from HTML content
            videos = self.extract_from_html(scraped_data.html_content, base_url=url)
            
            # For news sites, apply additional extraction methods if no videos found
            if is_news_site and not videos:
                news_videos = self._extract_news_site_videos(scraped_data.html_content, url)
                videos.extend(news_videos)
            
            return videos
            
        except Exception as e:
            logger.error(f"Error extracting videos from {url}: {str(e)}")
            return []
    
    def extract_from_html(self, html_content, base_url=None):
        """
        Extract videos from HTML content.
        
        Args:
            html_content: HTML content to extract videos from
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of extracted videos with metadata
        """
        videos = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract videos
        youtube_videos = self._extract_youtube_videos(soup, base_url)
        vimeo_videos = self._extract_vimeo_videos(soup, base_url)
        html5_videos = self._extract_html5_videos(soup, base_url)
        iframe_videos = self._extract_iframe_videos(soup, base_url)
        
        # Combine all videos
        videos.extend(youtube_videos)
        videos.extend(vimeo_videos)
        videos.extend(html5_videos)
        videos.extend(iframe_videos)
        
        # Remove duplicates
        unique_videos = []
        urls = set()
        
        for video in videos:
            if video.get('embed_url') not in urls and video.get('source_url') not in urls:
                urls.add(video.get('embed_url', ''))
                urls.add(video.get('source_url', ''))
                unique_videos.append(video)
        
        return unique_videos
    
    def _extract_youtube_videos(self, soup, base_url=None):
        """Extract YouTube videos from BeautifulSoup object."""
        videos = []
        
        # Find all iframes
        iframes = soup.find_all('iframe', src=True)
        for iframe in iframes:
            src = iframe['src']
            
            # Check if it's a YouTube video
            if 'youtube' in src or 'youtu.be' in src:
                video_id = self._extract_youtube_id(src)
                if video_id:
                    videos.append({
                        'type': 'youtube',
                        'video_id': video_id,
                        'source_url': base_url,
                        'embed_url': src,
                        'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                        'embed_code': self._generate_youtube_embed(video_id),
                        'title': self._get_youtube_title(video_id)
                    })
        
        # Find YouTube links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'youtube' in href or 'youtu.be' in href:
                video_id = self._extract_youtube_id(href)
                if video_id:
                    videos.append({
                        'type': 'youtube',
                        'video_id': video_id,
                        'source_url': base_url,
                        'embed_url': href,
                        'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                        'embed_code': self._generate_youtube_embed(video_id),
                        'title': self._get_youtube_title(video_id)
                    })
        
        return videos
    
    def _extract_vimeo_videos(self, soup, base_url=None):
        """Extract Vimeo videos from BeautifulSoup object."""
        videos = []
        
        # Find all iframes
        iframes = soup.find_all('iframe', src=True)
        for iframe in iframes:
            src = iframe['src']
            
            # Check if it's a Vimeo video
            if 'vimeo' in src:
                video_id = self._extract_vimeo_id(src)
                if video_id:
                    metadata = self._get_vimeo_metadata(video_id)
                    videos.append({
                        'type': 'vimeo',
                        'video_id': video_id,
                        'source_url': base_url,
                        'embed_url': src,
                        'thumbnail': metadata.get('thumbnail', ''),
                        'embed_code': self._generate_vimeo_embed(video_id),
                        'title': metadata.get('title', '')
                    })
        
        # Find Vimeo links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'vimeo' in href:
                video_id = self._extract_vimeo_id(href)
                if video_id:
                    metadata = self._get_vimeo_metadata(video_id)
                    videos.append({
                        'type': 'vimeo',
                        'video_id': video_id,
                        'source_url': base_url,
                        'embed_url': href,
                        'thumbnail': metadata.get('thumbnail', ''),
                        'embed_code': self._generate_vimeo_embed(video_id),
                        'title': metadata.get('title', '')
                    })
        
        return videos
    
    def _extract_html5_videos(self, soup, base_url=None):
        """Extract HTML5 videos from BeautifulSoup object."""
        videos = []
        
        # Find all video elements
        video_elements = soup.find_all('video')
        for video in video_elements:
            # Get video sources
            sources = []
            for source in video.find_all('source', src=True):
                src = source['src']
                # Handle relative URLs
                if base_url and not src.startswith(('http://', 'https://')):
                    src = self._resolve_relative_url(base_url, src)
                
                sources.append({
                    'src': src,
                    'type': source.get('type', '')
                })
            
            # If no source elements but video has src attribute
            if not sources and video.has_attr('src'):
                src = video['src']
                # Handle relative URLs
                if base_url and not src.startswith(('http://', 'https://')):
                    src = self._resolve_relative_url(base_url, src)
                
                sources.append({
                    'src': src,
                    'type': video.get('type', '')
                })
            
            if sources:
                videos.append({
                    'type': 'html5',
                    'sources': sources,
                    'source_url': base_url,
                    'embed_url': sources[0]['src'],
                    'poster': video.get('poster', ''),
                    'controls': video.has_attr('controls'),
                    'autoplay': video.has_attr('autoplay'),
                    'loop': video.has_attr('loop'),
                    'muted': video.has_attr('muted'),
                    'width': video.get('width', ''),
                    'height': video.get('height', ''),
                    'title': video.get('title', '') or video.get('alt', '')
                })
        
        return videos
    
    def _extract_iframe_videos(self, soup, base_url=None):
        """Extract other iframe-based videos from BeautifulSoup object."""
        videos = []
        
        # Find all iframes that might be videos but aren't from YouTube or Vimeo
        iframes = soup.find_all('iframe', src=True)
        for iframe in iframes:
            src = iframe['src']
            
            # Skip YouTube and Vimeo as they're handled separately
            if 'youtube' in src or 'youtu.be' in src or 'vimeo' in src:
                continue
            
            # Check if it's a video embed based on common patterns
            if any(provider in src for provider in ['dailymotion', 'twitch', 'facebook.com/plugins/video', 
                                                   'player.', '.mp4', 'brightcove', 'jwplayer', 
                                                   'cdn.cnn.com', 'video/playout', 'video-api',
                                                   'video.', 'player.', 'embed']):
                videos.append({
                    'type': 'iframe',
                    'source_url': base_url,
                    'embed_url': src,
                    'width': iframe.get('width', ''),
                    'height': iframe.get('height', ''),
                    'title': iframe.get('title', ''),
                    'embed_code': self._generate_iframe_embed(src, iframe.get('width', ''), iframe.get('height', ''))
                })
        
        return videos
    
    def _extract_news_site_videos(self, html_content, base_url):
        """Extract videos from news sites like CNN that use data attributes."""
        videos = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for CNN specific patterns
        for div in soup.find_all(['div', 'section', 'article']):
            # Check for data attributes that might indicate videos
            if div.has_attr('data-video-id') or div.has_attr('data-player-id') or div.has_attr('data-video') or div.has_attr('data-media-id'):
                video_id = div.get('data-video-id', div.get('data-player-id', div.get('data-video', div.get('data-media-id', ''))))
                if video_id:
                    # For CNN videos
                    if 'cnn.com' in base_url:
                        videos.append({
                            'type': 'cnn',
                            'video_id': video_id,
                            'source_url': base_url,
                            'embed_url': f"https://www.cnn.com/videos/{video_id}",
                            'title': div.get('data-video-title', 'CNN Video'),
                            'embed_code': f'<div class="cnn-video" data-video-id="{video_id}">CNN Video Embed</div>'
                        })
                    else:
                        # Generic data-attribute video
                        videos.append({
                            'type': 'data-video',
                            'video_id': video_id,
                            'source_url': base_url,
                            'embed_url': base_url,
                            'title': div.get('data-title', 'Video Content'),
                            'embed_code': f'<div class="embedded-video" data-video-id="{video_id}">Video Embed</div>'
                        })
        
        # Look for script tags with video JSON data (common in news sites)
        for script in soup.find_all('script', type='application/json'):
            try:
                json_content = json.loads(script.string)
                # Check if json contains video data
                if isinstance(json_content, dict) and ('video' in str(json_content).lower() or 'media' in str(json_content).lower()):
                    # Extract video information from JSON
                    video_data = self._extract_video_from_json(json_content)
                    if video_data and 'src' in video_data:
                        videos.append({
                            'type': 'json-embedded',
                            'video_id': video_data.get('id', 'unknown'),
                            'source_url': base_url,
                            'embed_url': video_data.get('src', ''),
                            'title': video_data.get('title', 'Embedded Video'),
                            'thumbnail': video_data.get('thumbnail', ''),
                            'embed_code': f'<iframe src="{video_data.get("src", "")}" width="100%" height="400" frameborder="0" allowfullscreen></iframe>'
                        })
            except (json.JSONDecodeError, AttributeError):
                pass
                
        return videos
        
    def _extract_video_from_json(self, json_data):
        """Recursively extract video data from JSON structures."""
        if isinstance(json_data, dict):
            # Check if this is a video object
            if 'video' in json_data and isinstance(json_data['video'], dict):
                video = json_data['video']
                return {
                    'id': video.get('id', ''),
                    'src': video.get('src', video.get('url', '')),
                    'title': video.get('title', ''),
                    'thumbnail': video.get('thumbnail', video.get('poster', ''))
                }
            
            # Check for mp4Sources or other video indicators
            if 'mp4Sources' in json_data or 'videoSrc' in json_data or 'videoUrl' in json_data:
                return {
                    'id': json_data.get('id', ''),
                    'src': json_data.get('videoSrc', json_data.get('videoUrl', json_data.get('mp4Sources', [''])[0])),
                    'title': json_data.get('title', json_data.get('headline', '')),
                    'thumbnail': json_data.get('thumbnail', json_data.get('poster', ''))
                }
                
            # Recursively check all properties
            for key, value in json_data.items():
                result = self._extract_video_from_json(value)
                if result:
                    return result
                    
        elif isinstance(json_data, list):
            # Check each item in the list
            for item in json_data:
                result = self._extract_video_from_json(item)
                if result:
                    return result
                    
        return None
    
    def _extract_youtube_id(self, url):
        """Extract YouTube video ID from URL."""
        match = self.youtube_pattern.search(url)
        if match:
            return match.group(1)
        
        # Try parsing the URL for v parameter
        parsed_url = urlparse(url)
        if 'youtube.com' in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            if 'v' in query_params:
                return query_params['v'][0]
        
        return None
    
    def _extract_vimeo_id(self, url):
        """Extract Vimeo video ID from URL."""
        match = self.vimeo_pattern.search(url)
        if match:
            return match.group(1)
        return None
    
    def _get_youtube_title(self, video_id):
        """Get YouTube video title using oEmbed."""
        try:
            response = requests.get(f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json')
            if response.status_code == 200:
                data = response.json()
                return data.get('title', '')
        except Exception as e:
            logger.error(f"Error getting YouTube title: {str(e)}")
        return ''
    
    def _get_vimeo_metadata(self, video_id):
        """Get Vimeo video metadata using oEmbed."""
        try:
            response = requests.get(f'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{video_id}')
            if response.status_code == 200:
                data = response.json()
                return {
                    'title': data.get('title', ''),
                    'thumbnail': data.get('thumbnail_url', ''),
                    'author': data.get('author_name', '')
                }
        except Exception as e:
            logger.error(f"Error getting Vimeo metadata: {str(e)}")
        return {}
    
    def _generate_youtube_embed(self, video_id, width=560, height=315):
        """Generate YouTube embed code."""
        return f'<iframe width="{width}" height="{height}" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
    
    def _generate_vimeo_embed(self, video_id, width=640, height=360):
        """Generate Vimeo embed code."""
        return f'<iframe src="https://player.vimeo.com/video/{video_id}" width="{width}" height="{height}" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>'
    
    def _generate_iframe_embed(self, src, width=640, height=360):
        """Generate generic iframe embed code."""
        width = width or 640
        height = height or 360
        return f'<iframe src="{src}" width="{width}" height="{height}" frameborder="0" allowfullscreen></iframe>'
    
    def _resolve_relative_url(self, base_url, relative_url):
        """Resolve a relative URL against a base URL."""
        parsed_base = urlparse(base_url)
        if relative_url.startswith('/'):
            # Absolute path
            return f"{parsed_base.scheme}://{parsed_base.netloc}{relative_url}"
        else:
            # Relative path
            path = parsed_base.path
            if not path.endswith('/'):
                path = path[:path.rfind('/')+1]
            return f"{parsed_base.scheme}://{parsed_base.netloc}{path}{relative_url}"
