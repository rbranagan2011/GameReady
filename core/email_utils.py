"""
Email utility functions for GameReady.

This module provides centralized email sending functionality with proper error handling,
logging, and support for multiple email backends (SMTP, SendGrid, etc.).
"""
import logging
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def is_email_configured():
    """
    Check if email is properly configured.
    
    Returns:
        bool: True if email is configured, False otherwise
    """
    # Check if we're using console backend (development)
    if getattr(settings, 'EMAIL_BACKEND', None) == 'django.core.mail.backends.console.EmailBackend':
        return True  # Console backend is always "configured" for development
    
    # For SMTP, check required settings
    if getattr(settings, 'EMAIL_BACKEND', None) == 'django.core.mail.backends.smtp.EmailBackend':
        email_host = getattr(settings, 'EMAIL_HOST', None)
        email_host_user = getattr(settings, 'EMAIL_HOST_USER', None)
        email_host_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
        
        # For production, we need at least host and credentials
        if not email_host:
            logger.warning("EMAIL_HOST is not configured")
            return False
        if not email_host_user or not email_host_password:
            logger.warning("EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is not configured")
            return False
    
    # Check DEFAULT_FROM_EMAIL
    if not getattr(settings, 'DEFAULT_FROM_EMAIL', None):
        logger.warning("DEFAULT_FROM_EMAIL is not configured")
        return False
    
    return True


def send_verification_email(user, verification_token):
    """
    Send email verification email to a user.
    
    Args:
        user: User instance
        verification_token: EmailVerification token string
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    # Validate email configuration
    if not is_email_configured():
        error_msg = "Email service is not properly configured. Please contact support."
        logger.error(f"Email not configured - cannot send verification to {user.email}")
        return False, error_msg
    
    # Validate user email
    if not user.email:
        error_msg = "User email is missing"
        logger.error(f"Cannot send verification email - user {user.username} has no email")
        return False, error_msg
    
    try:
        # Build verification URL
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        verification_url = base_url + reverse('core:verify_email', args=[verification_token])
        
        # Render email template
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'GameReady',
        }
        
        html_message = render_to_string('core/emails/verification_email.html', context)
        plain_message = f"""
Hi {user.get_full_name() or user.email},

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
GameReady Team
"""
        
        # Send email
        send_mail(
            subject='Verify your GameReady account',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,  # Raise exception on failure so we can catch it
        )
        
        logger.info(f"Verification email sent successfully to {user.email}")
        return True, None
        
    except Exception as e:
        error_msg = f"Failed to send verification email: {str(e)}"
        logger.error(f"Error sending verification email to {user.email}: {e}", exc_info=True)
        return False, error_msg


def send_email_safely(subject, message, recipient_list, html_message=None, from_email=None):
    """
    Send an email with proper error handling and logging.
    
    Args:
        subject: Email subject
        message: Plain text message
        recipient_list: List of recipient email addresses
        html_message: Optional HTML message
        from_email: Optional from email (defaults to DEFAULT_FROM_EMAIL)
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    if not is_email_configured():
        error_msg = "Email service is not properly configured"
        logger.error("Email not configured - cannot send email")
        return False, error_msg
    
    if not recipient_list:
        error_msg = "No recipients specified"
        logger.error("Cannot send email - no recipients")
        return False, error_msg
    
    try:
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email sent successfully to {', '.join(recipient_list)}")
        return True, None
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(f"Error sending email to {', '.join(recipient_list)}: {e}", exc_info=True)
        return False, error_msg

