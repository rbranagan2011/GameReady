"""
PostHog tracking utility for GameReady.
Handles server-side event tracking.
"""
import posthog
from django.conf import settings

# Initialize PostHog if enabled
if settings.POSTHOG_ENABLED:
    posthog.api_key = settings.POSTHOG_API_KEY
    posthog.host = settings.POSTHOG_HOST
else:
    # Create a no-op PostHog instance if not enabled
    class NoOpPostHog:
        def capture(self, *args, **kwargs):
            pass
        def identify(self, *args, **kwargs):
            pass
        def alias(self, *args, **kwargs):
            pass
    
    posthog = NoOpPostHog()


def track_event(user, event_name, properties=None):
    """
    Track an event in PostHog.
    
    Args:
        user: Django User instance (can be None for anonymous events)
        event_name: Name of the event (e.g., 'report_submitted')
        properties: Dictionary of event properties
    """
    if not settings.POSTHOG_ENABLED:
        return
    
    try:
        user_id = str(user.id) if user and user.is_authenticated else None
        props = properties or {}
        
        # Add user info if authenticated
        if user and user.is_authenticated:
            props['user_email'] = user.email
            props['username'] = user.username
            try:
                if hasattr(user, 'profile'):
                    props['user_role'] = user.profile.role
            except:
                pass
        
        posthog.capture(
            distinct_id=user_id or 'anonymous',
            event=event_name,
            properties=props
        )
    except Exception as e:
        # Silently fail - don't break the app if tracking fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"PostHog tracking error: {e}")


def identify_user(user):
    """
    Identify a user in PostHog (links events to user profile).
    Should be called after login or signup.
    
    Args:
        user: Django User instance
    """
    if not settings.POSTHOG_ENABLED or not user or not user.is_authenticated:
        return
    
    try:
        properties = {
            'email': user.email,
            'username': user.username,
        }
        
        # Add profile info if available
        try:
            if hasattr(user, 'profile'):
                properties['role'] = user.profile.role
                if user.profile.team:
                    properties['team_name'] = user.profile.team.name
        except:
            pass
        
        posthog.identify(
            distinct_id=str(user.id),
            properties=properties
        )
    except Exception as e:
        # Silently fail - don't break the app if tracking fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"PostHog identify error: {e}")

