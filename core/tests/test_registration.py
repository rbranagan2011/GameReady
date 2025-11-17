"""
Tests for user registration and email verification.
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from core.models import Profile, EmailVerification
from core.tests.test_utils import create_test_user


class RegistrationTests(TestCase):
    """Tests for user registration flow."""
    
    def setUp(self):
        """Set up test data."""
        cache.clear()
        self.role_selection_url = reverse('core:role_selection')
        self.signup_url = reverse('core:signup')
    
    def test_role_selection_page_loads(self):
        """Test that role selection page loads."""
        response = self.client.get(self.role_selection_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Athlete')
        self.assertContains(response, 'Coach')
    
    def test_role_selection_stores_in_session(self):
        """Test that role selection stores role in session."""
        # Select athlete role
        response = self.client.post(self.role_selection_url, {'role': 'ATHLETE'})
        self.assertEqual(response.status_code, 302)  # Redirect to signup
        self.assertEqual(self.client.session.get('selected_role'), 'ATHLETE')
        
        # Select coach role
        response = self.client.post(self.role_selection_url, {'role': 'COACH'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('selected_role'), 'COACH')
    
    def test_signup_requires_role_selection(self):
        """Test that signup requires role to be selected first."""
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 302)  # Redirect to role selection
        self.assertRedirects(response, self.role_selection_url)
    
    def test_signup_with_valid_data_creates_user(self):
        """Test that signup with valid data creates inactive user."""
        # Set role in session
        session = self.client.session
        session['selected_role'] = Profile.Role.ATHLETE
        session.save()
        
        # Signup data
        signup_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'accept_terms': True,
        }
        
        with patch('core.signals.send_verification_email') as mock_send:
            response = self.client.post(self.signup_url, signup_data)
            
            # Should redirect to verification pending page
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, reverse('core:verify_email_pending'))
            
            # User should be created but inactive
            user = User.objects.get(email='john@example.com')
            self.assertFalse(user.is_active)
            self.assertEqual(user.first_name, 'John')
            self.assertEqual(user.last_name, 'Doe')
            
            # Profile should be created with correct role
            self.assertEqual(user.profile.role, Profile.Role.ATHLETE)
    
    def test_signup_with_invalid_email(self):
        """Test that signup with invalid email fails."""
        session = self.client.session
        session['selected_role'] = Profile.Role.ATHLETE
        session.save()
        
        signup_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'invalid-email',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'accept_terms': True,
        }
        
        response = self.client.post(self.signup_url, signup_data)
        self.assertEqual(response.status_code, 200)  # Form errors shown
        self.assertFalse(User.objects.filter(email='invalid-email').exists())
    
    def test_signup_with_duplicate_email(self):
        """Test that signup with duplicate email fails."""
        # Create existing user
        create_test_user(email='existing@example.com')
        
        session = self.client.session
        session['selected_role'] = Profile.Role.ATHLETE
        session.save()
        
        signup_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'existing@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'accept_terms': True,
        }
        
        response = self.client.post(self.signup_url, signup_data)
        self.assertEqual(response.status_code, 200)  # Form errors shown
        # Should still only have one user with that email
        self.assertEqual(User.objects.filter(email='existing@example.com').count(), 1)
    
    def test_signup_without_accepting_terms(self):
        """Test that signup without accepting terms fails."""
        session = self.client.session
        session['selected_role'] = Profile.Role.ATHLETE
        session.save()
        
        signup_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'accept_terms': False,  # Not accepted
        }
        
        response = self.client.post(self.signup_url, signup_data)
        self.assertEqual(response.status_code, 200)  # Form errors shown
        self.assertFalse(User.objects.filter(email='john@example.com').exists())


class EmailVerificationTests(TestCase):
    """Tests for email verification flow."""
    
    def setUp(self):
        """Set up test data."""
        self.user = create_test_user(email='test@example.com', is_active=False)
        self.verification, _ = EmailVerification.objects.get_or_create(user=self.user)
    
    def test_email_verification_created_on_signup(self):
        """Test that email verification is created when user signs up."""
        # User should have email verification
        self.assertTrue(hasattr(self.user, 'email_verification'))
        self.assertFalse(self.user.email_verification.verified)
    
    def test_email_verification_token_is_unique(self):
        """Test that verification tokens are unique."""
        user2 = create_test_user(email='test2@example.com', is_active=False)
        verification2, _ = EmailVerification.objects.get_or_create(user=user2)
        
        self.assertNotEqual(self.verification.token, verification2.token)
    
    def test_email_verification_expires_after_24_hours(self):
        """Test that verification tokens expire after 24 hours."""
        # Set created_at to 25 hours ago
        self.verification.created_at = timezone.now() - timedelta(hours=25)
        self.verification.expires_at = timezone.now() - timedelta(hours=1)
        self.verification.save()
        
        self.assertTrue(self.verification.is_expired)
        self.assertFalse(self.verification.is_valid)
    
    def test_verify_email_with_valid_token(self):
        """Test email verification with valid token."""
        verify_url = reverse('core:verify_email', args=[self.verification.token])
        response = self.client.get(verify_url)
        
        # Should redirect and activate user
        self.assertEqual(response.status_code, 302)
        
        # Refresh user from database
        self.user.refresh_from_db()
        self.verification.refresh_from_db()
        
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.verification.verified)
    
    def test_verify_email_with_invalid_token(self):
        """Test email verification with invalid token."""
        verify_url = reverse('core:verify_email', args=['invalid-token'])
        response = self.client.get(verify_url)
        
        # Should redirect to pending page with error
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:verify_email_pending'))
        
        follow_response = self.client.get(verify_url, follow=True)
        self.assertContains(follow_response, 'Invalid verification link', status_code=200)
        
        # User should still be inactive
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
    
    def test_verify_email_with_expired_token(self):
        """Test email verification with expired token."""
        # Expire the token
        self.verification.expires_at = timezone.now() - timedelta(hours=1)
        self.verification.save()
        
        verify_url = reverse('core:verify_email', args=[self.verification.token])
        response = self.client.get(verify_url)
        
        # Should redirect to pending page with expired message
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:verify_email_pending'))
        
        follow_response = self.client.get(verify_url, follow=True)
        self.assertContains(follow_response, 'verification link has expired', status_code=200)
        
        # User should still be inactive
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
    
    def test_verify_email_pending_page_loads(self):
        """Test that verification pending page loads."""
        url = reverse('core:verify_email_pending')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'verification')
    
    def test_user_cannot_login_before_verification(self):
        """Test that unverified users cannot login."""
        login_url = reverse('login')
        response = self.client.post(login_url, {
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Should redirect to verification pending
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:verify_email_pending'))
        
        # User should not be authenticated
        self.assertFalse(response.wsgi_request.user.is_authenticated)

