import json
from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Profile, TeamSchedule, TeamTag, ReadinessReport
from core.tests.test_utils import (
    create_test_athlete,
    create_test_coach,
    create_test_team,
    create_test_report,
)


class PlayerAjaxTests(TestCase):
    """Tests for player-facing AJAX endpoints."""

    def setUp(self):
        self.athlete = create_test_athlete(username='player', email='player@example.com')
        self.coach = create_test_coach(username='coach-player', email='coach-player@example.com')
        self.team = create_test_team(name='Player Team', coach=self.coach)
        self.athlete.profile.team = self.team
        self.athlete.profile.save()
        self.athlete.profile.teams.add(self.team)
        self.today = timezone.now().date()
        self.report = create_test_report(self.athlete, report_date=self.today, sleep_quality=7)
        self.client.login(username='player@example.com', password='athletepass123')

    def test_player_metrics_self_ajax_returns_metrics(self):
        url = reverse('core:player_metrics_self_ajax')
        response = self.client.get(url, {'date': self.today.strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['date'], self.today.strftime('%Y-%m-%d'))
        self.assertGreater(len(payload['metrics']), 0)

    def test_player_set_status_updates_profile(self):
        url = reverse('core:player_set_status')
        payload = {'status': Profile.PlayerStatus.AVAILABLE, 'note': 'Ready to play'}
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.athlete.profile.refresh_from_db()
        self.assertEqual(self.athlete.profile.current_status, Profile.PlayerStatus.AVAILABLE)
        self.assertEqual(self.athlete.profile.status_note, 'Ready to play')

    def test_player_set_status_rejects_invalid_status(self):
        url = reverse('core:player_set_status')
        response = self.client.post(
            url,
            data=json.dumps({'status': 'INVALID'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid status', response.json()['message'])


class PlayerPartialViewTests(TestCase):
    """Tests for player dashboard partials."""

    def setUp(self):
        self.athlete = create_test_athlete(username='partial-player', email='partial@example.com', with_today_report=True)
        self.team = create_test_team(name='Partial Team')
        self.athlete.profile.team = self.team
        self.athlete.profile.save()
        self.athlete.profile.teams.add(self.team)
        self.client.login(username='partial@example.com', password='athletepass123')

        self.tag = TeamTag.objects.create(
            team=self.team,
            name='Training',
            target_min=60,
            target_max=80,
            color='#0d6efd',
        )
        self.schedule = TeamSchedule.objects.create(team=self.team)
        self.schedule.set_day_tag('Mon', self.tag.id)

    def test_player_week_partial_returns_html(self):
        url = reverse('core:player_week_partial')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Weekly Overview', response.content.decode())

    def test_player_month_partial_returns_html(self):
        url = reverse('core:player_month_partial')
        response = self.client.get(url, {'month': timezone.now().strftime('%Y-%m')})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Monthly Overview', response.content.decode())

    def test_player_month_partial_includes_day_tags(self):
        """Regression test: ensure schedule dots remain after month navigation."""
        url = reverse('core:player_month_partial')
        response = self.client.get(url, {'month': timezone.now().strftime('%Y-%m')})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # color hex should appear for tag indicator
        self.assertIn('#0d6efd', html)


class CoachPlayerAjaxTests(TestCase):
    """Tests for coach-facing player AJAX endpoints."""

    def setUp(self):
        self.coach = create_test_coach(username='coach-day', email='coach-day@example.com')
        self.team = create_test_team(name='Coach Team', coach=self.coach)
        self.athlete = create_test_athlete(username='ath-day', email='ath-day@example.com')
        self.athlete.profile.team = self.team
        self.athlete.profile.save()
        self.athlete.profile.teams.add(self.team)
        self.client.login(username='coach-day@example.com', password='coachpass123')

        self.tag = TeamTag.objects.create(
            team=self.team,
            name='Game Day',
            target_min=80,
            target_max=100,
            color='#198754',
        )
        self.schedule = TeamSchedule.objects.create(team=self.team)
        self.schedule.set_day_tag('Mon', self.tag.id)
        self.date_str = timezone.now().date().strftime('%Y-%m-%d')

    def test_coach_player_day_details_requires_date(self):
        url = reverse('core:coach_player_day_details', args=[self.athlete.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('Date parameter required', response.json()['message'])

    def test_coach_player_day_details_returns_schedule_tags(self):
        url = reverse('core:coach_player_day_details', args=[self.athlete.id])
        response = self.client.get(url, {'date': self.date_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['day_tags']), 1)

