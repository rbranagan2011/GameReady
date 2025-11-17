"""
Management command to delete a user by email address.

Usage:
    python manage.py delete_user --email user@example.com
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction


class Command(BaseCommand):
    help = 'Delete a user account by email address'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email address of the user to delete',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        force = options.get('force', False)
        
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User with email "{email}" not found.'))
            return
        except User.MultipleObjectsReturned:
            users = User.objects.filter(email__iexact=email)
            self.stdout.write(self.style.WARNING(f'⚠️  Multiple users found with email "{email}":'))
            for u in users:
                self.stdout.write(f'  - ID: {u.id}, Username: {u.username}, Active: {u.is_active}, Created: {u.date_joined}')
            self.stdout.write(self.style.ERROR('Please use user ID to delete specific user.'))
            return
        
        # Show user details
        self.stdout.write(self.style.WARNING('User to be deleted:'))
        self.stdout.write(f'  ID: {user.id}')
        self.stdout.write(f'  Username: {user.username}')
        self.stdout.write(f'  Email: {user.email}')
        self.stdout.write(f'  Full Name: {user.get_full_name()}')
        self.stdout.write(f'  Active: {user.is_active}')
        self.stdout.write(f'  Date Joined: {user.date_joined}')
        
        if hasattr(user, 'profile'):
            self.stdout.write(f'  Role: {user.profile.get_role_display()}')
            if user.profile.team:
                self.stdout.write(f'  Team: {user.profile.team.name}')
        
        # Confirm deletion
        if not force:
            confirm = input('\nAre you sure you want to delete this user? (yes/no): ')
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(self.style.WARNING('Deletion cancelled.'))
                return
        
        # Delete user (this will cascade delete related objects like Profile, EmailVerification, etc.)
        with transaction.atomic():
            username = user.username
            user_email = user.email
            user.delete()
        
        self.stdout.write(self.style.SUCCESS(f'✅ User "{username}" ({user_email}) has been deleted successfully.'))


