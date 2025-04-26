"""
Authentication forms for TechSaaS.
Contains forms for login, registration, and profile management.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_login import current_user

from app.models.user.user import User

class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')


class RegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8)
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    agree_terms = BooleanField('I agree to the Terms of Service', validators=[
        DataRequired(message='You must agree to the Terms of Service')
    ])
    submit = SubmitField('Register')


class ProfileForm(FlaskForm):
    """User profile form."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64)
    ])
    full_name = StringField('Full Name', validators=[
        Length(max=128)
    ])
    bio = TextAreaField('Bio', validators=[
        Length(max=500)
    ])
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password', validators=[
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Update Profile')

    def validate_current_password(self, field):
        """Validate current password if changing password."""
        if self.new_password.data and not current_user.verify_password(field.data):
            raise ValidationError('Current password is incorrect')


class PasswordResetRequestForm(FlaskForm):
    """Password reset request form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    submit = SubmitField('Request Password Reset')


class PasswordResetForm(FlaskForm):
    """Password reset form."""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8)
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')
