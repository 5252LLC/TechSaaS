"""
Scraper forms for TechSaaS.
Contains forms for web scraping configuration and options.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, URL, Optional, NumberRange

class ScrapeForm(FlaskForm):
    """Form for configuring a web scraping job."""
    url = StringField('URL to Scrape', validators=[
        DataRequired(),
        URL(message="Please enter a valid URL including http:// or https://")
    ])
    
    proxy_enabled = BooleanField('Use Proxy Rotation', default=True)
    
    max_depth = IntegerField('Maximum Crawl Depth', validators=[
        Optional(),
        NumberRange(min=0, max=3, message="Depth must be between 0 and 3")
    ], default=0)
    
    respect_robots = BooleanField('Respect robots.txt', default=True)
    
    use_cache = BooleanField('Use Cached Results When Available', default=True)
    
    cache_duration = IntegerField('Cache Duration (seconds)', validators=[
        Optional(),
        NumberRange(min=60, max=86400, message="Cache duration must be between 60 seconds and 24 hours")
    ], default=3600)
    
    export_format = SelectField('Export Format', choices=[
        ('none', 'No Export'),
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('xml', 'XML'),
        ('html', 'HTML')
    ], default='none')
    
    submit = SubmitField('Start Scraping')
