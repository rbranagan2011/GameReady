"""
Tests for authentication (login, logout, password reset).
"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Profile
from core.tests.test_utils import (
    create_test_user,
    create_test_coach,
    create_test_athlete,
    create_test_report,
)


class LoginTests(TestCase):
    """Tests for user login."""
    
    def setUp(self):
        """Set up test data."""
        self.login_url = reverse('login')
        self.athlete = create_test_athlete()
        self.coach = create_test_coach()
    
    def test_login_page_loads(self):
        """Test that login page loads."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')
    
    def test_login_with_valid_credentials(self):
        """Test login with valid credentials."""
        response = self.client.post(self.login_url, {
            'username': 'athlete@example.com',
            'password': 'athletepass123'
        })
        
        # Should redirect to home/dashboard
        self.assertEqual(response.status_code, 302)
        
        # User should be authenticated
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(self.login_url, {
            'username': 'athlete@example.com',
            'password': 'wrongpassword'
        })
        
        # Should stay on login page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error', status_code=200)
        
        # User should not be authenticated
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_login_with_email_or_username(self):
        """Test that login works with both email and username."""
        # Login with email
        response = self.client.post(self.login_url, {
            'username': 'athlete@example.com',
            'password': 'athletepass123'
        })
        self.assertEqual(response.status_code, 302)
        
        # Logout
        self.client.logout()
        
        # Login with username
        response = self.client.post(self.login_url, {
            'username': 'athlete',
            'password': 'athletepass123'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_login_redirects_authenticated_users(self):
        """Test that authenticated users are redirected from login page."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)  # Redirected to dashboard

    def test_login_rotates_session_and_logs_profile_activity(self):
        """Login should rotate the session key and store last-login metadata."""
        session = self.client.session
        session['prelogin'] = '1'
        session.save()
        original_session_key = session.session_key

        response = self.client.post(
            self.login_url,
            {
                'username': 'athlete@example.com',
                'password': 'athletepass123'
            },
            HTTP_USER_AGENT='GameReadyTest/1.0'
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertNotEqual(original_session_key, self.client.session.session_key)

        profile = self.athlete.profile
        profile.refresh_from_db()
        self.assertIsNotNone(profile.last_login_at)
        self.assertEqual(profile.last_login_ip, '127.0.0.1')
        self.assertEqual(profile.last_login_user_agent, 'GameReadyTest/1.0')


class LogoutTests(TestCase):
    """Tests for user logout."""
    
    def setUp(self):
        """Set up test data."""
        self.athlete = create_test_athlete()
        self.logout_url = reverse('logout')
    
    def test_logout_works(self):
        """Test that logout works."""
        # Login first
        self.client.login(username='athlete@example.com', password='athletepass123')
        self.assertTrue(self.client.session.get('_auth_user_id'))
        
        # Logout
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)  # Redirected to login
        
        # User should not be authenticated
        self.assertIsNone(self.client.session.get('_auth_user_id'))


class HomeRedirectTests(TestCase):
    """Tests for home page redirects based on role."""
    
    def setUp(self):
        """Set up test data."""
        self.home_url = reverse('core:home')
        self.athlete = create_test_athlete()
        self.coach = create_test_coach()
        create_test_report(self.athlete, report_date=timezone.now().date())
    
    def test_home_redirects_unauthenticated_to_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
    
    def test_home_redirects_athlete_to_player_dashboard(self):
        """Test that athletes are redirected to player dashboard."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:player_dashboard'))
    
    def test_home_redirects_coach_to_coach_dashboard(self):
        """Test that coaches are redirected to coach dashboard."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:coach_dashboard'))

