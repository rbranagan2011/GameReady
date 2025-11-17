"""
Tests for authorization and role-based access control.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from core.models import Profile
from core.tests.test_utils import (
    create_test_athlete,
    create_test_coach,
    create_test_team,
    create_test_report,
)


class AuthorizationTests(TestCase):
    """Tests for role-based authorization."""
    
    def setUp(self):
        """Set up test data."""
        self.athlete = create_test_athlete()
        self.coach = create_test_coach()
        self.team = create_test_team(coach=self.coach)
        # Add athlete to team
        self.athlete.profile.teams.add(self.team)
        create_test_report(self.athlete, report_date=timezone.now().date())
    
    def test_athlete_cannot_access_coach_dashboard(self):
        """Test that athletes cannot access coach dashboard."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(reverse('core:coach_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirected
        self.assertRedirects(response, reverse('core:home'), target_status_code=302)
    
    def test_coach_cannot_access_player_dashboard(self):
        """Test that coaches cannot access player dashboard."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(reverse('core:player_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirected
        self.assertRedirects(response, reverse('core:home'), target_status_code=302)
    
    def test_coach_can_access_coach_dashboard(self):
        """Test that coaches can access coach dashboard."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(reverse('core:coach_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_athlete_can_access_player_dashboard(self):
        """Test that athletes can access player dashboard."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(reverse('core:player_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_unauthenticated_cannot_access_dashboards(self):
        """Test that unauthenticated users cannot access dashboards."""
        # Try coach dashboard
        response = self.client.get(reverse('core:coach_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirected to login
        
        # Try player dashboard
        response = self.client.get(reverse('core:player_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirected to login
    
    def test_coach_can_view_team_athletes(self):
        """Test that coaches can view athletes from their team."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        # Get athlete detail page
        athlete_detail_url = reverse('core:athlete_detail', args=[self.athlete.id])
        response = self.client.get(athlete_detail_url)
        self.assertEqual(response.status_code, 200)
    
    def test_coach_cannot_view_athletes_from_other_teams(self):
        """Test that coaches cannot view athletes from other teams."""
        # Create another team and athlete
        other_team = create_test_team(name='Other Team')
        from core.tests.test_utils import create_test_user
        other_athlete = create_test_user(
            username='other_athlete',
            email='other@example.com',
            role=Profile.Role.ATHLETE
        )
        other_athlete.profile.teams.add(other_team)
        
        self.client.login(username='coach@example.com', password='coachpass123')
        
        # Try to view athlete from other team
        athlete_detail_url = reverse('core:athlete_detail', args=[other_athlete.id])
        response = self.client.get(athlete_detail_url)
        self.assertEqual(response.status_code, 302)  # Redirected (access denied)
    
    def test_profile_created_on_user_creation(self):
        """Test that profile is automatically created when user is created."""
        from django.contrib.auth.models import User
        user = User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            password='password123'
        )
        
        # Profile should be created automatically via signal
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.role, Profile.Role.ATHLETE)  # Default role

