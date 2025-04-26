"""
Authentication routes for TechSaaS.
Handles user registration, login, logout, and profile management.
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from app import db
from app.routes.auth import auth_bp
from app.models.user.user import User
from app.forms.auth import LoginForm, RegistrationForm, ProfileForm

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    # Redirect if user is already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        # Check if user exists and password is correct
        if user and user.verify_password(form.password.data):
            # Update last login time
            user.update_last_login()
            
            # Ensure user is marked as active
            if not user.active:
                user.active = True
                db.session.commit()
                
            # Log in user and remember if requested
            login_user(user, remember=form.remember_me.data)
            
            # Get next page from request args or default to dashboard
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
                
            flash('Login successful', 'success')
            return redirect(next_page)
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    # Redirect if user is already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Check if email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email address already registered', 'danger')
            return render_template('auth/register.html', form=form)
        
        # Check if username already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken', 'danger')
            return render_template('auth/register.html', form=form)
        
        # Create new user - set confirmed=True to allow immediate login
        user = User(
            email=form.email.data,
            username=form.username.data,
            password=form.password.data,
            is_active=True,
            confirmed=True
        )
        
        # Add user to database
        db.session.add(user)
        db.session.commit()
        
        # Log the user in automatically
        login_user(user)
        
        flash('Registration successful! Welcome to TechSaaS!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management route."""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        # Check if username is changed and already exists
        if form.username.data != current_user.username and User.query.filter_by(username=form.username.data).first():
            flash('Username already taken', 'danger')
            return render_template('auth/profile.html', form=form)
        
        # Update user data
        current_user.username = form.username.data
        current_user.full_name = form.full_name.data
        current_user.bio = form.bio.data
        
        # Update password if provided
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
            
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', form=form)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """Password reset request route."""
    # Implement password reset functionality
    return render_template('auth/reset_password_request.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset with token route."""
    # Implement password reset with token
    return render_template('auth/reset_password.html')
