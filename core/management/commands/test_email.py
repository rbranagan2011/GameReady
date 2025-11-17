"""
Management command to test email configuration.

Usage:
    python manage.py test_email [--to email@example.com]
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from core.email_utils import is_email_configured, send_email_safely


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default=None,
            help='Email address to send test email to (defaults to DEFAULT_FROM_EMAIL)',
        )

    def handle(self, *args, **options):
        recipient = options.get('to') or settings.DEFAULT_FROM_EMAIL
        
        self.stdout.write(self.style.SUCCESS('Testing email configuration...'))
        self.stdout.write('')
        
        # Check if email is configured
        if not is_email_configured():
            self.stdout.write(self.style.ERROR('❌ Email is NOT properly configured!'))
            self.stdout.write('')
            self.stdout.write('Please check the following settings:')
            
            if getattr(settings, 'EMAIL_BACKEND', None) == 'django.core.mail.backends.smtp.EmailBackend':
                self.stdout.write(f'  EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
                self.stdout.write(f'  EMAIL_HOST: {getattr(settings, "EMAIL_HOST", "NOT SET")}')
                self.stdout.write(f'  EMAIL_PORT: {getattr(settings, "EMAIL_PORT", "NOT SET")}')
                self.stdout.write(f'  EMAIL_USE_TLS: {getattr(settings, "EMAIL_USE_TLS", "NOT SET")}')
                self.stdout.write(f'  EMAIL_HOST_USER: {getattr(settings, "EMAIL_HOST_USER", "NOT SET")}')
                self.stdout.write(f'  EMAIL_HOST_PASSWORD: {"***" if getattr(settings, "EMAIL_HOST_PASSWORD", None) else "NOT SET"}')
            else:
                self.stdout.write(f'  EMAIL_BACKEND: {getattr(settings, "EMAIL_BACKEND", "NOT SET")}')
            
            self.stdout.write(f'  DEFAULT_FROM_EMAIL: {getattr(settings, "DEFAULT_FROM_EMAIL", "NOT SET")}')
            self.stdout.write(f'  BASE_URL: {getattr(settings, "BASE_URL", "NOT SET")}')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('For Render deployment, set these environment variables:'))
            self.stdout.write('  - EMAIL_HOST (e.g., smtp.gmail.com or smtp.sendgrid.net)')
            self.stdout.write('  - EMAIL_PORT (e.g., 587)')
            self.stdout.write('  - EMAIL_USE_TLS (True)')
            self.stdout.write('  - EMAIL_HOST_USER (your email username)')
            self.stdout.write('  - EMAIL_HOST_PASSWORD (your email password or API key)')
            self.stdout.write('  - DEFAULT_FROM_EMAIL (e.g., noreply@gamereadyapp.com)')
            self.stdout.write('  - BASE_URL (e.g., https://start.gamereadyapp.com)')
            return
        
        self.stdout.write(self.style.SUCCESS('✅ Email configuration looks good!'))
        self.stdout.write('')
        self.stdout.write(f'Sending test email to: {recipient}')
        
        # Send test email
        success, error_msg = send_email_safely(
            subject='GameReady Email Test',
            message='This is a test email from GameReady. If you received this, your email configuration is working correctly!',
            recipient_list=[recipient],
            html_message='<p>This is a <strong>test email</strong> from GameReady. If you received this, your email configuration is working correctly!</p>',
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS('✅ Test email sent successfully!'))
            self.stdout.write(f'   Please check {recipient} for the test email.')
        else:
            self.stdout.write(self.style.ERROR(f'❌ Failed to send test email: {error_msg}'))
            self.stdout.write('')
            self.stdout.write('Common issues:')
            self.stdout.write('  1. Incorrect SMTP credentials')
            self.stdout.write('  2. Firewall blocking SMTP port')
            self.stdout.write('  3. Email provider requiring app-specific password')
            self.stdout.write('  4. Two-factor authentication not configured for SMTP')


