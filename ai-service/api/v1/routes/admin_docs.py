"""
Admin Documentation Endpoints
Provides secure access to admin-only documentation
"""

import os
import logging
from flask import jsonify, send_file, current_app
from flask_smorest import Blueprint, abort
import markdown

from api.v1.middleware import require_admin

# Create blueprint for admin documentation
admin_docs_blueprint = Blueprint(
    'admin_docs', 
    'admin_docs_endpoints',
    description='Secure admin documentation access'
)

# Set up logger
logger = logging.getLogger(__name__)

@admin_docs_blueprint.route('/', methods=['GET'])
@require_admin
def admin_docs_index():
    """Return the admin documentation index"""
    try:
        # Path to admin docs
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                                os.path.dirname(__file__))))), 'docs', 'admin')
        
        # Read README.md content
        readme_path = os.path.join(base_path, 'README.md')
        if not os.path.exists(readme_path):
            return jsonify({
                "error": "Admin documentation not found",
                "status": "not_found"
            }), 404
        
        with open(readme_path, 'r') as f:
            content = f.read()
        
        # Convert markdown to HTML for display
        html_content = markdown.markdown(content)
        
        # List all available documentation files
        doc_files = []
        if os.path.exists(base_path):
            for file in os.listdir(base_path):
                if file.endswith('.md'):
                    doc_files.append({
                        "name": file,
                        "path": f"/api/v1/admin-docs/file/{file}",
                        "title": file.replace('.md', '').replace('_', ' ').title()
                    })
        
        return jsonify({
            "title": "Admin Documentation",
            "html_content": html_content,
            "markdown_content": content,
            "available_docs": doc_files,
            "message": "This documentation is restricted to admin users only"
        })
    except Exception as e:
        logger.exception(f"Error retrieving admin documentation: {str(e)}")
        abort(500, message=str(e))

@admin_docs_blueprint.route('/file/<path:doc_name>', methods=['GET'])
@require_admin
def admin_docs_file(doc_name):
    """Return a specific admin documentation file"""
    try:
        # Security: Prevent directory traversal
        doc_name = os.path.basename(doc_name)
        
        # Path to admin docs
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                                os.path.dirname(__file__))))), 'docs', 'admin')
        
        doc_path = os.path.join(base_path, doc_name)
        
        # Verify the file exists and is within the admin docs directory
        if not os.path.exists(doc_path) or not os.path.normpath(doc_path).startswith(os.path.normpath(base_path)):
            return jsonify({
                "error": "Documentation file not found or access denied",
                "status": "not_found"
            }), 404
        
        # For Markdown files, return processed content
        if doc_name.endswith('.md'):
            with open(doc_path, 'r') as f:
                content = f.read()
            
            # Convert markdown to HTML
            html_content = markdown.markdown(content)
            
            return jsonify({
                "title": doc_name.replace('.md', '').replace('_', ' ').title(),
                "filename": doc_name,
                "html_content": html_content,
                "markdown_content": content
            })
        
        # For other file types (images, PDFs, etc.), return the file directly
        return send_file(doc_path)
    
    except Exception as e:
        logger.exception(f"Error retrieving admin documentation file {doc_name}: {str(e)}")
        abort(500, message=str(e))
