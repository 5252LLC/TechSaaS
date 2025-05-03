"""
Request Validation Middleware

This module provides middleware for validating incoming API requests,
including schema validation, content type validation, and input sanitization.
"""

import logging
import functools
import json
from typing import Dict, List, Any, Optional, Union, Callable
from flask import request, jsonify, g, current_app, Request
from marshmallow import Schema, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

logger = logging.getLogger(__name__)

def validate_json(f):
    """
    Decorator to validate that the request contains valid JSON data
    
    Args:
        f: The view function to decorate
        
    Returns:
        The decorated function
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip validation for GET requests which typically don't have a body
        if request.method == "GET":
            return f(*args, **kwargs)
            
        # Validate Content-Type header
        if not request.is_json:
            logger.warning(f"Request to {request.path} has invalid Content-Type: {request.content_type}")
            return jsonify({
                "error": "Invalid Content-Type",
                "message": "Content-Type must be application/json",
                "status_code": 415
            }), 415
            
        # Validate that body contains valid JSON
        try:
            # Force the request to be parsed as JSON
            _ = request.get_json(force=False)
        except BadRequest as e:
            logger.warning(f"Invalid JSON in request to {request.path}: {str(e)}")
            return jsonify({
                "error": "Invalid JSON",
                "message": "Request body contains invalid JSON",
                "status_code": 400
            }), 400
            
        return f(*args, **kwargs)
        
    return decorated_function

def validate_schema(schema_class):
    """
    Decorator to validate request data against a marshmallow schema
    
    Args:
        schema_class: A marshmallow Schema class
        
    Returns:
        The decorator function
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip validation for GET requests which typically use query params instead
            if request.method == "GET":
                schema = schema_class()
                try:
                    # For GET requests, validate query parameters
                    errors = {}
                    for field_name, field_obj in schema.fields.items():
                        if field_name in request.args:
                            try:
                                field_obj.deserialize(request.args.get(field_name))
                            except ValidationError as e:
                                errors[field_name] = e.messages
                    
                    if errors:
                        logger.warning(f"Query param validation failed for {request.path}: {errors}")
                        return jsonify({
                            "error": "Validation Error",
                            "message": "Invalid query parameters",
                            "details": errors,
                            "status_code": 400
                        }), 400
                        
                    # Add validated data to the Flask global context
                    g.validated_args = request.args.to_dict()
                    return f(*args, **kwargs)
                except Exception as e:
                    logger.exception(f"Unexpected error in schema validation: {str(e)}")
                    return jsonify({
                        "error": "Validation Error",
                        "message": str(e),
                        "status_code": 400
                    }), 400
                
            # For other methods, validate the JSON body
            schema = schema_class()
            try:
                # Get JSON data
                json_data = request.get_json()
                
                # Validate against schema
                validated_data = schema.load(json_data)
                
                # Add validated data to the Flask global context
                g.validated_data = validated_data
            except ValidationError as err:
                logger.warning(f"Schema validation failed for {request.path}: {err.messages}")
                return jsonify({
                    "error": "Validation Error",
                    "message": "Invalid request data",
                    "details": err.messages,
                    "status_code": 400
                }), 400
            except Exception as e:
                logger.exception(f"Unexpected error in schema validation: {str(e)}")
                return jsonify({
                    "error": "Validation Error",
                    "message": str(e),
                    "status_code": 400
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def validate_content_type(allowed_types=None):
    """
    Decorator to validate the Content-Type header of the request
    
    Args:
        allowed_types: A list of allowed content types. 
                      Default is ["application/json"]
        
    Returns:
        The decorator function
    """
    if allowed_types is None:
        allowed_types = ["application/json"]
        
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip validation for GET requests
            if request.method == "GET":
                return f(*args, **kwargs)
                
            # Check if Content-Type header is present and is one of the allowed types
            content_type = request.headers.get("Content-Type", "")
            
            # Handle Content-Type with charset
            base_content_type = content_type.split(";")[0].strip()
            
            if base_content_type not in allowed_types:
                logger.warning(f"Invalid Content-Type ({content_type}) for {request.path}")
                return jsonify({
                    "error": "Unsupported Media Type",
                    "message": f"Content-Type must be one of: {', '.join(allowed_types)}",
                    "status_code": 415
                }), 415
                
            return f(*args, **kwargs)
            
        return decorated_function
        
    return decorator

def sanitize_input(sanitize_functions=None):
    """
    Decorator to sanitize input data for security purposes
    
    Args:
        sanitize_functions: A list of functions that take and return a dict
                          to sanitize the input data
                          
    Returns:
        The decorator function
    """
    if sanitize_functions is None:
        sanitize_functions = []
        
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == "GET":
                # Sanitize query parameters for GET requests
                sanitized_args = request.args.to_dict()
                for sanitize_func in sanitize_functions:
                    sanitized_args = sanitize_func(sanitized_args)
                g.sanitized_args = sanitized_args
            else:
                # Sanitize JSON body for other requests
                try:
                    json_data = request.get_json(silent=True) or {}
                    sanitized_data = json_data
                    
                    for sanitize_func in sanitize_functions:
                        sanitized_data = sanitize_func(sanitized_data)
                        
                    g.sanitized_data = sanitized_data
                except Exception as e:
                    logger.exception(f"Error sanitizing input: {str(e)}")
                    # Continue anyway but log the error
            
            return f(*args, **kwargs)
            
        return decorated_function
        
    return decorator

# Common sanitization functions
def remove_script_tags(data):
    """
    Remove potential script tags from string values in a dict
    
    Args:
        data: Dictionary with input data
        
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
        
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Remove script tags
            import re
            result[key] = re.sub(r'<script.*?>.*?</script>', '', value, flags=re.DOTALL)
        elif isinstance(value, dict):
            result[key] = remove_script_tags(value)
        elif isinstance(value, list):
            result[key] = [
                remove_script_tags(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result

def limit_input_size(data, max_size=10240):
    """
    Limit the size of input strings to prevent DoS attacks
    
    Args:
        data: Dictionary with input data
        max_size: Maximum size for string values in bytes
        
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
        
    result = {}
    for key, value in data.items():
        if isinstance(value, str) and len(value.encode('utf-8')) > max_size:
            # Truncate string to max size
            result[key] = value[:max_size]
            logger.warning(f"Input data for field {key} truncated to {max_size} bytes")
        elif isinstance(value, dict):
            result[key] = limit_input_size(value, max_size)
        elif isinstance(value, list):
            result[key] = [
                limit_input_size(item, max_size) if isinstance(item, dict) else 
                (item[:max_size] if isinstance(item, str) and len(item.encode('utf-8')) > max_size else item)
                for item in value
            ]
        else:
            result[key] = value
    
    return result

# Combined validation decorator for convenience
def validate_request(schema_class=None, content_types=None, sanitize=True):
    """
    Combined decorator for request validation
    
    Args:
        schema_class: Marshmallow schema for validation
        content_types: Allowed content types
        sanitize: Whether to sanitize input
        
    Returns:
        Decorated function with all validations
    """
    def decorator(f):
        # Start with JSON validation
        result = validate_json(f)
        
        # Add content type validation if needed
        if content_types:
            result = validate_content_type(content_types)(result)
            
        # Add schema validation if a schema is provided
        if schema_class:
            result = validate_schema(schema_class)(result)
            
        # Add input sanitization if requested
        if sanitize:
            result = sanitize_input([remove_script_tags, limit_input_size])(result)
            
        return result
        
    return decorator
