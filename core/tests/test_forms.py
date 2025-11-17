import os
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from PIL import Image

from core.forms import (
    TeamLogoForm,
    TeamScheduleForm,
    ReminderSettingsForm,
    JoinTeamForm,
    JoinTeamByCodeForm,
    FeatureRequestForm,
    FeatureRequestCommentForm,
    AddMemberForm,
)
from core.models import TeamSchedule, TeamTag
from core.tests.test_utils import create_test_team, create_test_athlete, create_test_coach


class TeamLogoFormTests(TestCase):
    """Tests for TeamLogoForm validation and saving."""

    def setUp(self):
        self.team = create_test_team()
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _make_image_file(self, name='logo.png', size=(100, 100), color='red'):
        img = Image.new('RGB', size, color=color)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile(name, buffer.read(), content_type='image/png')

    def _make_large_image_file(self, name='large_logo.png'):
        """Generate a noisy PNG file that exceeds the 5MB limit."""
        side = 1800
        max_size = 5 * 1024 * 1024
        while True:
            img = Image.effect_noise((side, side), 100).convert('RGB')
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            data = buffer.getvalue()
            if len(data) > max_size:
                return SimpleUploadedFile(name, data, content_type='image/png')
            side += 200

    def test_team_logo_form_accepts_valid_image(self):
        """Form saves when provided a valid image and required branding fields."""
        form = TeamLogoForm(
            data={
                'logo_display_mode': 'HEADER',
                'background_opacity': '0.15',
                'background_position': 'CENTER',
            },
            files={'logo': self._make_image_file()},
            instance=self.team,
        )

        self.assertTrue(form.is_valid())
        saved_team = form.save()
        self.assertTrue(saved_team.logo.name.endswith('.png'))
        self.assertTrue(os.path.exists(saved_team.logo.path))

    def test_team_logo_form_rejects_large_file(self):
        """Files larger than the 5MB limit should raise validation errors."""
        large_file = self._make_large_image_file()

        form = TeamLogoForm(
            data={
                'logo_display_mode': 'BACKGROUND',
                'background_opacity': '0.2',
                'background_position': 'CENTER',
            },
            files={'logo': large_file},
            instance=self.team,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('File is too large', form.errors['logo'][0])

    def test_team_logo_form_rejects_invalid_extension(self):
        """Unsupported file extensions should be rejected with clear messaging."""
        bad_file = self._make_image_file(name='logo.exe')

        form = TeamLogoForm(
            data={
                'logo_display_mode': 'BOTH',
                'background_opacity': '0.25',
                'background_position': 'TOP_LEFT',
            },
            files={'logo': bad_file},
            instance=self.team,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('File extension', form.errors['logo'][0])


class TeamScheduleFormTests(TestCase):
    """Tests for TeamScheduleForm weekly schedule handling."""

    def setUp(self):
        self.team = create_test_team()
        self.tag_a = TeamTag.objects.create(team=self.team, name='Training', target_min=60, target_max=80)
        self.tag_b = TeamTag.objects.create(team=self.team, name='Recovery', target_min=40, target_max=60)
        self.schedule = TeamSchedule.objects.create(team=self.team, weekly_schedule={'Mon': self.tag_a.id})

    def _all_day_data(self, value):
        return {
            'day_mon': str(value),
            'day_tue': str(value),
            'day_wed': str(value),
            'day_thu': str(value),
            'day_fri': str(value),
            'day_sat': str(value),
            'day_sun': str(value),
        }

    def test_schedule_form_populates_existing_values(self):
        """Existing weekly_schedule values should populate initial field data."""
        form = TeamScheduleForm(instance=self.schedule)
        self.assertEqual(form.fields['day_mon'].initial, self.tag_a.id)

    def test_schedule_form_saves_weekly_schedule(self):
        """Form should persist selected tags as integers in weekly_schedule."""
        data = self._all_day_data(self.tag_b.id)
        form = TeamScheduleForm(data=data, instance=self.schedule)
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertEqual(saved.weekly_schedule['Tue'], self.tag_b.id)

    def test_schedule_form_rejects_invalid_input(self):
        """Invalid tag values should trigger validation errors."""
        data = self._all_day_data(self.tag_a.id)
        data['day_wed'] = 'invalid'
        form = TeamScheduleForm(data=data, instance=self.schedule)
        self.assertFalse(form.is_valid())
        self.assertIn('Select a valid choice', form.errors['day_wed'][0])


class ReminderSettingsFormTests(TestCase):
    """Tests for reminder preference management."""

    def setUp(self):
        self.athlete = create_test_athlete(username='reminder-user', email='reminder@example.com')
        self.profile = self.athlete.profile
        self.profile.daily_reminder_enabled = False
        self.profile.timezone = 'UTC'
        self.profile.save()

    def test_form_initializes_from_profile(self):
        """Initial values should match the profile."""
        form = ReminderSettingsForm(profile=self.profile)
        self.assertFalse(form.fields['daily_reminder_enabled'].initial)
        self.assertEqual(form.fields['timezone'].initial, 'UTC')

    def test_form_requires_timezone(self):
        """Timezone is mandatory even if reminders are disabled."""
        form = ReminderSettingsForm(
            data={'daily_reminder_enabled': True, 'timezone': ''},
            profile=self.profile
        )
        self.assertFalse(form.is_valid())
        self.assertIn('This field is required.', form.errors['timezone'])

    def test_form_saves_preferences_to_profile(self):
        """Saving should persist to the profile instance."""
        form = ReminderSettingsForm(
            data={'daily_reminder_enabled': True, 'timezone': 'America/New_York'},
            profile=self.profile
        )
        self.assertTrue(form.is_valid())
        form.save()
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.daily_reminder_enabled)
        self.assertEqual(self.profile.timezone, 'America/New_York')


class JoinTeamFormTests(TestCase):
    """Tests for joining a team via join code."""

    def setUp(self):
        self.team = create_test_team(name='Joinable Team')

    def test_valid_join_code_returns_team(self):
        form = JoinTeamForm(data={'join_code': self.team.join_code})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['team'], self.team)

    def test_invalid_format_rejected(self):
        form = JoinTeamForm(data={'join_code': 'abc'})
        self.assertFalse(form.is_valid())
        self.assertIn('Team code must be 6 alphanumeric characters.', form.errors['join_code'])

    def test_unknown_code_rejected(self):
        form = JoinTeamForm(data={'join_code': 'ZZZZZZ'})
        self.assertFalse(form.is_valid())
        self.assertIn('Invalid team code', form.errors['join_code'][0])


class JoinTeamByCodeFormTests(TestCase):
    """Tests for authenticated users joining teams via code."""

    def setUp(self):
        self.user = create_test_athlete(username='joiner', email='joiner@example.com')
        self.team = create_test_team(name='Secondary Team')

    def test_form_adds_team_to_profile(self):
        form = JoinTeamByCodeForm(
            data={'join_code': self.team.join_code},
            user=self.user,
        )
        self.assertTrue(form.is_valid())
        saved_team = form.save()
        self.assertEqual(saved_team, self.team)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.teams.filter(id=self.team.id).exists())

    def test_requires_join_code(self):
        form = JoinTeamByCodeForm(data={}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('This field is required.', form.errors['join_code'])

    def test_rejects_invalid_code_format(self):
        form = JoinTeamByCodeForm(data={'join_code': '!!!'}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Team code must be 6 alphanumeric characters.', form.errors['join_code'][0])

    def test_rejects_duplicate_membership(self):
        self.user.profile.teams.add(self.team)
        form = JoinTeamByCodeForm(
            data={'join_code': self.team.join_code},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('You are already a member of this team.', form.non_field_errors())


class FeatureRequestFormTests(TestCase):
    """Tests for feature/bug request submission form."""

    def test_valid_data_is_sanitized(self):
        form = FeatureRequestForm(
            data={
                'request_type': 'FEATURE',
                'title': '<b>New view</b>',
                'description': '<script>alert("xss")</script>This should render cleanly.',
            }
        )
        self.assertTrue(form.is_valid())
        self.assertNotIn('<', form.cleaned_data['title'])
        self.assertNotIn('<', form.cleaned_data['description'])

    def test_short_title_rejected(self):
        form = FeatureRequestForm(
            data={
                'request_type': 'FEATURE',
                'title': 'abc',
                'description': 'Detailed description that meets length requirements.',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('Title must be at least 5 characters long.', form.errors['title'])

    def test_short_description_rejected(self):
        form = FeatureRequestForm(
            data={
                'request_type': 'BUG',
                'title': 'Valid title',
                'description': '          short',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('at least 10 characters', form.errors['description'][0])


class FeatureRequestCommentFormTests(TestCase):
    """Tests for feature request comments."""

    def test_valid_comment_is_sanitized(self):
        form = FeatureRequestCommentForm(data={'comment': '<b>Great idea!</b>'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['comment'], 'Great idea!')

    def test_comment_requires_minimum_length(self):
        form = FeatureRequestCommentForm(data={'comment': '   ok'})
        self.assertFalse(form.is_valid())
        self.assertIn('at least 3 characters', form.errors['comment'][0])


class AddMemberFormTests(TestCase):
    """Tests for adding existing members to a team."""

    def setUp(self):
        self.existing_user = create_test_athlete(username='existing-user', email='existing@example.com')

    def test_requires_username_or_email(self):
        form = AddMemberForm(data={'username': '', 'email': '', 'role': 'ATHLETE'})
        self.assertFalse(form.is_valid())
        self.assertIn('Provide a username or email', form.non_field_errors()[0])

    def test_finds_user_by_username(self):
        form = AddMemberForm(data={'username': 'existing-user', 'role': 'ATHLETE'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['user_obj'], self.existing_user)

    def test_finds_user_by_email(self):
        form = AddMemberForm(data={'username': '', 'email': 'existing@example.com', 'role': 'COACH'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['user_obj'], self.existing_user)

    def test_unknown_user_raises_error(self):
        form = AddMemberForm(data={'username': 'missing', 'role': 'ATHLETE'})
        self.assertFalse(form.is_valid())
        self.assertIn('User not found', form.non_field_errors()[0])

