"""
Tests for readiness report submission.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from core.models import ReadinessReport, Profile
from core.tests.test_utils import create_test_athlete, create_test_coach, create_test_report


class ReadinessReportSubmissionTests(TestCase):
    """Tests for readiness report submission."""
    
    def setUp(self):
        """Set up test data."""
        self.athlete = create_test_athlete()
        self.coach = create_test_coach()
        self.submit_url = reverse('core:submit_report')
    
    def test_submit_report_requires_login(self):
        """Test that report submission requires authentication."""
        response = self.client.get(self.submit_url)
        self.assertEqual(response.status_code, 302)  # Redirected to login
        self.assertRedirects(response, reverse('login') + '?next=' + self.submit_url)
    
    def test_submit_report_requires_athlete_role(self):
        """Test that only athletes can submit reports."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.submit_url)
        self.assertEqual(response.status_code, 302)  # Redirected to coach dashboard
    
    def test_submit_report_page_loads_for_athlete(self):
        """Test that submit report page loads for athletes."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.submit_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sleep Quality')
        self.assertContains(response, 'Energy')
    
    def test_submit_report_with_valid_data(self):
        """Test submitting a report with valid data."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        
        report_data = {
            'sleep_quality': 8,
            'energy_fatigue': 7,
            'muscle_soreness': 6,
            'mood_stress': 8,
            'motivation': 9,
            'nutrition_quality': 8,
            'hydration': 9,
        }
        
        response = self.client.post(self.submit_url, report_data)
        
        # Should redirect to player dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:player_dashboard'))
        
        # Report should be created
        today = timezone.now().date()
        report = ReadinessReport.objects.get(athlete=self.athlete, date_created=today)
        self.assertEqual(report.sleep_quality, 8)
        self.assertEqual(report.energy_fatigue, 7)
        
        # Readiness score should be calculated
        self.assertIsNotNone(report.readiness_score)
        self.assertGreaterEqual(report.readiness_score, 0)
        self.assertLessEqual(report.readiness_score, 100)
    
    def test_cannot_submit_duplicate_report_same_day(self):
        """Test that athletes cannot submit duplicate reports for the same day."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        
        # Create a report for today
        today = timezone.now().date()
        create_test_report(self.athlete, report_date=today)
        
        # Try to submit another report for today
        report_data = {
            'sleep_quality': 9,
            'energy_fatigue': 8,
            'muscle_soreness': 7,
            'mood_stress': 8,
            'motivation': 9,
            'nutrition_quality': 8,
            'hydration': 9,
        }
        
        response = self.client.post(self.submit_url, report_data)
        
        # Should redirect to dashboard (no error, just redirects)
        self.assertEqual(response.status_code, 302)
        
        # Should still only have one report for today
        reports_today = ReadinessReport.objects.filter(
            athlete=self.athlete, 
            date_created=today
        )
        self.assertEqual(reports_today.count(), 1)
    
    def test_submit_report_with_invalid_data(self):
        """Test submitting a report with invalid data."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        
        # Invalid: value out of range
        report_data = {
            'sleep_quality': 15,  # Should be 1-10
            'energy_fatigue': 7,
            'muscle_soreness': 6,
            'mood_stress': 8,
            'motivation': 9,
            'nutrition_quality': 8,
            'hydration': 9,
        }
        
        response = self.client.post(self.submit_url, report_data)
        
        # Should show form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error', status_code=200)
        
        # No report should be created
        today = timezone.now().date()
        self.assertFalse(
            ReadinessReport.objects.filter(athlete=self.athlete, date_created=today).exists()
        )
    
    def test_readiness_score_calculation(self):
        """Test that readiness score is calculated correctly."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        
        # Submit report with known values
        report_data = {
            'sleep_quality': 10,  # All 10s should give 100%
            'energy_fatigue': 10,
            'muscle_soreness': 10,
            'mood_stress': 10,
            'motivation': 10,
            'nutrition_quality': 10,
            'hydration': 10,
        }
        
        self.client.post(self.submit_url, report_data)
        
        today = timezone.now().date()
        report = ReadinessReport.objects.get(athlete=self.athlete, date_created=today)
        
        # All 10s should give 100% (or very close due to rounding)
        self.assertGreaterEqual(report.readiness_score, 99)
        self.assertLessEqual(report.readiness_score, 100)
    
    def test_can_submit_report_different_days(self):
        """Test that athletes can submit reports for different days."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        
        # Submit report for today
        today = timezone.now().date()
        report_data_today = {
            'sleep_quality': 8,
            'energy_fatigue': 7,
            'muscle_soreness': 6,
            'mood_stress': 8,
            'motivation': 9,
            'nutrition_quality': 8,
            'hydration': 9,
        }
        self.client.post(self.submit_url, report_data_today)
        
        # Create report for yesterday manually (can't submit past dates via form)
        yesterday = today - timedelta(days=1)
        create_test_report(self.athlete, report_date=yesterday)
        
        # Should have reports for both days
        self.assertTrue(
            ReadinessReport.objects.filter(athlete=self.athlete, date_created=today).exists()
        )
        self.assertTrue(
            ReadinessReport.objects.filter(athlete=self.athlete, date_created=yesterday).exists()
        )

