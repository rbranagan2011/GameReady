"""
Test utilities and helper functions for GameReady tests.
"""
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from core.models import Profile, Team, ReadinessReport, EmailVerification


def _make_unique_username(username):
    """Ensure username is unique by appending suffix when needed."""
    if not User.objects.filter(username=username).exists():
        return username
    
    base = username
    counter = 1
    unique_username = f"{base}_{counter}"
    while User.objects.filter(username=unique_username).exists():
        counter += 1
        unique_username = f"{base}_{counter}"
    return unique_username


def _make_unique_email(email):
    """Ensure email is unique by appending +label when needed."""
    if not User.objects.filter(email=email).exists():
        return email
    
    if '@' in email:
        local_part, domain = email.split('@', 1)
    else:
        local_part, domain = email, 'example.com'
    
    counter = 1
    candidate = f"{local_part}+test{counter}@{domain}"
    while User.objects.filter(email=candidate).exists():
        counter += 1
        candidate = f"{local_part}+test{counter}@{domain}"
    return candidate


def create_test_user(username='testuser', email='test@example.com', password='testpass123', 
                     role=Profile.Role.ATHLETE, is_active=True):
    """
    Create a test user with profile.
    
    Args:
        username: Username for the user
        email: Email address
        password: Password
        role: Profile role (ATHLETE or COACH)
        is_active: Whether user is active (for email verification testing)
    
    Returns:
        User instance
    """
    unique_username = _make_unique_username(username)
    unique_email = _make_unique_email(email)
    
    user = User.objects.create_user(
        username=unique_username,
        email=unique_email,
        password=password,
        is_active=is_active
    )
    # Profile is created automatically via signal
    user.profile.role = role
    user.profile.save()
    return user


def create_test_coach(username='coach', email='coach@example.com', password='coachpass123'):
    """Create a test coach user."""
    return create_test_user(username=username, email=email, password=password, 
                           role=Profile.Role.COACH, is_active=True)


def create_test_athlete(
    username='athlete',
    email='athlete@example.com',
    password='athletepass123',
    with_today_report=False,
):
    """
    Create a test athlete user.
    
    Args:
        username: Username for the athlete
        email: Email address
        password: Password
        with_today_report: If True, create a readiness report for today so dashboards render
    """
    athlete = create_test_user(
        username=username,
        email=email,
        password=password,
        role=Profile.Role.ATHLETE,
        is_active=True,
    )
    if with_today_report:
        create_test_report(athlete, report_date=timezone.now().date())
    return athlete


def create_test_team(name='Test Team', coach=None):
    """
    Create a test team.
    
    Args:
        name: Team name
        coach: Optional coach user to assign to team
    
    Returns:
        Team instance
    """
    team = Team.objects.create(name=name)
    if coach:
        coach.profile.team = team
        coach.profile.save()
    return team


def create_test_report(athlete, report_date=None, sleep_quality=8, energy_fatigue=8,
                      muscle_soreness=7, mood_stress=8, motivation=9, 
                      nutrition_quality=8, hydration=9):
    """
    Create a test readiness report.
    
    Args:
        athlete: User instance (athlete)
        report_date: Date for report (defaults to today)
        sleep_quality: Sleep quality score (1-10)
        energy_fatigue: Energy/fatigue score (1-10)
        muscle_soreness: Muscle soreness score (1-10)
        mood_stress: Mood/stress score (1-10)
        motivation: Motivation score (1-10)
        nutrition_quality: Nutrition quality score (1-10)
        hydration: Hydration score (1-10)
    
    Returns:
        ReadinessReport instance
    """
    if report_date is None:
        report_date = timezone.now().date()
    
    report = ReadinessReport.objects.create(
        athlete=athlete,
        date_created=report_date,
        sleep_quality=sleep_quality,
        energy_fatigue=energy_fatigue,
        muscle_soreness=muscle_soreness,
        mood_stress=mood_stress,
        motivation=motivation,
        nutrition_quality=nutrition_quality,
        hydration=hydration
    )
    return report


def create_email_verification(user, verified=False):
    """
    Create an email verification record for testing.
    
    Args:
        user: User instance
        verified: Whether verification is already verified
    
    Returns:
        EmailVerification instance
    """
    verification, _ = EmailVerification.objects.get_or_create(user=user)
    if verified:
        verification.verified = True
        verification.save()
    return verification

