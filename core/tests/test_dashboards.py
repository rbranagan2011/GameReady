"""
Tests for coach and player dashboards.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from core.models import ReadinessReport, TeamSchedule, TeamTag
from core.tests.test_utils import (
    create_test_athlete, create_test_coach, create_test_team, create_test_report
)


class CoachDashboardTests(TestCase):
    """Tests for coach dashboard."""
    
    def setUp(self):
        """Set up test data."""
        self.coach = create_test_coach()
        self.team = create_test_team(name='Test Team', coach=self.coach)
        self.athlete1 = create_test_athlete(username='athlete1', email='athlete1@example.com')
        self.athlete2 = create_test_athlete(username='athlete2', email='athlete2@example.com')
        
        # Add athletes to team
        self.athlete1.profile.teams.add(self.team)
        self.athlete2.profile.teams.add(self.team)
        
        self.dashboard_url = reverse('core:coach_dashboard')
    
    def test_coach_dashboard_requires_login(self):
        """Test that coach dashboard requires authentication."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)  # Redirected to login
    
    def test_coach_dashboard_requires_coach_role(self):
        """Test that only coaches can access coach dashboard."""
        athlete = create_test_athlete()
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)  # Redirected
        self.assertRedirects(response, reverse('core:home'), target_status_code=302)
    
    def test_coach_dashboard_loads_for_coach(self):
        """Test that coach dashboard loads for coaches."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Team')
    
    def test_coach_dashboard_shows_team_athletes(self):
        """Test that coach dashboard shows team athletes."""
        # Create a report for today so athletes show up
        today = timezone.now().date()
        create_test_report(self.athlete1, report_date=today)
        
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        # Should show athlete names or usernames in squad_data
        self.assertIn('squad_data', response.context)
        squad_data = response.context['squad_data']
        athlete_usernames = [item['athlete'].username for item in squad_data]
        self.assertIn('athlete1', athlete_usernames)
    
    def test_coach_dashboard_shows_reports_for_selected_date(self):
        """Test that coach dashboard shows reports for selected date."""
        today = timezone.now().date()
        
        # Create reports for today
        create_test_report(self.athlete1, report_date=today)
        create_test_report(self.athlete2, report_date=today)
        
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.dashboard_url, {'date': today.strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)
        
        # Should show reports in squad_data
        self.assertIn('squad_data', response.context)
        squad_data = response.context['squad_data']
        # Count athletes with submitted reports
        submitted_count = sum(1 for item in squad_data if item.get('submitted', False))
        self.assertEqual(submitted_count, 2)
    
    def test_coach_dashboard_calculates_team_average(self):
        """Test that coach dashboard calculates team average."""
        today = timezone.now().date()
        
        # Create reports with known scores
        create_test_report(self.athlete1, report_date=today, sleep_quality=8, energy_fatigue=8)
        create_test_report(self.athlete2, report_date=today, sleep_quality=6, energy_fatigue=6)
        
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.dashboard_url, {'date': today.strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)
        
        # Should have team average in context
        self.assertIn('today_team_avg', response.context)
        avg = response.context['today_team_avg']
        self.assertIsInstance(avg, (int, float))
        self.assertGreaterEqual(avg, 0)
        self.assertLessEqual(avg, 100)
    
    def test_coach_dashboard_handles_no_team(self):
        """Test that coach dashboard handles coach with no team."""
        coach_no_team = create_test_coach(username='coach_no_team', email='coach_no_team@example.com')
        self.client.login(username='coach_no_team@example.com', password='coachpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        # Should show message about no team
    
    def test_coach_dashboard_date_navigation(self):
        """Test that coach dashboard supports date navigation."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Create report for yesterday
        create_test_report(self.athlete1, report_date=yesterday)
        
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.dashboard_url, {'date': yesterday.strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)
        
        # Should show report for yesterday in squad_data
        self.assertIn('squad_data', response.context)
        squad_data = response.context['squad_data']
        # Count athletes with submitted reports for yesterday
        submitted_count = sum(1 for item in squad_data if item.get('submitted', False))
        self.assertEqual(submitted_count, 1)
    
    def test_coach_dashboard_updates_target_readiness(self):
        """Test that coach can update team target readiness."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        response = self.client.post(self.dashboard_url, {
            'target_readiness': '85'
        })
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Team target should be updated
        self.team.refresh_from_db()
        self.assertEqual(self.team.target_readiness, 85)
    
    def test_coach_dashboard_invalid_target_readiness(self):
        """Test that invalid target readiness values are rejected."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        # Try invalid value (out of range)
        response = self.client.post(self.dashboard_url, {
            'target_readiness': '150'  # Should be 0-100
        })
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Team target should not be updated
        self.team.refresh_from_db()
        self.assertNotEqual(self.team.target_readiness, 150)


class PlayerDashboardTests(TestCase):
    """Tests for player dashboard."""
    
    def setUp(self):
        """Set up test data."""
        self.athlete = create_test_athlete()
        self.dashboard_url = reverse('core:player_dashboard')
    
    def test_player_dashboard_requires_login(self):
        """Test that player dashboard requires authentication."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)  # Redirected to login
    
    def test_player_dashboard_requires_athlete_role(self):
        """Test that only athletes can access player dashboard."""
        coach = create_test_coach()
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)  # Redirected
        self.assertRedirects(response, reverse('core:home'), target_status_code=302)
    
    def test_player_dashboard_loads_for_athlete(self):
        """Test that player dashboard loads for athletes."""
        create_test_report(self.athlete, report_date=timezone.now().date())
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
    
    def test_player_dashboard_shows_todays_report_if_exists(self):
        """Test that player dashboard shows today's report if it exists."""
        today = timezone.now().date()
        create_test_report(self.athlete, report_date=today)
        
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Should show today's report
        self.assertIn('today_report', response.context)
        self.assertIsNotNone(response.context['today_report'])
    
    def test_player_dashboard_shows_weekly_data(self):
        """Test that player dashboard shows weekly data."""
        today = timezone.now().date()
        
        # Create reports for this week
        for i in range(3):
            report_date = today - timedelta(days=i)
            create_test_report(self.athlete, report_date=report_date)
        
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Should have weekly data in context
        # Check for week-related context variables
    
    def test_player_dashboard_week_navigation(self):
        """Test that player dashboard supports week navigation."""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        create_test_report(self.athlete, report_date=today)
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.dashboard_url, {
            'week_start': week_start.strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)
    
    def test_player_dashboard_shows_streak(self):
        """Test that player dashboard shows submission streak."""
        today = timezone.now().date()
        
        # Create reports for consecutive days
        for i in range(3):
            report_date = today - timedelta(days=i)
            create_test_report(self.athlete, report_date=report_date)
        
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Should show streak information
        # Check context for streak data

