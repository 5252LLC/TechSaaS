"""
Scraper Routes

This module defines the routes for web scraping functionality, one of the
core features of TechSaaS. It includes advanced scraping with ban avoidance.
"""

import os
import json
import csv
import io
from flask import render_template, request, jsonify, current_app, flash, redirect, url_for, send_file, Response
from flask_login import login_required, current_user
from urllib.parse import urlparse

from app import db
from app.routes.scraper import scraper_bp
from app.forms.scraper import ScrapeForm
from app.services.scraper_service import scrape_url
from app.models.scraped_data.scraped_data import ScrapedData

@scraper_bp.route('/', methods=['GET'])
def index():
    """Web scraper landing page."""
    form = ScrapeForm()
    return render_template('scraper/index.html', form=form)

@scraper_bp.route('/scrape', methods=['POST'])
# Temporarily commented out to allow testing without login
# @login_required
def scrape():
    """Process scraping request and store results."""
    form = ScrapeForm()
    
    if form.validate_on_submit():
        url = form.url.data
        
        try:
            # Get user_id safely (handle anonymous users for testing)
            user_id = None
            if hasattr(current_user, 'id'):
                user_id = current_user.id
            
            # Call scraping service with form options
            scraped_data = scrape_url(
                url=url,
                user_id=user_id,  # Use None for anonymous users
                depth=form.max_depth.data,
                max_depth=form.max_depth.data,
                proxy_enabled=form.proxy_enabled.data,
                respect_robots=form.respect_robots.data,
                use_cache=form.use_cache.data,
                cache_duration=form.cache_duration.data
            )
            
            # Flash success message
            domain = urlparse(url).netloc
            flash(f'Successfully scraped {domain}', 'success')
            
            # Redirect to results page
            return redirect(url_for('scraper.results', id=scraped_data.id))
        
        except Exception as e:
            flash(f'Error scraping URL: {str(e)}', 'danger')
            return render_template('scraper/index.html', form=form)
    
    # If form validation fails
    return render_template('scraper/index.html', form=form)

@scraper_bp.route('/results/<int:id>', methods=['GET'])
# Temporarily commented out to allow testing without login
# @login_required
def results(id):
    """Display scraping results."""
    # Get scraped data by ID
    scraped_data = ScrapedData.query.get_or_404(id)
    
    # Temporarily disabled access check for testing
    # if hasattr(current_user, 'id') and scraped_data.user_id and scraped_data.user_id != current_user.id:
    #     flash('You do not have permission to view this data', 'danger')
    #     return redirect(url_for('scraper.index'))
    
    return render_template('scraper/results.html', data=scraped_data)

@scraper_bp.route('/history', methods=['GET'])
# Temporarily commented out to allow testing without login
# @login_required
def history():
    """Show user's scraping history."""
    # Get all scraped data for the current user
    # Temporarily allowing all scraped data for testing
    scraped_data = ScrapedData.query.order_by(ScrapedData.created_at.desc()).all()
    
    return render_template('scraper/history.html', data_list=scraped_data)

@scraper_bp.route('/export/<int:id>/<format>', methods=['GET'])
# Temporarily commented out to allow testing without login
# @login_required
def export(id, format):
    """Export scraped data in specified format."""
    # Get scraped data by ID
    scraped_data = ScrapedData.query.get_or_404(id)
    
    # Check if user has access to this data
    # Temporarily disabled access check for testing
    # if scraped_data.user_id and scraped_data.user_id != current_user.id:
    #     flash('You do not have permission to export this data', 'danger')
    #     return redirect(url_for('scraper.index'))
    
    # Get domain for filename
    domain = urlparse(scraped_data.url).netloc
    filename = f"{domain.replace('.', '_')}_{scraped_data.id}"
    
    # Export based on format
    if format == 'json':
        # Create JSON export
        data = {
            'url': scraped_data.url,
            'title': scraped_data.title,
            'text': scraped_data.text_content,
            'links': scraped_data.links,
            'images': scraped_data.images,
            'tables': scraped_data.tables,
            'scraped_at': scraped_data.created_at.isoformat(),
        }
        return jsonify(data)
    
    elif format == 'csv':
        # Create CSV export
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Type', 'Content', 'URL'])
        
        # Write text content (limit to avoid excessive size)
        truncated_text = scraped_data.text_content[:1000] + '...' if len(scraped_data.text_content) > 1000 else scraped_data.text_content
        writer.writerow(['Text', truncated_text, scraped_data.url])
        
        # Write links
        for link in scraped_data.links:
            if isinstance(link, dict):
                writer.writerow(['Link', link.get('text', ''), link.get('href', '')])
            elif isinstance(link, str):
                writer.writerow(['Link', '', link])
        
        # Write images
        for image in scraped_data.images:
            if isinstance(image, dict):
                writer.writerow(['Image', image.get('alt', ''), image.get('src', '')])
            elif isinstance(image, str):
                writer.writerow(['Image', '', image])
            
        # Add table data as separate rows
        for i, table in enumerate(scraped_data.tables):
            if not isinstance(table, dict):
                continue
                
            headers = table.get('headers', [])
            rows = table.get('rows', [])
            
            # Write table headers
            if headers:
                writer.writerow(['Table_Header', f'Table {i+1}', ','.join(headers)])
                
            # Write table rows
            for row in rows:
                writer.writerow(['Table_Row', f'Table {i+1}', ','.join(row)])
        
        # Prepare response
        output.seek(0)
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}.csv"}
        )
    
    elif format == 'html':
        # Create HTML export
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Scraped Data from {domain}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }}
                h1, h2 {{ color: #4A90E2; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                img {{ max-width: 100%; height: auto; }}
                pre {{ background-color: #f5f5f5; padding: 10px; overflow-x: auto; }}
                a {{ color: #4A90E2; }}
                @media (max-width: 768px) {{
                    table {{ display: block; overflow-x: auto; }}
                }}
            </style>
        </head>
        <body>
            <h1>Scraped Data from {domain}</h1>
            <p><strong>URL:</strong> <a href="{scraped_data.url}" target="_blank">{scraped_data.url}</a></p>
            <p><strong>Scraped at:</strong> {scraped_data.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Content</h2>
            <pre>{scraped_data.text_content}</pre>
            
            <h2>Links</h2>
            <table>
                <tr><th>Text</th><th>URL</th></tr>
                {"".join(f"<tr><td>{link.get('text', '')}</td><td><a href='{link.get('href', '')}' target='_blank'>{link.get('href', '')}</a></td></tr>" for link in scraped_data.links[:100] if isinstance(link, dict))}
                {f"<tr><td colspan='2'>... {len(scraped_data.links) - 100} more links</td></tr>" if len(scraped_data.links) > 100 else ""}
            </table>
            
            <h2>Images</h2>
            <div>
                {"".join(f"<div style='margin-bottom: 20px;'><img src='{image.get('src', '')}' alt='{image.get('alt', '')}' onerror=\"this.onerror=null; this.src='/static/images/image-placeholder.svg'; this.style.maxWidth='200px';\"><p>{image.get('alt', '')}</p></div>" for image in scraped_data.images[:20] if isinstance(image, dict))}
                {f"<p>... {len(scraped_data.images) - 20} more images</p>" if len(scraped_data.images) > 20 else ""}
            </div>
            
            <h2>Tables</h2>
            <div>
                {"".join(
                    f'''
                    <div style="margin-bottom: 30px;">
                        <h3>Table {i+1}</h3>
                        <table>
                            {f"<tr>{''.join(f'<th>{header}</th>' for header in table.get('headers', []))}</tr>" if table.get('headers') and isinstance(table, dict) else ""}
                            {"".join(f"<tr>{''.join(f'<td>{cell}</td>' for cell in row)}</tr>" for row in table.get('rows', []) if isinstance(table, dict))}
                        </table>
                    </div>
                    '''
                    for i, table in enumerate(scraped_data.tables[:10]) if isinstance(table, dict)
                )}
                {f"<p>... {len(scraped_data.tables) - 10} more tables</p>" if len(scraped_data.tables) > 10 else ""}
            </div>
        </body>
        </html>
        """
        return Response(
            html,
            mimetype="text/html",
            headers={"Content-Disposition": f"attachment;filename={filename}.html"}
        )
    
    else:
        flash(f'Unsupported export format: {format}', 'danger')
        return redirect(url_for('scraper.results', id=id))
