"""
TechSaaS Brand Configuration

This file contains brand-specific configuration that will be used
throughout the application. Update this file with your brand details.
"""

# Domain information
DOMAIN = "TechSaaS.Tech"
FULL_URL = f"https://{DOMAIN}"

# Company information
COMPANY_NAME = "TechSaaS"
COMPANY_TAGLINE = "Advanced Web Scraping & Data Platform"
COMPANY_DESCRIPTION = """
TechSaaS is a professional web scraping, video extraction, and crypto analysis platform
built with Flask and enhanced with AI capabilities via Eliza AI.
"""

# Social media and contact
TWITTER_HANDLE = "@525277x"
GITHUB_USERNAME = "5252LLC" 
CONTACT_EMAIL = "contact@techsaas.tech"

# Brand colors (hex values)
PRIMARY_COLOR = "#4A90E2"  # Blue
SECONDARY_COLOR = "#50E3C2"  # Teal
ACCENT_COLOR = "#F5A623"  # Orange
TEXT_COLOR = "#333333"  # Dark gray
BACKGROUND_COLOR = "#F9F9F9"  # Light gray

# Logo information
LOGO_PATH = "/static/images/techsaas-logo.png"
LOGO_WIDTH = 200
LOGO_HEIGHT = 60
FAVICON_PATH = "/static/images/favicon.ico"

# Call to action
CTA_TEXT = "Start Scraping Now"
CTA_URL = "/register"

# Feature highlights (for landing page)
FEATURES = [
    {
        "title": "Web Scraping",
        "description": "Advanced web scraping with ban avoidance",
        "icon": "fa-spider"
    },
    {
        "title": "Video Extraction",
        "description": "Extract videos from websites easily",
        "icon": "fa-video"
    },
    {
        "title": "Crypto Analysis",
        "description": "Real-time cryptocurrency data analysis",
        "icon": "fa-chart-line"
    },
    {
        "title": "AI Integration",
        "description": "Enhanced with Eliza AI capabilities",
        "icon": "fa-robot"
    }
]

# Email configuration
EMAIL_ADDRESSES = {
    'CONTACT': 'contact@techsaas.tech',  # For contact form
    'SUPPORT': 'support@techsaas.tech',  # For support requests
    'NOREPLY': 'noreply@techsaas.tech',  # For automated emails
    'ADMIN': 'admin@techsaas.tech',      # For admin notifications
    'TEMPORARY': '525277x@gmail.com'     # Temporary email until custom mail server is set up
}

# ProtonMail configuration
PROTONMAIL_ADDRESSES = {
    'CONTACT': 'contact@techsaas.tech',  # For contact form
    'SUPPORT': 'support@techsaas.tech',  # For support requests
    'NOREPLY': 'noreply@techsaas.tech',  # For automated emails
    'ADMIN': 'admin@techsaas.tech',      # For admin notifications
}

# Which email provider to use (GMAIL, PROTONMAIL, CUSTOM)
EMAIL_PROVIDER = 'GMAIL'  # Change to 'PROTONMAIL' after setup

# Email to use based on provider
if EMAIL_PROVIDER == 'GMAIL':
    ACTIVE_EMAIL = EMAIL_ADDRESSES['TEMPORARY']
elif EMAIL_PROVIDER == 'PROTONMAIL':
    ACTIVE_EMAIL = PROTONMAIL_ADDRESSES['CONTACT']
else:  # CUSTOM
    ACTIVE_EMAIL = EMAIL_ADDRESSES['CONTACT']
