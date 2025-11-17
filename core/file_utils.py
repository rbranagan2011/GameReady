"""
Secure file upload utilities for GameReady.

This module provides secure file upload validation including:
- Content-type validation (actual file content, not just extension)
- Filename sanitization (prevents path traversal attacks)
- Storage quota tracking per team
- Security logging
"""

import os
import re
import logging
from pathlib import Path
from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)

# Maximum file size: 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024

# Maximum image dimensions: 2000x2000 pixels
MAX_IMAGE_DIMENSIONS = (2000, 2000)

# Allowed file extensions
ALLOWED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.svg']

# Allowed MIME types (for content-type validation)
ALLOWED_MIME_TYPES = {
    'image/png': ['.png'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/svg+xml': ['.svg'],
}

# Storage quota per team: 10MB (allows multiple logo uploads)
STORAGE_QUOTA_PER_TEAM = 10 * 1024 * 1024


def sanitize_filename(filename):
    """
    Sanitize filename to prevent path traversal and other security issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem storage
        
    Security features:
    - Removes path components (../, /, \\)
    - Removes null bytes
    - Limits length
    - Removes dangerous characters
    - Preserves valid alphanumeric, dots, dashes, underscores
    """
    if not filename:
        return None
    
    # Remove path components to prevent directory traversal
    filename = os.path.basename(filename)
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Remove any remaining path separators
    filename = filename.replace('/', '').replace('\\', '')
    
    # Keep only safe characters: alphanumeric, dots, dashes, underscores
    # This regex keeps: a-z, A-Z, 0-9, ., -, _
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit filename length (max 255 chars for most filesystems)
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    
    # Ensure filename is not empty
    if not filename or filename == '.' or filename == '..':
        # Generate a safe default name
        filename = 'uploaded_file'
    
    return filename


def generate_secure_filename(original_filename, team_id=None):
    """
    Generate a secure, unique filename for uploaded files.
    
    Args:
        original_filename: Original filename from upload
        team_id: Optional team ID for organization
        
    Returns:
        Secure filename with UUID-like hash to prevent collisions
    """
    import secrets
    
    # Sanitize the original filename
    sanitized = sanitize_filename(original_filename)
    
    # Get file extension
    _, ext = os.path.splitext(sanitized)
    ext = ext.lower()
    
    # Generate a random hash for uniqueness (prevents overwrites and collisions)
    random_hash = secrets.token_hex(8)  # 16 character hex string
    
    # Create secure filename: team_id_hash_originalname.ext
    if team_id:
        secure_name = f"{team_id}_{random_hash}_{sanitized}"
    else:
        secure_name = f"{random_hash}_{sanitized}"
    
    # Ensure total length is reasonable
    if len(secure_name) > 255:
        # Truncate but keep extension
        max_name_len = 255 - len(ext)
        secure_name = secure_name[:max_name_len] + ext
    
    return secure_name


def validate_file_content_type(file, allowed_extensions=None, allowed_mime_types=None):
    """
    Validate file content type by actually reading the file content.
    This is more secure than trusting the file extension or Content-Type header.
    
    Args:
        file: Django UploadedFile object
        allowed_extensions: List of allowed extensions (defaults to ALLOWED_EXTENSIONS)
        allowed_mime_types: Dict of MIME types to extensions (defaults to ALLOWED_MIME_TYPES)
        
    Returns:
        tuple: (is_valid, detected_mime_type, error_message)
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS
    if allowed_mime_types is None:
        allowed_mime_types = ALLOWED_MIME_TYPES
    
    # Get file extension
    file_ext = os.path.splitext(file.name)[1].lower()
    
    if file_ext not in allowed_extensions:
        return False, None, f"File extension {file_ext} is not allowed."
    
    # Reset file pointer to beginning
    file.seek(0)
    
    # For SVG files, do basic content validation
    if file_ext == '.svg':
        try:
            content = file.read(1024).decode('utf-8', errors='ignore')
            file.seek(0)
            # Check if it looks like SVG (has SVG tags)
            if '<svg' in content.lower() or '<?xml' in content.lower():
                return True, 'image/svg+xml', None
            else:
                return False, None, "File does not appear to be a valid SVG image."
        except (UnicodeDecodeError, AttributeError):
            return False, None, "Invalid SVG file format."
    
    # For raster images (PNG, JPEG), use Pillow to verify actual image content
    try:
        # Use Pillow to open and verify the image
        img = Image.open(file)
        
        # Verify it's actually an image (Pillow will raise exception if not)
        img.verify()
        
        # Reset file pointer after verify (verify() closes the file)
        file.seek(0)
        
        # Re-open for format detection (verify() closes the file)
        img = Image.open(file)
        detected_format = img.format
        
        # Map Pillow formats to MIME types
        format_to_mime = {
            'PNG': 'image/png',
            'JPEG': 'image/jpeg',
            'JPG': 'image/jpeg',
        }
        
        detected_mime = format_to_mime.get(detected_format)
        
        # Check if detected format matches extension
        if file_ext == '.png' and detected_format != 'PNG':
            return False, detected_mime, f"File extension is .png but file content is {detected_format}."
        elif file_ext in ['.jpg', '.jpeg'] and detected_format not in ['JPEG', 'JPG']:
            return False, detected_mime, f"File extension is {file_ext} but file content is {detected_format}."
        
        # Verify MIME type is allowed
        if detected_mime and detected_mime in allowed_mime_types:
            if file_ext in allowed_mime_types[detected_mime]:
                file.seek(0)  # Reset for saving
                return True, detected_mime, None
        
        file.seek(0)
        return False, detected_mime, f"File content type {detected_mime} is not allowed for extension {file_ext}."
        
    except Exception as e:
        file.seek(0)
        logger.warning(f"Content validation failed for {file.name}: {str(e)}")
        return False, None, f"Invalid image file: {str(e)}"


def validate_image_dimensions(file, max_dimensions=None):
    """
    Validate image dimensions.
    
    Args:
        file: Django UploadedFile object
        max_dimensions: Tuple of (max_width, max_height), defaults to MAX_IMAGE_DIMENSIONS
        
    Returns:
        tuple: (is_valid, dimensions, error_message)
    """
    if max_dimensions is None:
        max_dimensions = MAX_IMAGE_DIMENSIONS
    
    max_width, max_height = max_dimensions
    
    try:
        file.seek(0)
        img = Image.open(file)
        width, height = img.size
        file.seek(0)
        
        if width > max_width or height > max_height:
            return False, (width, height), f"Image dimensions ({width}x{height}) exceed maximum ({max_width}x{max_height})."
        
        return True, (width, height), None
        
    except Exception as e:
        file.seek(0)
        return False, None, f"Could not read image dimensions: {str(e)}"


def get_team_storage_usage(team):
    """
    Calculate total storage usage for a team (in bytes).
    
    Args:
        team: Team model instance
        
    Returns:
        int: Total storage used in bytes
    """
    total_size = 0
    
    # Check team logo
    if team.logo:
        try:
            if os.path.exists(team.logo.path):
                total_size += os.path.getsize(team.logo.path)
        except (ValueError, OSError):
            # File doesn't exist or path is invalid
            pass
    
    return total_size


def check_storage_quota(team, new_file_size, quota=None):
    """
    Check if team has enough storage quota for a new file.
    
    Args:
        team: Team model instance
        new_file_size: Size of new file in bytes
        quota: Storage quota in bytes (defaults to STORAGE_QUOTA_PER_TEAM)
        
    Returns:
        tuple: (has_quota, current_usage, quota_limit, error_message)
    """
    if quota is None:
        quota = STORAGE_QUOTA_PER_TEAM
    
    current_usage = get_team_storage_usage(team)
    
    # If updating existing logo, subtract old logo size
    if team.logo:
        try:
            if os.path.exists(team.logo.path):
                current_usage -= os.path.getsize(team.logo.path)
        except (ValueError, OSError):
            pass
    
    new_total = current_usage + new_file_size
    
    if new_total > quota:
        return False, current_usage, quota, f"Storage quota exceeded. Current usage: {current_usage / 1024 / 1024:.2f}MB, Quota: {quota / 1024 / 1024:.2f}MB"
    
    return True, current_usage, quota, None


def log_file_upload_security_event(event_type, team_id, user_id, filename, file_size, success, error_message=None):
    """
    Log security events related to file uploads for audit trail.
    
    Args:
        event_type: Type of event ('upload_attempt', 'upload_success', 'upload_rejected', etc.)
        team_id: Team ID
        user_id: User ID
        filename: Filename (sanitized)
        file_size: File size in bytes
        success: Whether operation was successful
        error_message: Optional error message
    """
    log_data = {
        'event_type': event_type,
        'team_id': team_id,
        'user_id': user_id,
        'filename': filename,
        'file_size': file_size,
        'success': success,
    }
    
    if error_message:
        log_data['error'] = error_message
    
    if success:
        logger.info(f"File upload security event: {log_data}")
    else:
        logger.warning(f"File upload security event (REJECTED): {log_data}")

