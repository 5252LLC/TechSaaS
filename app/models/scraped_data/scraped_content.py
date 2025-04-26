"""
Scraped Content Model

This module defines the ScrapedContent model for storing detailed content extracted
during web scraping operations. It has a many-to-one relationship with ScrapedData.
"""

from datetime import datetime
from app import db

class ScrapedContent(db.Model):
    """
    ScrapedContent model for storing specific content pieces extracted from a web page.
    
    This allows for storing multiple content elements from a single scraping job,
    such as individual articles, products, or other structured data.
    """
    __tablename__ = 'scraped_content'
    
    id = db.Column(db.Integer, primary_key=True)
    scraped_data_id = db.Column(db.Integer, db.ForeignKey('scraped_data.id'), nullable=False)
    
    # Content type and metadata
    content_type = db.Column(db.String(32))  # 'article', 'product', 'image', etc.
    selector_path = db.Column(db.String(256))  # CSS or XPath selector used to extract
    position = db.Column(db.Integer)  # Position in the page
    
    # Content data
    title = db.Column(db.String(256))
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    
    # For media content
    media_url = db.Column(db.String(512))
    media_type = db.Column(db.String(32))  # 'image', 'video', 'audio', etc.
    
    # For structured data
    structured_data = db.Column(db.Text)  # JSON representation of structured data
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scraped_data = db.relationship('ScrapedData', backref=db.backref('content_items', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ScrapedContent {self.id} - {self.content_type}>'
    
    def to_dict(self):
        """
        Convert the content item to a dictionary for API responses
        
        Returns:
            A dictionary representation of the content item
        """
        return {
            'id': self.id,
            'content_type': self.content_type,
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'media_url': self.media_url,
            'media_type': self.media_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def create_from_element(scraped_data_id, element, content_type, selector_path=None, position=None):
        """
        Create a content item from a BeautifulSoup element
        
        Args:
            scraped_data_id: The ID of the parent ScrapedData record
            element: BeautifulSoup element
            content_type: Type of content ('article', 'product', etc.)
            selector_path: CSS or XPath selector used
            position: Position in the document
            
        Returns:
            The newly created ScrapedContent instance
        """
        content_item = ScrapedContent(
            scraped_data_id=scraped_data_id,
            content_type=content_type,
            selector_path=selector_path,
            position=position,
            title=element.get('title', ''),
            content=str(element),
            description=element.get_text()[:500] if hasattr(element, 'get_text') else ''
        )
        
        # Handle media elements
        if element.name == 'img':
            content_item.media_type = 'image'
            content_item.media_url = element.get('src', '')
        elif element.name == 'video':
            content_item.media_type = 'video'
            content_item.media_url = element.get('src', '')
        
        return content_item
