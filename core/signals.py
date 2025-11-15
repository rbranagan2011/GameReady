from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
import logging
from .models import Profile, EmailVerification
from .email_utils import send_verification_email

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a Profile when a User is created.
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Automatically save the Profile when the User is saved.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # If for some reason the profile doesn't exist, create it
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_email_verification(sender, instance, created, **kwargs):
    """
    Create email verification record and send verification email when a new user is created.
    Only for new users that are not active (awaiting email verification).
    
    This signal uses the email_utils module for proper error handling and logging.
    """
    if created and not instance.is_active:
        # Create email verification record
        verification = EmailVerification.objects.create(user=instance)
        
        # Send verification email using centralized utility
        success, error_msg = send_verification_email(instance, verification.token)
        
        if not success:
            # Log the error - user creation still succeeds, but email failed
            # The user can resend the verification email later
            logger.error(
                f"Failed to send verification email to {instance.email} during signup. "
                f"Error: {error_msg}. User ID: {instance.id}, Verification token: {verification.token}"
            )
