"""
Management command to set up the management user account.
This creates a user with full system access.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile


class Command(BaseCommand):
    help = 'Set up the management user account'

    def handle(self, *args, **options):
        username = 'naganarb1994'
        password = 'Creamwhistlingshark%55'
        email = 'naganarb1994@getreadyapp.com'
        
        # Check if user already exists
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        
        if not created:
            # Update existing user
            user.email = email
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.WARNING(f'Updated existing user: {username}'))
        else:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
        
        # Ensure profile exists
        profile, profile_created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'role': Profile.Role.COACH,  # Set as coach for compatibility
            }
        )
        
        if not profile_created:
            self.stdout.write(self.style.WARNING(f'Profile already exists for: {username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created profile for: {username}'))
        
        self.stdout.write(self.style.SUCCESS('Management user setup complete!'))

