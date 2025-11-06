from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from .models import Profile, EmailVerification


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
    """
    if created and not instance.is_active:
        # Create email verification record
        verification = EmailVerification.objects.create(user=instance)
        
        # Send verification email
        try:
            # Build verification URL
            verification_url = settings.BASE_URL + reverse('core:verify_email', args=[verification.token])
            
            # Render email template
            context = {
                'user': instance,
                'verification_url': verification_url,
                'site_name': 'GameReady',
            }
            
            html_message = render_to_string('core/emails/verification_email.html', context)
            plain_message = f"""
Hi {instance.get_full_name() or instance.email},

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
GameReady Team
"""
            
            send_mail(
                subject='Verify your GameReady account',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log error but don't fail user creation
            # In production, you'd want to use proper logging here
            print(f"Error sending verification email: {e}")
