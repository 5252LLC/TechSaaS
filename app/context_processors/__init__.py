"""
Flask context processors to inject variables into template context.
These will be available in all templates.
"""
from config.brand import *

def inject_brand():
    """
    Inject brand configuration into all templates.
    Access these in templates with e.g. {{ brand.DOMAIN }}
    
    TEACHING POINT:
    Context processors are a powerful Flask feature that make variables
    available to all templates without having to pass them explicitly
    in each render_template() call. This is perfect for brand information
    that should appear consistently across the entire site.
    """
    return {
        'brand': {
            'DOMAIN': DOMAIN,
            'FULL_URL': FULL_URL,
            'COMPANY_NAME': COMPANY_NAME,
            'COMPANY_TAGLINE': COMPANY_TAGLINE,
            'COMPANY_DESCRIPTION': COMPANY_DESCRIPTION,
            'TWITTER_HANDLE': TWITTER_HANDLE,
            'GITHUB_USERNAME': GITHUB_USERNAME,
            'CONTACT_EMAIL': CONTACT_EMAIL,
            'PRIMARY_COLOR': PRIMARY_COLOR,
            'SECONDARY_COLOR': SECONDARY_COLOR,
            'ACCENT_COLOR': ACCENT_COLOR,
            'TEXT_COLOR': TEXT_COLOR,
            'BACKGROUND_COLOR': BACKGROUND_COLOR,
            'LOGO_PATH': LOGO_PATH,
            'LOGO_WIDTH': LOGO_WIDTH,
            'LOGO_HEIGHT': LOGO_HEIGHT,
            'FAVICON_PATH': FAVICON_PATH,
            'CTA_TEXT': CTA_TEXT,
            'CTA_URL': CTA_URL,
            'FEATURES': FEATURES,
            'EMAIL': ACTIVE_EMAIL  # The currently active email address
        }
    }
