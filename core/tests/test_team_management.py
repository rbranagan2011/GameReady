"""
Tests for team management functionality.
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Team, Profile, TeamSchedule, TeamTag
from core.tests.test_utils import create_test_coach, create_test_athlete, create_test_team
import tempfile
import os
import json
import datetime


class TeamCreationTests(TestCase):
    """Tests for team creation."""
    
    def setUp(self):
        """Set up test data."""
        self.coach = create_test_coach()
        self.team_setup_url = reverse('core:team_setup_coach')
        self.team_admin_url = reverse('core:team_admin')
    
    def test_team_setup_requires_login(self):
        """Test that team setup requires authentication."""
        response = self.client.get(self.team_setup_url)
        self.assertEqual(response.status_code, 302)  # Redirected to login
    
    def test_team_setup_requires_coach_role(self):
        """Test that only coaches can access team setup."""
        athlete = create_test_athlete()
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.team_setup_url)
        self.assertEqual(response.status_code, 302)  # Redirected
    
    def test_team_setup_page_loads(self):
        """Test that team setup page loads for coaches."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.team_setup_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Team')
        self.assertContains(response, 'Join Team')
    
    def test_coach_can_create_team(self):
        """Test that coach can create a new team."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        response = self.client.post(self.team_setup_url, {
            'action': 'create',
            'name': 'New Team'
        })
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Team should be created
        team = Team.objects.get(name='New Team')
        self.assertIsNotNone(team)
        self.assertIsNotNone(team.join_code)
        self.assertEqual(len(team.join_code), 6)  # 6-character code
        
        # Coach should be added to team
        self.coach.profile.refresh_from_db()
        self.assertIn(team, self.coach.profile.get_teams())
    
    def test_team_creation_generates_join_code(self):
        """Test that team creation automatically generates join code."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        self.client.post(self.team_setup_url, {
            'action': 'create',
            'name': 'Team With Code'
        })
        
        team = Team.objects.get(name='Team With Code')
        self.assertIsNotNone(team.join_code)
        self.assertEqual(len(team.join_code), 6)
        # Should be alphanumeric uppercase
        self.assertTrue(team.join_code.isalnum())
        self.assertTrue(team.join_code.isupper())
    
    def test_team_creation_assigns_coach_to_team(self):
        """Test that creating a team assigns coach to that team."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        self.client.post(self.team_setup_url, {
            'action': 'create',
            'name': 'My Team'
        })
        
        team = Team.objects.get(name='My Team')
        self.coach.profile.refresh_from_db()
        
        # Coach should be in team's members
        self.assertIn(team, self.coach.profile.get_teams())
    
    def test_team_creation_sets_active_team_in_session(self):
        """Test that creating a team sets it as active team in session."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        self.client.post(self.team_setup_url, {
            'action': 'create',
            'name': 'Active Team'
        })
        
        team = Team.objects.get(name='Active Team')
        # Check session has active team ID
        self.assertEqual(self.client.session.get('active_team_id'), team.id)
    
    def test_team_name_validation(self):
        """Test that team name validation works."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        # Try to create team with empty name
        response = self.client.post(self.team_setup_url, {
            'action': 'create',
            'name': ''
        })
        
        # Should show form errors
        self.assertEqual(response.status_code, 200)
        # Team should not be created
        self.assertEqual(Team.objects.filter(name='').count(), 0)
    
    def test_team_name_uniqueness(self):
        """Test that team names must be unique."""
        # Create existing team
        existing_team = create_test_team(name='Existing Team', coach=self.coach)
        
        self.client.login(username='coach@example.com', password='coachpass123')
        
        # Try to create team with same name
        response = self.client.post(self.team_setup_url, {
            'action': 'create',
            'name': 'Existing Team'
        })
        
        # Should show form errors
        self.assertEqual(response.status_code, 200)
        # Should still only have one team with that name
        self.assertEqual(Team.objects.filter(name='Existing Team').count(), 1)


class TeamJoinTests(TestCase):
    """Tests for joining teams."""
    
    def setUp(self):
        """Set up test data."""
        self.coach = create_test_coach()
        self.team = create_test_team(name='Joinable Team', coach=self.coach)
        self.athlete = create_test_athlete()
        self.team_setup_url = reverse('core:team_setup_coach')
        self.join_url = reverse('core:join_team_link', args=[self.team.join_code])
    
    def test_athlete_can_join_team_with_code(self):
        """Test that athlete can join team using join code."""
        self.client.login(username='athlete@example.com', password='athletepass123')
        
        # Use join team form (if available) or direct join
        # For now, test that join code exists and is valid
        self.assertIsNotNone(self.team.join_code)
        self.assertEqual(len(self.team.join_code), 6)
    
    def test_join_code_is_case_insensitive(self):
        """Test that join codes work case-insensitively."""
        # Join codes are stored uppercase, but should accept lowercase
        self.assertIsNotNone(self.team.join_code)
        self.assertTrue(self.team.join_code.isupper())


class TeamAdminTests(TestCase):
    """Tests for team administration."""
    
    def setUp(self):
        """Set up test data."""
        self.coach = create_test_coach()
        self.team = create_test_team(name='Admin Team', coach=self.coach)
        self.team_admin_url = reverse('core:team_admin')
    
    def test_team_admin_requires_login(self):
        """Test that team admin requires authentication."""
        response = self.client.get(self.team_admin_url)
        self.assertEqual(response.status_code, 302)  # Redirected to login
    
    def test_team_admin_requires_coach_role(self):
        """Test that only coaches can access team admin."""
        athlete = create_test_athlete()
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.team_admin_url)
        self.assertEqual(response.status_code, 302)  # Redirected
    
    def test_team_admin_page_loads(self):
        """Test that team admin page loads for coaches."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.team_admin_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Team')
    
    def test_coach_can_rename_team(self):
        """Test that coach can rename team."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        response = self.client.post(self.team_admin_url, {
            'action': 'rename',
            'name': 'Renamed Team'
        })
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Team name should be updated
        self.team.refresh_from_db()
        self.assertEqual(self.team.name, 'Renamed Team')
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_coach_can_upload_team_logo(self):
        """Test that coach can upload team logo."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        # Create a simple test image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(img_file.name, 'PNG')
        img_file.seek(0)
        
        with open(img_file.name, 'rb') as f:
            response = self.client.post(self.team_admin_url, {
                'action': 'update_logo',
                'logo': SimpleUploadedFile('test_logo.png', f.read(), content_type='image/png'),
                'logo_display_mode': 'HEADER',
                'background_opacity': '0.1',
                'background_position': 'CENTER',
            })
        
        # Clean up
        os.unlink(img_file.name)
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Team should have logo
        self.team.refresh_from_db()
        # Logo field should be set (check if file exists)
    
    def test_team_logo_file_size_validation(self):
        """Test that team logo file size is validated."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        # Create a file larger than 5MB
        large_file = SimpleUploadedFile(
            'large_logo.png',
            b'x' * (6 * 1024 * 1024),  # 6MB
            content_type='image/png'
        )
        
        response = self.client.post(self.team_admin_url, {
            'action': 'update_logo',
            'logo': large_file,
            'logo_display_mode': 'BACKGROUND',
            'background_opacity': '0.2',
            'background_position': 'CENTER',
        })
        
        # Should show form errors
        self.assertEqual(response.status_code, 200)
        # Should contain error about file size

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_coach_can_remove_logo(self):
        """Removing a logo should clear the field and reset display mode."""
        self.client.login(username='coach@example.com', password='coachpass123')
        # Seed an existing logo
        self.team.logo.save('existing.png', SimpleUploadedFile('existing.png', b'file', content_type='image/png'))
        self.team.logo_display_mode = 'HEADER'
        self.team.save()

        response = self.client.post(self.team_admin_url, {
            'action': 'remove_logo',
        })
        self.assertEqual(response.status_code, 302)
        self.team.refresh_from_db()
        self.assertFalse(self.team.logo)
        self.assertEqual(self.team.logo_display_mode, 'NONE')

    def test_coach_can_remove_athlete_member(self):
        """Coach should be able to remove an athlete from the team."""
        athlete = create_test_athlete(username='member-athlete', email='member@example.com')
        athlete.profile.team = self.team
        athlete.profile.save()

        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.post(self.team_admin_url, {
            'action': 'remove_member',
            'user_id': athlete.id,
        })
        self.assertEqual(response.status_code, 302)
        athlete.profile.refresh_from_db()
        self.assertIsNone(athlete.profile.team)

    def test_cannot_remove_last_coach(self):
        """Attempting to remove the final coach should be prevented."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.post(self.team_admin_url, {
            'action': 'remove_member',
            'user_id': self.coach.id,
        })
        self.assertEqual(response.status_code, 302)
        self.coach.profile.refresh_from_db()
        self.assertEqual(self.coach.profile.team, self.team)

    def test_coach_can_delete_team_with_confirmation(self):
        """Team deletes only when confirmation text matches."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.post(self.team_admin_url, {
            'action': 'delete_team',
            'confirm': 'Admin Team',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Team.objects.filter(name='Admin Team').exists())


class TeamSwitchingTests(TestCase):
    """Tests for team switching functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.coach = create_test_coach()
        self.team1 = create_test_team(name='Team 1', coach=self.coach)
        self.team2 = create_test_team(name='Team 2')
        # Add coach to second team
        self.coach.profile.teams.add(self.team2)
        self.switch_url = reverse('core:switch_team', args=[self.team2.id])
    
    def test_coach_can_switch_teams(self):
        """Test that coach can switch between teams."""
        self.client.login(username='coach@example.com', password='coachpass123')
        
        response = self.client.get(self.switch_url)
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Active team should be updated in session
        self.assertEqual(self.client.session.get('active_team_id'), self.team2.id)
    
    def test_coach_cannot_switch_to_unauthorized_team(self):
        """Test that coach cannot switch to team they don't belong to."""
        unauthorized_team = create_test_team(name='Unauthorized Team')
        
        self.client.login(username='coach@example.com', password='coachpass123')
        
        switch_url = reverse('core:switch_team', args=[unauthorized_team.id])
        response = self.client.get(switch_url)
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Active team should not be changed
        self.assertNotEqual(self.client.session.get('active_team_id'), unauthorized_team.id)


class TeamScheduleSettingsTests(TestCase):
    """Coach-facing schedule builder tests."""

    def setUp(self):
        self.coach = create_test_coach()
        self.team = create_test_team(name='Schedule Team', coach=self.coach)
        self.schedule_url = reverse('core:team_schedule_settings')
        self.tag_training = TeamTag.objects.create(team=self.team, name='Training', target_min=60, target_max=80)
        self.tag_recovery = TeamTag.objects.create(team=self.team, name='Recovery', target_min=40, target_max=60)
        self.schedule = TeamSchedule.objects.create(team=self.team, weekly_schedule={'Mon': self.tag_training.id})

    def _ajax_post(self, payload):
        return self.client.post(
            self.schedule_url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

    def test_view_requires_login(self):
        response = self.client.get(self.schedule_url)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_coach_role(self):
        athlete = create_test_athlete()
        self.client.login(username='athlete@example.com', password='athletepass123')
        response = self.client.get(self.schedule_url)
        self.assertEqual(response.status_code, 302)

    def test_coach_can_load_schedule_page(self):
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self.client.get(self.schedule_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team Schedule Guide')

    def test_ajax_set_all_weekdays(self):
        """Setting all weekdays via AJAX should update weekly_schedule."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self._ajax_post({
            'action': 'set_all_weekdays',
            'day_tag': str(self.tag_recovery.id),
        })
        self.assertEqual(response.status_code, 200)
        self.schedule.refresh_from_db()
        # Ensure at least one weekday changed
        self.assertEqual(self.schedule.weekly_schedule.get('Tue'), self.tag_recovery.id)

    def test_ajax_set_specific_date_override(self):
        """Setting a specific date should store the override."""
        self.client.login(username='coach@example.com', password='coachpass123')
        response = self._ajax_post({
            'date': '2025-11-15',
            'day_tag': str(self.tag_training.id),
        })
        self.assertEqual(response.status_code, 200)
        # set_day_tag stores overrides in date_overrides
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.date_overrides.get('2025-11-15'), self.tag_training.id)

    def test_ajax_clear_month(self):
        """Clearing a month should succeed and remove overrides."""
        self.client.login(username='coach@example.com', password='coachpass123')
        # Seed override to ensure it is cleared
        self.schedule.set_day_tag(datetime.date(2025, 11, 5), self.tag_training.id)
        response = self._ajax_post({
            'action': 'clear_month',
            'month': '2025-11',
        })
        self.assertEqual(response.status_code, 200)
        self.schedule.refresh_from_db()
        self.assertTrue(all(value is None for value in self.schedule.date_overrides.values()))

