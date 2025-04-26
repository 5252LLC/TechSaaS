"""
Scraped Data Model

This module defines the ScrapedData model for storing and managing web scraped content.
"""

from datetime import datetime
import json
from bs4 import BeautifulSoup
from app import db

class ScrapedData(db.Model):
    """
    ScrapedData model for storing web scraped content.
    
    TEACHING POINT:
    This model demonstrates:
    1. Proper data modeling for web scraping
    2. JSON storage for complex data
    3. Computed properties for derived data
    4. Multiple data type handling (text, images, links)
    """
    __tablename__ = 'scraped_data'
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(512), nullable=False, index=True)
    title = db.Column(db.String(256))
    html_content = db.Column(db.Text)  # Raw HTML content
    text_content = db.Column(db.Text)  # Extracted text content
    
    # Metadata
    status_code = db.Column(db.Integer)
    headers = db.Column(db.Text)  # Stored as JSON
    content_type = db.Column(db.String(128))
    content_length = db.Column(db.Integer)
    
    # Extracted data
    links = db.Column(db.Text)  # Stored as JSON
    images = db.Column(db.Text)  # Stored as JSON
    tables = db.Column(db.Text)  # Stored as JSON
    
    # Data categorization
    data_type = db.Column(db.String(32))  # 'web', 'crypto', 'news', etc.
    is_crypto_data = db.Column(db.Boolean, default=False)
    crypto_data = db.Column(db.Text)  # Structured crypto data as JSON
    
    # AI generated content
    summary = db.Column(db.Text)  # AI summary of content
    insights = db.Column(db.Text)  # AI generated insights
    
    # Timestamps and user association
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    user = db.relationship('User', backref=db.backref('scraped_data', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        """Initialize a new ScrapedData instance with optional extraction"""
        super(ScrapedData, self).__init__(**kwargs)
        if self.html_content and not self.text_content:
            self.extract_text()
        if self.html_content and not self.links:
            self.extract_links()
        if self.html_content and not self.images:
            self.extract_images()
        if self.html_content and not self.tables:
            self.extract_tables()
    
    def extract_text(self):
        """Extract text content from HTML"""
        if not self.html_content:
            return
        
        soup = BeautifulSoup(self.html_content, 'html.parser')
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.extract()
        
        # Get text and clean whitespace
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        self.text_content = '\n'.join(chunk for chunk in chunks if chunk)
    
    def extract_links(self):
        """Extract links from HTML content"""
        if not self.html_content:
            return
        
        soup = BeautifulSoup(self.html_content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            links.append({
                'text': link.get_text().strip(),
                'href': link['href'],
                'title': link.get('title', '')
            })
        
        self.links = json.dumps(links)
    
    def extract_images(self):
        """Extract images from HTML content"""
        if not self.html_content:
            return
        
        soup = BeautifulSoup(self.html_content, 'html.parser')
        images = []
        
        for img in soup.find_all('img', src=True):
            images.append({
                'src': img['src'],
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            })
        
        self.images = json.dumps(images)
    
    def extract_tables(self):
        """Extract tables from HTML content"""
        if not self.html_content:
            return
        
        soup = BeautifulSoup(self.html_content, 'html.parser')
        tables = []
        
        for table_idx, table in enumerate(soup.find_all('table')):
            headers = []
            rows = []
            
            # Extract headers
            for th in table.find_all('th'):
                headers.append(th.get_text().strip())
            
            # Extract rows
            for tr in table.find_all('tr'):
                row = []
                for td in tr.find_all('td'):
                    row.append(td.get_text().strip())
                if row:  # Skip empty rows
                    rows.append(row)
            
            tables.append({
                'id': table_idx,
                'headers': headers,
                'rows': rows
            })
        
        self.tables = json.dumps(tables)
    
    @property
    def links_count(self):
        """Get the number of links in the content"""
        if not self.links:
            return 0
        return len(json.loads(self.links))
    
    @property
    def images_count(self):
        """Get the number of images in the content"""
        if not self.images:
            return 0
        return len(json.loads(self.images))
    
    @property
    def tables_count(self):
        """Get the number of tables in the content"""
        if not self.tables:
            return 0
        return len(json.loads(self.tables))
    
    @property
    def headers_dict(self):
        """Get response headers as a dictionary"""
        if not self.headers:
            return {}
        return json.loads(self.headers)
    
    def to_dict(self):
        """Convert model to dictionary for API responses and exports"""
        base_dict = {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'status_code': self.status_code,
            'content_type': self.content_type,
            'content_length': self.content_length,
            'data_type': self.data_type,
            'links_count': self.links_count,
            'images_count': self.images_count,
            'tables_count': self.tables_count,
            'is_crypto_data': self.is_crypto_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # Include summary if available
        if self.summary:
            base_dict['summary'] = self.summary
        
        # Include insights if available
        if self.insights:
            base_dict['insights'] = self.insights
        
        return base_dict
    
    def to_full_dict(self):
        """Convert model to complete dictionary including all content"""
        full_dict = self.to_dict()
        
        # Add full content
        full_dict['text_content'] = self.text_content
        
        # Add parsed JSON data
        if self.links:
            full_dict['links'] = json.loads(self.links)
        
        if self.images:
            full_dict['images'] = json.loads(self.images)
        
        if self.tables:
            full_dict['tables'] = json.loads(self.tables)
        
        if self.crypto_data:
            full_dict['crypto_data'] = json.loads(self.crypto_data)
        
        return full_dict
    
    def __repr__(self):
        return f'<ScrapedData {self.url}>'
