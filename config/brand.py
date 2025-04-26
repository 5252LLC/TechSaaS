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
CONTACT_EMAIL = "TechSaaS52@proton.me"  # Primary contact email

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
CTA_URL = "/auth/register"

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
# NOTE: Currently using ProtonMail personal account (TechSaaS52@proton.me)
# Future enhancement: Set up custom domain emails when ProtonMail account is upgraded
EMAIL_ADDRESSES = {
    'CONTACT': 'TechSaaS52@proton.me',  # Primary contact email
    'SUPPORT': 'TechSaaS52@proton.me',  # For support requests
    'NOREPLY': 'TechSaaS52@proton.me',  # For automated emails
    'ADMIN': 'TechSaaS52@proton.me',    # For admin notifications
    'PROTONMAIL': 'TechSaaS52@proton.me' # ProtonMail address
}

# Future ProtonMail custom domain configuration
# Will be implemented when ProtonMail is upgraded to support custom domains
PROTONMAIL_ADDRESSES = {
    'CONTACT': 'contact@techsaas.tech',  # Not yet active
    'SUPPORT': 'support@techsaas.tech',  # Not yet active
    'NOREPLY': 'noreply@techsaas.tech',  # Not yet active
    'ADMIN': 'admin@techsaas.tech',      # Not yet active
}

# Which email provider to use (GMAIL, PROTONMAIL, CUSTOM)
EMAIL_PROVIDER = 'PROTONMAIL'

# Email to use based on provider
if EMAIL_PROVIDER == 'GMAIL':
    ACTIVE_EMAIL = EMAIL_ADDRESSES['CONTACT']
elif EMAIL_PROVIDER == 'PROTONMAIL':
    ACTIVE_EMAIL = EMAIL_ADDRESSES['PROTONMAIL']
else:  # CUSTOM
    ACTIVE_EMAIL = EMAIL_ADDRESSES['CONTACT']
