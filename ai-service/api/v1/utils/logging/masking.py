"""
PII Masking Module for TechSaaS Logging

This module provides functionality to mask personally identifiable information (PII)
and other sensitive data in log records to ensure compliance with privacy regulations.

SECURITY NOTE: This file contains regex patterns for DETECTING sensitive information.
It does NOT contain any actual credentials, API keys, or sensitive data.
These patterns are used solely to identify and mask such information in logs and responses.
"""

import re
import copy
from typing import Dict, Any, List, Union, Pattern, Callable, Tuple

# Define PII patterns
# SECURITY NOTE: These are detection patterns only, not actual sensitive data
PII_PATTERNS = {
    # Credit Card Numbers (major cards)
    'credit_card': re.compile(r'\b(?:\d{4}[ -]?){3}\d{4}\b'),
    
    # Email Addresses
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    
    # Social Security Numbers (US)
    'ssn': re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'),
    
    # Phone Numbers (various formats)
    'phone': re.compile(r'\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b'),
    
    # IP Addresses (IPv4)
    'ipv4': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
    
    # IP Addresses (IPv6)
    'ipv6': re.compile(r'\b([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\b'),
    
    # Passport Numbers (US format)
    'passport': re.compile(r'\b[A-Z]{1,2}[0-9]{6,9}\b'),
    
    # Dates of Birth
    'dob': re.compile(r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b'),
    
    # API Keys, Tokens, and Secrets (common patterns)
    'api_key': re.compile(r'\b[a-zA-Z0-9_\-]{20,40}\b'),
    
    # Authentication tokens (JWT-like patterns)
    'auth_token': re.compile(r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'),
    
    # Password fields
    'password': re.compile(r'\b(password|passwd|pwd|secret)[:=]\s*[^\s,;]{3,}\b', re.IGNORECASE),
}

# Define sensitive field names (case-insensitive keys)
# SECURITY NOTE: These are field names to look for, not actual values
SENSITIVE_FIELDS = {
    # Authentication
    'password', 'passwd', 'pwd', 'secret', 'api_key', 'apikey', 'api_secret',
    'token', 'auth_token', 'authorization', 'authentication', 'access_token', 
    'refresh_token', 'session_token', 'session_id', 'cookie', 'csrf_token',
    
    # Personal Information
    'ssn', 'social_security', 'social_security_number', 'tax_id', 'national_id',
    'passport', 'passport_number', 'driver_license', 'drivers_license', 
    'license_number', 'dob', 'date_of_birth', 'birthdate', 'birth_date',
    
    # Financial Information
    'credit_card', 'card_number', 'cc_number', 'cvv', 'cvc', 'ccv', 'security_code',
    'expiry', 'expiration', 'card_expiry', 'card_expiration', 'account_number',
    'routing_number', 'bank_account', 'iban', 'swift', 'tax_id',
    
    # Contact Information
    'phone', 'phone_number', 'mobile', 'mobile_number', 'fax', 'fax_number',
    'email', 'email_address', 'address', 'street', 'city', 'postal_code',
    'zip', 'zip_code', 'postcode', 'state', 'country',
}

# Field masking configuration
DEFAULT_MASK = '********'
PARTIAL_MASKS = {
    'credit_card': lambda v: v[:6] + '*' * (len(v) - 10) + v[-4:] if len(v) >= 12 else DEFAULT_MASK,
    'email': lambda v: v[:3] + '****@' + v.split('@')[1] if '@' in v and len(v.split('@')[0]) > 3 else DEFAULT_MASK,
    'phone': lambda v: v[:3] + '****' + v[-3:] if len(v) >= 7 else DEFAULT_MASK,
    'ssn': lambda v: '***-**-' + v[-4:] if len(v) >= 9 else DEFAULT_MASK,
}


def mask_string(value: str) -> str:
    """
    Mask PII in a string using regular expressions.
    
    Args:
        value: String that may contain PII
        
    Returns:
        String with PII masked
    """
    if not isinstance(value, str):
        return value
    
    masked_value = value
    
    # Apply PII pattern masking
    for pii_type, pattern in PII_PATTERNS.items():
        # Check if we should use a partial mask for this PII type
        mask_func = PARTIAL_MASKS.get(pii_type, lambda _: DEFAULT_MASK)
        
        # Replace each match with its appropriate mask
        def mask_match(match):
            matched_text = match.group(0)
            return mask_func(matched_text)
        
        masked_value = pattern.sub(mask_match, masked_value)
    
    return masked_value


def mask_field_by_name(field_name: str, value: Any) -> Any:
    """
    Mask a value if its field name matches a sensitive pattern.
    
    Args:
        field_name: Name of the field
        value: Value to potentially mask
        
    Returns:
        Masked value if field is sensitive, otherwise original value
    """
    # Normalize field name for comparison
    normalized_name = field_name.lower().replace('-', '_').strip()
    
    # Check exact matches
    if normalized_name in SENSITIVE_FIELDS:
        if isinstance(value, str):
            # Use partial masking if available for this field type
            for pii_type, mask_func in PARTIAL_MASKS.items():
                if pii_type in normalized_name:
                    return mask_func(value)
            # Default masking
            return DEFAULT_MASK
        return DEFAULT_MASK
    
    # Check for sensitive substrings in field name
    for sensitive_field in SENSITIVE_FIELDS:
        if sensitive_field in normalized_name:
            if isinstance(value, str):
                return DEFAULT_MASK
            return DEFAULT_MASK
    
    return value


def mask_pii(data: Any) -> Any:
    """
    Recursively mask PII in data structures.
    
    This function handles:
    - Dictionaries (recursive masking of values)
    - Lists and tuples (recursive masking of elements)
    - Strings (pattern-based masking)
    - Other types are returned as-is
    
    Args:
        data: Data structure to mask
        
    Returns:
        Data structure with PII masked
    """
    if data is None:
        return None
    
    # Handle dictionaries
    if isinstance(data, dict):
        masked_data = {}
        for key, value in data.items():
            # First check if field name itself is sensitive
            masked_value = mask_field_by_name(key, value)
            
            # If the value wasn't masked by field name, recursively check it
            if masked_value == value and not isinstance(value, (int, float, bool, type(None))):
                masked_value = mask_pii(value)
            
            masked_data[key] = masked_value
        return masked_data
    
    # Handle lists
    elif isinstance(data, list):
        return [mask_pii(item) for item in data]
    
    # Handle tuples
    elif isinstance(data, tuple):
        return tuple(mask_pii(item) for item in data)
    
    # Handle strings
    elif isinstance(data, str):
        return mask_string(data)
    
    # Other types (numbers, booleans, None) are returned as-is
    return data


def add_sensitive_field(field_name: str) -> None:
    """
    Add a custom field name to the list of sensitive fields.
    
    Args:
        field_name: Name of the field to add
    """
    SENSITIVE_FIELDS.add(field_name.lower())


def add_pii_pattern(name: str, pattern: Union[str, Pattern]) -> None:
    """
    Add a custom PII pattern for masking.
    
    Args:
        name: Name for the pattern
        pattern: Regular expression pattern (string or compiled)
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    PII_PATTERNS[name] = pattern


def add_partial_mask(pii_type: str, mask_function: Callable[[str], str]) -> None:
    """
    Add a custom partial masking function for a PII type.
    
    Args:
        pii_type: PII type name
        mask_function: Function that takes a string and returns a masked string
    """
    PARTIAL_MASKS[pii_type] = mask_function
