"""
Routes for video extraction functionality.
"""
from flask import render_template, request, jsonify, current_app, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from urllib.parse import urlparse

from app.routes.video import video_bp
from app.services.video_service import VideoExtractor

@video_bp.route('/', methods=['GET'])
def index():
    """Video extraction landing page."""
    return render_template('video/index.html')

@video_bp.route('/extract', methods=['POST'])
def extract():
    """Extract videos from a URL."""
    # Note: CSRF protection is temporarily bypassed for testing purposes
    
    url = request.form.get('url')
    proxy_enabled = request.form.get('proxy_enabled', 'on') == 'on'
    
    if not url:
        flash('URL is required', 'danger')
        return redirect(url_for('video.index'))
    
    try:
        # Use the actual video extractor service
        extractor = VideoExtractor()
        videos = extractor.extract_from_url(url, proxy_enabled=proxy_enabled)
        
        if not videos:
            flash('No videos found on the provided URL', 'warning')
            return render_template('video/results.html', videos=[], url=url)
        
        domain = urlparse(url).netloc
        flash(f'Successfully extracted {len(videos)} videos from {domain}', 'success')
        return render_template('video/results.html', videos=videos, url=url)
    
    except Exception as e:
        current_app.logger.error(f"Error extracting videos: {str(e)}")
        flash(f'Error extracting videos: {str(e)}', 'danger')
        return redirect(url_for('video.index'))

@video_bp.route('/api/extract', methods=['POST'])
@login_required
def api_extract():
    """API endpoint for video extraction."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    url = data.get('url')
    proxy_enabled = data.get('proxy_enabled', True)
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        # Use the video extractor service
        extractor = VideoExtractor()
        videos = extractor.extract_from_url(url, proxy_enabled=proxy_enabled)
        
        return jsonify({
            "status": "success",
            "url": url,
            "count": len(videos),
            "videos": videos
        })
    
    except Exception as e:
        current_app.logger.error(f"API error extracting videos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@video_bp.route('/embed/<path:video_url>', methods=['GET'])
def embed(video_url):
    """Generate an embed code for a video URL."""
    try:
        extractor = VideoExtractor()
        video_id = None
        embed_type = None
        
        # Check if it's a YouTube URL
        youtube_id = extractor._extract_youtube_id(video_url)
        if youtube_id:
            video_id = youtube_id
            embed_type = 'youtube'
        
        # Check if it's a Vimeo URL
        if not video_id:
            vimeo_id = extractor._extract_vimeo_id(video_url)
            if vimeo_id:
                video_id = vimeo_id
                embed_type = 'vimeo'
        
        if not video_id or not embed_type:
            flash('Unsupported video URL', 'danger')
            return redirect(url_for('video.index'))
        
        if embed_type == 'youtube':
            embed_code = extractor._generate_youtube_embed(video_id)
            title = extractor._get_youtube_title(video_id)
        elif embed_type == 'vimeo':
            embed_code = extractor._generate_vimeo_embed(video_id)
            metadata = extractor._get_vimeo_metadata(video_id)
            title = metadata.get('title', '')
        
        return render_template('video/embed.html', 
                              embed_code=embed_code, 
                              title=title, 
                              video_type=embed_type,
                              video_id=video_id,
                              video_url=video_url)
    
    except Exception as e:
        current_app.logger.error(f"Error generating embed: {str(e)}")
        flash(f'Error generating embed: {str(e)}', 'danger')
        return redirect(url_for('video.index'))
