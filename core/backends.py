"""
Custom authentication backend for email-based login.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned


class EmailBackend(ModelBackend):
    """
    Authenticate using email instead of username.
    Also supports username for backward compatibility with existing users.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Support both 'username' and 'email' parameters for compatibility
        identifier = kwargs.get('email', username)
        
        if identifier is None or password is None:
            return None
        
        user = None
        
        # Try email first (new users)
        try:
            user = User.objects.get(email=identifier)
        except User.DoesNotExist:
            # Fall back to username for backward compatibility (existing users)
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                # Run the default password hasher once to reduce the timing
                # difference between an existing and a non-existing user
                User().set_password(password)
                return None
        except MultipleObjectsReturned:
            # Multiple users with same email - shouldn't happen but handle it
            user = User.objects.filter(email=identifier).first()
        
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None

