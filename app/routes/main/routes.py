"""
Main Routes

This module defines the main routes for the TechSaaS application.
These include the home page, about page, contact page, and other general routes.
"""

from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, EmailField
from wtforms.validators import DataRequired, Email, Length

from app.routes.main import main_bp
from app.services.mail_service import send_contact_email

class ContactForm(FlaskForm):
    """
    Form for the contact page.
    
    TEACHING POINT:
    This demonstrates proper form validation using WTForms,
    with appropriate validators for each field type.
    """
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=2, max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])

@main_bp.route('/')
def home():
    """
    Render the home page.
    
    TEACHING POINT:
    The home page uses the base template and passes minimal context.
    Most of the branding is handled by the context processor.
    """
    return render_template('index.html')

@main_bp.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """
    Render the contact page and handle form submission.
    
    TEACHING POINT:
    This route demonstrates handling both GET and POST requests
    in the same function, with proper form validation.
    """
    form = ContactForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        # Send email
        send_result = send_contact_email(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data
        )
        
        if send_result:
            flash('Your message has been sent! We will get back to you soon.', 'success')
            return redirect(url_for('main.contact'))
        else:
            flash('There was an error sending your message. Please try again later.', 'danger')
    
    return render_template('contact.html', form=form)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Render the user dashboard.
    
    TEACHING POINT:
    This route is protected with @login_required decorator,
    ensuring only authenticated users can access it.
    """
    return render_template('dashboard.html')

@main_bp.route('/privacy')
def privacy():
    """Render the privacy policy page."""
    return render_template('privacy.html')

@main_bp.route('/terms')
def terms():
    """Render the terms of service page."""
    return render_template('terms.html')

@main_bp.route('/test-eliza')
def test_eliza():
    """
    Test the Eliza AI connection.
    
    TEACHING POINT:
    This demonstrates connecting to an external API (Eliza)
    and returning the result to the template.
    """
    from app.services.eliza_service import ElizaService
    
    eliza = ElizaService(
        ollama_host=current_app.config['OLLAMA_HOST'],
        model=current_app.config['OLLAMA_MODEL']
    )
    
    response = eliza.generate_text("Hello, I'm testing the connection to Eliza. Are you working properly?")
    
    return render_template('test_eliza.html', response=response)
