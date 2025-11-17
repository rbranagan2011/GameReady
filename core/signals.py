from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction
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
    Uses transaction.on_commit() to ensure email is sent after database transaction commits.
    """
    if created and not instance.is_active:
        # Create or refresh email verification record
        verification, _ = EmailVerification.objects.update_or_create(
            user=instance,
            defaults={
                'token': '',
                'verified': False,
                'expires_at': None,
            },
        )
        
        # Store values we need for the email (in case instance is modified)
        user_email = instance.email
        user_id = instance.id
        verification_token = verification.token
        
        # Send verification email AFTER the transaction commits
        # This ensures the user and verification record are fully saved before sending
        def send_email_after_commit():
            # Refresh user from database to ensure we have the latest data
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.error(f"User {user_id} not found when trying to send verification email")
                return
            
            logger.info(f"Transaction committed. Sending verification email to {user_email} (User ID: {user_id})")
            success, error_msg = send_verification_email(user, verification_token)
            
            if not success:
                # Log the error - user creation still succeeds, but email failed
                # The user can resend the verification email later
                logger.error(
                    f"Failed to send verification email to {user_email} during signup. "
                    f"Error: {error_msg}. User ID: {user_id}, Verification token: {verification_token}"
                )
            else:
                logger.info(
                    f"Verification email sent successfully to {user_email} after transaction commit. "
                    f"User ID: {user_id}"
                )
        
        # Schedule email to be sent after transaction commits
        transaction.on_commit(send_email_after_commit)
