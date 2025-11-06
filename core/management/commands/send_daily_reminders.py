from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.db import models
from core.models import Profile, ReadinessReport
from datetime import date, timedelta
from zoneinfo import ZoneInfo

# Try to import pytz for fallback support, but make it optional
try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False


class Command(BaseCommand):
    help = 'Send daily reminder emails to athletes who haven\'t submitted their readiness report today. Timezone-aware - sends at 12pm local time for each user.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually sending emails (for testing)',
        )
        parser.add_argument(
            '--time-window',
            type=int,
            default=15,
            help='Time window in minutes around 12pm to send reminders (default: 15)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        time_window_minutes = options['time_window']
        verbosity = options.get('verbosity', 1)
        
        # Get current UTC time
        now_utc = timezone.now()
        today_utc = now_utc.date()
        
        # Get all athletes who are active, have reminders enabled, and have at least one team
        athletes = User.objects.filter(
            profile__role=Profile.Role.ATHLETE,
            is_active=True,
            profile__daily_reminder_enabled=True
        ).filter(
            models.Q(profile__team__isnull=False) | models.Q(profile__teams__isnull=False)
        ).distinct().select_related('profile')
        
        reminders_sent = 0
        reminders_skipped_submitted = 0
        reminders_skipped_time = 0
        errors = []
        
        # Target time is 12:00 PM (noon)
        target_hour = 12
        target_minute = 0
        
        for athlete in athletes:
            try:
                # Get athlete's timezone
                athlete_timezone_str = athlete.profile.timezone or 'UTC'
                
                # Parse timezone - try zoneinfo first (Python 3.9+), fallback to pytz if available
                athlete_tz = None
                try:
                    athlete_tz = ZoneInfo(athlete_timezone_str)
                except (ValueError, KeyError):
                    # Try pytz if available and zoneinfo failed
                    if HAS_PYTZ:
                        try:
                            athlete_tz = pytz.timezone(athlete_timezone_str)
                        except pytz.exceptions.UnknownTimeZoneError:
                            pass
                    
                    if athlete_tz is None:
                        # Invalid timezone, default to UTC
                        self.stdout.write(
                            self.style.WARNING(
                                f'Invalid timezone "{athlete_timezone_str}" for {athlete.email}, using UTC'
                            )
                        )
                        try:
                            athlete_tz = ZoneInfo('UTC')
                        except (ValueError, KeyError):
                            if HAS_PYTZ:
                                athlete_tz = pytz.UTC
                            else:
                                athlete_tz = ZoneInfo('UTC')  # This should always work
                        athlete.profile.timezone = 'UTC'
                        athlete.profile.save()
                
                # Convert current UTC time to athlete's local timezone
                now_local = now_utc.astimezone(athlete_tz)
                today_local = now_local.date()
                
                # Check if it's within the time window around 12pm
                current_hour = now_local.hour
                current_minute = now_local.minute
                
                # Calculate time difference from 12pm
                target_minutes = target_hour * 60 + target_minute
                current_minutes = current_hour * 60 + current_minute
                time_diff = abs(current_minutes - target_minutes)
                
                # Check if we're within the time window (e.g., 11:45 AM - 12:15 PM)
                if time_diff > time_window_minutes:
                    reminders_skipped_time += 1
                    if verbosity >= 2:
                        local_time_str = now_local.strftime('%I:%M %p %Z')
                        self.stdout.write(
                            f'Skipping {athlete.email} - not in time window (current: {local_time_str})'
                        )
                    continue
                
                # Check if athlete has already submitted a report today (in their local timezone)
                # We need to check both their local date and UTC date to handle edge cases
                has_report = ReadinessReport.objects.filter(
                    athlete=athlete,
                    date_created__in=[today_local, today_utc]
                ).exists()
                
                if has_report:
                    reminders_skipped_submitted += 1
                    if verbosity >= 2:
                        self.stdout.write(f'Skipping {athlete.email} - already submitted today')
                    continue
                
                # Build the submit report URL
                submit_url = settings.BASE_URL + reverse('core:submit_report')
                
                # Get team names for email context
                user_teams = athlete.profile.get_teams()
                if user_teams:
                    team_names = ', '.join([team.name for team in user_teams])
                else:
                    team_names = 'your team'
                
                # Prepare email context
                context = {
                    'user': athlete,
                    'submit_url': submit_url,
                    'site_name': 'GameReady',
                    'team_name': team_names,
                }
                
                # Render email template
                html_message = render_to_string('core/emails/daily_reminder.html', context)
                plain_message = f"""
Hi {athlete.get_full_name() or athlete.email},

Don't forget to log your daily wellness scores for {team_names}!

Your daily check-in helps your coach understand your readiness and optimize training.

Submit your report: {submit_url}

Best regards,
GameReady Team
"""
                
                if not dry_run:
                    # Send the email
                    send_mail(
                        subject='Daily Reminder: Log Your Wellness Scores',
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[athlete.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    reminders_sent += 1
                    local_time_str = now_local.strftime('%I:%M %p %Z')
                    if verbosity >= 1:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Sent reminder to {athlete.email} (local time: {local_time_str})'
                            )
                        )
                else:
                    reminders_sent += 1
                    local_time_str = now_local.strftime('%I:%M %p %Z')
                    if verbosity >= 1:
                        self.stdout.write(
                            self.style.WARNING(
                                f'[DRY RUN] Would send reminder to {athlete.email} (local time: {local_time_str})'
                            )
                        )
                        
            except Exception as e:
                error_msg = f'Error sending reminder to {athlete.email}: {str(e)}'
                errors.append(error_msg)
                if verbosity >= 1:
                    self.stdout.write(
                        self.style.ERROR(error_msg)
                    )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Daily Reminder Summary')
        self.stdout.write('='*50)
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN MODE - No emails were actually sent'))
        self.stdout.write(f'Reminders sent: {reminders_sent}')
        self.stdout.write(f'Reminders skipped (already submitted): {reminders_skipped_submitted}')
        self.stdout.write(f'Reminders skipped (outside time window): {reminders_skipped_time}')
        if errors:
            self.stdout.write(self.style.ERROR(f'Errors: {len(errors)}'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        self.stdout.write('='*50)

