"""
Response Formatter for TechSaaS API

This module provides standardized response formatting and error handling
for consistent API responses across the platform.
"""

import time
import logging
from typing import Any, Dict, List, Optional, Union
from flask import jsonify, Response

# Configure logging
logger = logging.getLogger(__name__)

class ResponseFormatter:
    """
    Utility class for formatting standardized API responses
    """
    
    @staticmethod
    def success_response(
        data: Any = None,
        message: str = "Operation completed successfully",
        metadata: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        start_time: Optional[float] = None
    ) -> Response:
        """
        Create a standardized success response
        
        Args:
            data: The response data
            message: A success message
            metadata: Additional metadata about the request/response
            status_code: HTTP status code
            start_time: Request start time for calculating processing time
            
        Returns:
            Flask Response object with standardized JSON structure
        """
        response_data = {
            "status": "success",
            "message": message,
            "data": data if data is not None else {},
            "metadata": {
                "timestamp": time.time(),
                "processing_time_ms": round((time.time() - start_time) * 1000) if start_time else None,
                **(metadata or {})
            }
        }
        
        return jsonify(response_data), status_code
    
    @staticmethod
    def error_response(
        error: Union[str, Exception],
        message: str = "An error occurred",
        status_code: int = 400,
        error_type: str = "request_error",
        error_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None,
        log_error: bool = True
    ) -> Response:
        """
        Create a standardized error response
        
        Args:
            error: The error message or exception
            message: A user-friendly error message
            status_code: HTTP status code
            error_type: Type of error (request_error, server_error, validation_error, etc.)
            error_details: Additional details about the error
            metadata: Additional metadata about the request/response
            start_time: Request start time for calculating processing time
            log_error: Whether to log the error
            
        Returns:
            Flask Response object with standardized JSON structure
        """
        # Convert exception to string if needed
        if isinstance(error, Exception):
            error_str = str(error)
            if log_error:
                logger.exception(f"API error ({error_type}): {error_str}")
        else:
            error_str = error
            if log_error:
                logger.error(f"API error ({error_type}): {error_str}")
        
        response_data = {
            "status": "error",
            "message": message,
            "error": {
                "type": error_type,
                "details": error_str,
                **(error_details or {})
            },
            "metadata": {
                "timestamp": time.time(),
                "processing_time_ms": round((time.time() - start_time) * 1000) if start_time else None,
                **(metadata or {})
            }
        }
        
        return jsonify(response_data), status_code
    
    @staticmethod
    def validation_error(
        errors: Union[List[Dict[str, Any]], Dict[str, Any]],
        message: str = "Validation error",
        status_code: int = 422,
        metadata: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None
    ) -> Response:
        """
        Create a standardized validation error response
        
        Args:
            errors: List of validation errors or dict of field errors
            message: A user-friendly error message
            status_code: HTTP status code
            metadata: Additional metadata about the request/response
            start_time: Request start time for calculating processing time
            
        Returns:
            Flask Response object with standardized JSON structure
        """
        
        return ResponseFormatter.error_response(
            error="Validation failed",
            message=message,
            status_code=status_code,
            error_type="validation_error",
            error_details={"validation_errors": errors},
            metadata=metadata,
            start_time=start_time,
            log_error=False
        )
    
    @staticmethod
    def tier_limit_error(
        tier: str,
        limit_type: str,
        current_usage: int,
        allowed_limit: int,
        message: str = "Usage limit exceeded for your subscription tier",
        status_code: int = 429,
        metadata: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None
    ) -> Response:
        """
        Create a standardized tier limit error response
        
        Args:
            tier: User's subscription tier
            limit_type: Type of limit (requests_per_minute, tokens_per_day, etc.)
            current_usage: Current usage
            allowed_limit: Maximum allowed usage
            message: A user-friendly error message
            status_code: HTTP status code
            metadata: Additional metadata about the request/response
            start_time: Request start time for calculating processing time
            
        Returns:
            Flask Response object with standardized JSON structure
        """
        
        return ResponseFormatter.error_response(
            error=f"Tier limit exceeded: {current_usage}/{allowed_limit} {limit_type}",
            message=message,
            status_code=status_code,
            error_type="tier_limit_error",
            error_details={
                "tier": tier,
                "limit_type": limit_type,
                "current_usage": current_usage,
                "allowed_limit": allowed_limit,
                "upgrade_url": "https://techsaas.tech/pricing"
            },
            metadata=metadata,
            start_time=start_time,
            log_error=False
        )
    
    @staticmethod
    def authentication_error(
        message: str = "Authentication required",
        status_code: int = 401,
        error_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None
    ) -> Response:
        """
        Create a standardized authentication error response
        
        Args:
            message: A user-friendly error message
            status_code: HTTP status code
            error_details: Additional details about the error
            metadata: Additional metadata about the request/response
            start_time: Request start time for calculating processing time
            
        Returns:
            Flask Response object with standardized JSON structure
        """
        
        return ResponseFormatter.error_response(
            error="Authentication failed",
            message=message,
            status_code=status_code,
            error_type="authentication_error",
            error_details=error_details,
            metadata=metadata,
            start_time=start_time,
            log_error=True
        )
    
    @staticmethod
    def permission_error(
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        status_code: int = 403,
        metadata: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None
    ) -> Response:
        """
        Create a standardized permission error response
        
        Args:
            message: A user-friendly error message
            required_permission: Permission that was required
            status_code: HTTP status code
            metadata: Additional metadata about the request/response
            start_time: Request start time for calculating processing time
            
        Returns:
            Flask Response object with standardized JSON structure
        """
        
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
        
        return ResponseFormatter.error_response(
            error="Permission denied",
            message=message,
            status_code=status_code,
            error_type="permission_error",
            error_details=details,
            metadata=metadata,
            start_time=start_time,
            log_error=True
        )
    
    @staticmethod
    def model_error(
        error: Union[str, Exception],
        model_name: str,
        message: str = "Error processing request with AI model",
        status_code: int = 500,
        metadata: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None
    ) -> Response:
        """
        Create a standardized AI model error response
        
        Args:
            error: The error message or exception
            model_name: Name of the AI model
            message: A user-friendly error message
            status_code: HTTP status code
            metadata: Additional metadata about the request/response
            start_time: Request start time for calculating processing time
            
        Returns:
            Flask Response object with standardized JSON structure
        """
        
        return ResponseFormatter.error_response(
            error=error,
            message=message,
            status_code=status_code,
            error_type="model_error",
            error_details={"model": model_name},
            metadata=metadata,
            start_time=start_time,
            log_error=True
        )
