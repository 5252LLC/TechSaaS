"""
Scraper Routes

This module defines the routes for web scraping functionality, one of the
core features of TechSaaS. It includes advanced scraping with ban avoidance.
"""

import json
from datetime import datetime
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SelectField
from wtforms.validators import DataRequired, URL, Optional, NumberRange

from app.routes.scraper import scraper_bp
from app.models.scraped_data import ScrapedData
from app.services.scraper_service import ScraperService
from app.services.eliza_service import ElizaService
from app import db

class ScrapeForm(FlaskForm):
    """
    Form for web scraping configuration.
    
    TEACHING POINT:
    This demonstrates a more complex form with different field types
    and conditional validation based on the scraping mode.
    """
    url = StringField('URL to Scrape', validators=[DataRequired(), URL()])
    mode = SelectField('Scraping Mode', choices=[
        ('single', 'Single Page'),
        ('links', 'Follow Links'),
        ('deep', 'Deep Scrape')
    ], default='single')
    max_depth = IntegerField('Maximum Depth', validators=[Optional(), NumberRange(min=1, max=5)], default=2)
    max_pages = IntegerField('Maximum Pages', validators=[Optional(), NumberRange(min=1, max=50)], default=10)
    extract_images = BooleanField('Extract Images', default=True)
    extract_tables = BooleanField('Extract Tables', default=True)
    detect_crypto = BooleanField('Detect Cryptocurrency Data', default=True)
    ai_summary = BooleanField('Generate AI Summary', default=True)

@scraper_bp.route('/')
def index():
    """
    Render the scraper home page.
    
    TEACHING POINT:
    This is a simple route that renders a template with a form.
    It demonstrates the basic pattern for form handling in Flask.
    """
    form = ScrapeForm()
    return render_template('scraper/index.html', form=form)

@scraper_bp.route('/scrape', methods=['POST'])
@login_required
def scrape():
    """
    Handle scraping requests.
    
    TEACHING POINT:
    This demonstrates how to handle form submission, perform the core
    business logic (scraping), and store results in the database.
    It also shows proper error handling and user feedback.
    """
    form = ScrapeForm()
    
    if not form.validate_on_submit():
        flash('Please correct the errors in the form.', 'danger')
        return render_template('scraper/index.html', form=form)
    
    url = form.url.data
    mode = form.mode.data
    
    # Initialize services
    scraper_service = ScraperService()
    eliza_service = ElizaService(
        ollama_host=current_app.config['OLLAMA_HOST'],
        model=current_app.config['OLLAMA_MODEL']
    )
    
    try:
        # Perform the scraping based on mode
        if mode == 'single':
            result = scraper_service.scrape_url(url)
            
            # Create database record
            scraped_data = ScrapedData(
                url=url,
                title=result.get('title', ''),
                html_content=result.get('html_content', ''),
                status_code=result.get('status_code', 0),
                headers=json.dumps(result.get('headers', {})),
                content_type=result.get('content_type', ''),
                content_length=result.get('content_length', 0),
                data_type='web',
                user_id=current_user.id if current_user.is_authenticated else None
            )
            
            # Generate AI summary if requested
            if form.ai_summary.data and result.get('text_content'):
                summary = eliza_service.generate_summary(result.get('text_content'))
                scraped_data.summary = summary
            
            # Save to database
            db.session.add(scraped_data)
            db.session.commit()
            
            flash('Successfully scraped the URL!', 'success')
            return redirect(url_for('scraper.view_result', id=scraped_data.id))
            
        elif mode == 'links':
            # Scrape with link following
            results = scraper_service.scrape_with_links(
                url, 
                max_pages=form.max_pages.data,
                extract_images=form.extract_images.data,
                extract_tables=form.extract_tables.data
            )
            
            # Store batch ID for grouping related scrapes
            batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Create database records for each result
            for result in results:
                scraped_data = ScrapedData(
                    url=result.get('url', ''),
                    title=result.get('title', ''),
                    html_content=result.get('html_content', ''),
                    status_code=result.get('status_code', 0),
                    headers=json.dumps(result.get('headers', {})),
                    content_type=result.get('content_type', ''),
                    content_length=result.get('content_length', 0),
                    data_type='web',
                    user_id=current_user.id if current_user.is_authenticated else None
                )
                
                # Add to session but don't commit yet
                db.session.add(scraped_data)
            
            # Commit all records at once
            db.session.commit()
            
            flash(f'Successfully scraped {len(results)} pages!', 'success')
            return redirect(url_for('scraper.list'))
            
        elif mode == 'deep':
            # Deep scraping with recursive link following
            results = scraper_service.deep_scrape(
                url,
                max_depth=form.max_depth.data,
                max_pages=form.max_pages.data,
                extract_images=form.extract_images.data,
                extract_tables=form.extract_tables.data,
                detect_crypto=form.detect_crypto.data
            )
            
            # Store batch ID for grouping related scrapes
            batch_id = f"deep_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Create database records for each result
            scraped_ids = []
            for result in results:
                scraped_data = ScrapedData(
                    url=result.get('url', ''),
                    title=result.get('title', ''),
                    html_content=result.get('html_content', ''),
                    status_code=result.get('status_code', 0),
                    headers=json.dumps(result.get('headers', {})),
                    content_type=result.get('content_type', ''),
                    content_length=result.get('content_length', 0),
                    data_type='web',
                    user_id=current_user.id if current_user.is_authenticated else None
                )
                
                # If crypto detection is enabled, check and set type
                if form.detect_crypto.data and scraper_service.is_crypto_data(result.get('text_content', '')):
                    scraped_data.is_crypto_data = True
                    scraped_data.data_type = 'crypto'
                    scraped_data.crypto_data = json.dumps(
                        scraper_service.extract_crypto_data(result.get('html_content', ''))
                    )
                
                # Add to session
                db.session.add(scraped_data)
                db.session.flush()  # Get ID without committing
                scraped_ids.append(scraped_data.id)
            
            # Commit all records at once
            db.session.commit()
            
            flash(f'Successfully deep scraped {len(results)} pages!', 'success')
            return redirect(url_for('scraper.list'))
    
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        current_app.logger.error(f"Scraping error: {str(e)}")
        return render_template('scraper/index.html', form=form)
    
    # Default fallback
    flash('Invalid scraping mode specified.', 'danger')
    return render_template('scraper/index.html', form=form)

@scraper_bp.route('/result/<int:id>')
def view_result(id):
    """
    View the result of a single scrape.
    
    TEACHING POINT:
    This demonstrates retrieving data from the database
    and rendering it in a template, with proper error handling
    for the case when the record doesn't exist.
    """
    scraped_data = ScrapedData.query.get_or_404(id)
    return render_template('scraper/result.html', data=scraped_data)

@scraper_bp.route('/list')
def list():
    """
    List all scraped data.
    
    TEACHING POINT:
    This demonstrates pagination of database results,
    which is important for performance when dealing with
    large datasets.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Filter by data type if provided
    data_type = request.args.get('type')
    
    # Base query
    query = ScrapedData.query
    
    # Apply filters
    if data_type:
        query = query.filter_by(data_type=data_type)
    
    # Apply user filter if authenticated
    if current_user.is_authenticated:
        query = query.filter_by(user_id=current_user.id)
    
    # Order by created_at descending (newest first)
    query = query.order_by(ScrapedData.created_at.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page)
    
    return render_template(
        'scraper/list.html',
        pagination=pagination,
        data_type=data_type
    )

@scraper_bp.route('/export/<int:id>')
@login_required
def export(id):
    """
    Export scraped data in various formats.
    
    TEACHING POINT:
    This demonstrates content negotiation based on the
    requested format, returning different content types
    depending on the 'format' parameter.
    """
    scraped_data = ScrapedData.query.get_or_404(id)
    
    # Check permission
    if current_user.is_authenticated and scraped_data.user_id != current_user.id:
        flash('You do not have permission to export this data.', 'danger')
        return redirect(url_for('scraper.list'))
    
    # Get requested format
    format_type = request.args.get('format', 'json')
    
    # Prepare data dictionary
    data_dict = scraped_data.to_full_dict()
    
    if format_type == 'json':
        return jsonify(data_dict)
    
    elif format_type == 'csv':
        # Flatten the dictionary for CSV
        flat_dict = {}
        for key, value in data_dict.items():
            if isinstance(value, (dict, list)):
                flat_dict[key] = json.dumps(value)
            else:
                flat_dict[key] = value
        
        # Create CSV response
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.DictWriter(output, flat_dict.keys())
        writer.writeheader()
        writer.writerow(flat_dict)
        
        response = current_app.response_class(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=scraped_data_{id}.csv'}
        )
        return response
    
    else:
        flash('Unsupported export format.', 'danger')
        return redirect(url_for('scraper.view_result', id=id))

@scraper_bp.route('/api/scrape', methods=['POST'])
@login_required
def api_scrape():
    """
    API endpoint for scraping.
    
    TEACHING POINT:
    This demonstrates creating a JSON API endpoint that
    accepts POST requests with JSON data and returns JSON responses.
    It shows proper API error handling and status codes.
    """
    # Check for JSON content
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    # Get optional parameters
    mode = data.get('mode', 'single')
    max_depth = data.get('max_depth', 2)
    max_pages = data.get('max_pages', 10)
    
    # Initialize services
    scraper_service = ScraperService()
    
    try:
        # Perform scraping based on mode
        if mode == 'single':
            result = scraper_service.scrape_url(url)
            
            # Create database record
            scraped_data = ScrapedData(
                url=url,
                title=result.get('title', ''),
                html_content=result.get('html_content', ''),
                status_code=result.get('status_code', 0),
                headers=json.dumps(result.get('headers', {})),
                content_type=result.get('content_type', ''),
                content_length=result.get('content_length', 0),
                data_type='web',
                user_id=current_user.id
            )
            
            db.session.add(scraped_data)
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "id": scraped_data.id,
                "data": scraped_data.to_dict()
            })
        
        # Implement other modes similarly
        
    except Exception as e:
        current_app.logger.error(f"API scraping error: {str(e)}")
        return jsonify({"error": str(e)}), 500
