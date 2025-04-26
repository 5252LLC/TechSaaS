"""
Mail Service for TechSaaS Platform
Handles email functionality including contact form emails and
notifications to users
"""
from flask import current_app, render_template
from flask_mail import Message
from app import mail
import os

class EmailConfig:
    """Email configuration settings for the application"""
    MAIL_SENDER = os.environ.get('MAIL_SENDER', 'TechSaaS52@proton.me')
    MAIL_ADMIN = os.environ.get('MAIL_ADMIN', 'TechSaaS52@proton.me')
    CONTACT_SUBJECT_PREFIX = '[TechSaaS Contact] '
    NOTIFICATION_SUBJECT_PREFIX = '[TechSaaS] '

def send_email(to, subject, template, **kwargs):
    """
    Sends an email using the Flask-Mail extension
    
    Args:
        to: Recipient email address
        subject: Email subject line
        template: Email template to render (without .html extension)
        **kwargs: Template variables
    """
    app = current_app._get_current_object()
    msg = Message(subject, 
                  sender=EmailConfig.MAIL_SENDER,
                  recipients=[to])
    
    msg.body = render_template(f'{template}.txt', **kwargs)
    msg.html = render_template(f'{template}.html', **kwargs)
    
    mail.send(msg)

def send_contact_email(name, email, subject, message):
    """
    Sends a contact form email to the site admin
    
    Args:
        name: Sender's name
        email: Sender's email address
        subject: Email subject line
        message: Contact message
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        full_subject = f"{EmailConfig.CONTACT_SUBJECT_PREFIX}{subject}"
        
        send_email(
            to=EmailConfig.MAIL_ADMIN,
            subject=full_subject,
            template='mail/contact',
            name=name,
            email=email,
            message=message
        )
        
        # Send confirmation email to the user
        send_email(
            to=email,
            subject="Thank you for contacting TechSaaS",
            template='mail/contact_confirmation',
            name=name
        )
        
        return True
    except Exception as e:
        current_app.logger.error(f"Email sending failed: {str(e)}")
        return False

def send_password_reset_email(user):
    """
    Sends a password reset email to the user
    
    Args:
        user: User object with email and generate_password_reset_token method
    """
    token = user.generate_password_reset_token()
    send_email(
        to=user.email,
        subject='Reset Your Password',
        template='mail/reset_password',
        user=user,
        token=token
    )

def send_account_notification(user, action):
    """
    Sends an account notification email
    
    Args:
        user: User object
        action: Action description (e.g., 'created', 'updated', 'password_changed')
    """
    actions = {
        'created': 'Account Created',
        'updated': 'Profile Updated',
        'password_changed': 'Password Changed',
        'login_detected': 'New Login Detected'
    }
    
    subject = f"{EmailConfig.NOTIFICATION_SUBJECT_PREFIX}{actions.get(action, 'Account Notification')}"
    
    send_email(
        to=user.email,
        subject=subject,
        template=f'mail/notification_{action}',
        user=user
    )

def send_scraper_completion_email(user, scraper_job):
    """
    Sends an email notification when a scraper job is completed
    
    Args:
        user: User object
        scraper_job: Scraper job details
    """
    send_email(
        to=user.email,
        subject=f"{EmailConfig.NOTIFICATION_SUBJECT_PREFIX}Scraping Job Complete",
        template='mail/scraper_complete',
        user=user,
        job=scraper_job
    )
