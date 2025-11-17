"""
Input sanitization utilities for GameReady.

This module provides secure text sanitization to prevent XSS attacks and
malicious content in user-generated text fields.

Uses the bleach library to sanitize HTML content while preserving safe text.
"""

import bleach
import logging
import re
import html

logger = logging.getLogger(__name__)

# Allowed HTML tags (empty list means strip all HTML)
# For most user-generated content, we want plain text only
ALLOWED_TAGS = []

# Allowed HTML attributes (empty list means strip all attributes)
ALLOWED_ATTRIBUTES = {}

# Allowed protocols for links (empty list means no links allowed)
ALLOWED_PROTOCOLS = []


def sanitize_text_field(text, max_length=None, strip_html=True):
    """
    Sanitize a text field to prevent XSS attacks and malicious content.
    
    Args:
        text: Input text to sanitize
        max_length: Optional maximum length (truncates if longer)
        strip_html: If True, removes all HTML tags. If False, allows safe HTML.
        
    Returns:
        Sanitized text string
        
    Security features:
    - Removes all HTML tags by default (prevents XSS)
    - Strips dangerous characters
    - Truncates to max_length if provided
    - Preserves plain text content
    """
    if not text:
        return ''
    
    # Convert to string if not already
    text = str(text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    if strip_html:
        # Remove all HTML tags and decode HTML entities
        # This prevents XSS attacks while preserving plain text
        text = bleach.clean(
            text,
            tags=ALLOWED_TAGS,  # No tags allowed = strip all HTML
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,  # Strip tags instead of escaping
        )
        
        # Decode HTML entities (e.g., &amp; -> &, &lt; -> <)
        text = html.unescape(text)
    
    # Remove null bytes and other dangerous characters
    text = text.replace('\x00', '')
    text = text.replace('\r', '')
    
    # Normalize whitespace (replace multiple spaces/tabs/newlines with single space)
    text = re.sub(r'\s+', ' ', text)
    
    # Truncate if max_length specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Text truncated to {max_length} characters")
    
    return text.strip()


def sanitize_html_field(html_content, allowed_tags=None, allowed_attributes=None):
    """
    Sanitize HTML content while allowing safe HTML tags.
    
    Use this for fields where HTML formatting is desired (e.g., rich text editors).
    Currently not used in GameReady, but available for future use.
    
    Args:
        html_content: HTML content to sanitize
        allowed_tags: List of allowed HTML tags (defaults to safe subset)
        allowed_attributes: Dict of allowed attributes per tag
        
    Returns:
        Sanitized HTML string
    """
    if not html_content:
        return ''
    
    # Default safe tags for rich text (if needed in future)
    if allowed_tags is None:
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'a']
    
    if allowed_attributes is None:
        allowed_attributes = {
            'a': ['href', 'title'],
        }
    
    # Sanitize HTML, keeping only safe tags and attributes
    sanitized = bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=['http', 'https', 'mailto'],
        strip=True,
    )
    
    return sanitized


def validate_no_html(text, field_name="Field"):
    """
    Validate that text contains no HTML tags.
    
    Args:
        text: Text to validate
        field_name: Name of the field (for error messages)
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not text:
        return True, None
    
    # Check for HTML tags
    html_pattern = re.compile(r'<[^>]+>')
    if html_pattern.search(text):
        return False, f"{field_name} cannot contain HTML tags. Please use plain text only."
    
    # Check for HTML entities (might indicate attempt to bypass)
    html_entity_pattern = re.compile(r'&[#\w]+;')
    if html_entity_pattern.search(text):
        # Decode and check again
        decoded = html.unescape(text)
        if html_pattern.search(decoded):
            return False, f"{field_name} contains invalid characters. Please use plain text only."
    
    return True, None


def sanitize_filename(text):
    """
    Sanitize text for use in filenames.
    
    This is a simple sanitizer for text that might be used in filenames.
    For actual file uploads, use file_utils.sanitize_filename() instead.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text safe for filenames
    """
    if not text:
        return ''
    
    # Remove path components
    text = text.replace('/', '').replace('\\', '')
    
    # Remove dangerous characters
    text = re.sub(r'[<>:"|?*]', '', text)
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Limit length
    if len(text) > 200:
        text = text[:200]
    
    return text.strip()
