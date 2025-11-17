from django.test import TestCase

from core.validation import (
    validate_date_string,
    validate_month_string,
    validate_team_id,
    validate_athlete_id,
    validate_target_readiness,
    validate_team_schedule_json,
    validate_numeric_range,
    validate_weekday,
    validate_date_overrides_json,
    validate_tag_id,
)
from core.tests.test_utils import create_test_coach, create_test_athlete, create_test_team
from core.models import TeamTag, TeamSchedule


class ValidationTests(TestCase):
    def setUp(self):
        self.coach = create_test_coach()
        self.team = create_test_team(name='Validation Team', coach=self.coach)
        self.athlete = create_test_athlete(
            username='validation-athlete',
            email='validation-athlete@example.com',
        )
        # Attach athlete to team
        self.athlete.profile.team = self.team
        self.athlete.profile.save()

    def test_validate_date_string_success(self):
        is_valid, parsed, error = validate_date_string('2025-11-17')
        self.assertTrue(is_valid)
        self.assertIsNotNone(parsed)
        self.assertIsNone(error)

    def test_validate_date_string_failure(self):
        is_valid, parsed, error = validate_date_string('17-11-2025')
        self.assertFalse(is_valid)
        self.assertIsNone(parsed)
        self.assertIn('YYYY-MM-DD', error)

    def test_validate_month_string_bounds(self):
        is_valid, year, month, error = validate_month_string('2025-12')
        self.assertTrue(is_valid)
        self.assertEqual(year, 2025)
        self.assertEqual(month, 12)

        is_valid, _, _, error = validate_month_string('2025-13')
        self.assertFalse(is_valid)
        self.assertIn('between 01 and 12', error)

    def test_validate_team_id_allows_coach_access(self):
        self.client.login(username='coach@example.com', password='coachpass123')
        valid, team_obj, error = validate_team_id(self.team.id, self.coach)
        self.assertTrue(valid)
        self.assertEqual(team_obj, self.team)
        self.assertIsNone(error)

    def test_validate_team_id_rejects_unknown_team(self):
        valid, team_obj, error = validate_team_id(9999, self.coach)
        self.assertFalse(valid)
        self.assertIsNone(team_obj)
        self.assertEqual(error, 'Team not found')

    def test_validate_athlete_id_checks_membership(self):
        valid, athlete, error = validate_athlete_id(self.athlete.id, self.team)
        self.assertTrue(valid)
        self.assertEqual(athlete, self.athlete)

        other_team = create_test_team(name='Other Team', coach=create_test_coach(username='other', email='other@example.com'))
        valid, _, error = validate_athlete_id(self.athlete.id, other_team)
        self.assertFalse(valid)
        self.assertIn('does not belong', error)

    def test_validate_target_readiness_range(self):
        valid, value, error = validate_target_readiness('75')
        self.assertTrue(valid)
        self.assertEqual(value, 75)

        valid, _, error = validate_target_readiness('150')
        self.assertFalse(valid)
        self.assertIn('between 0 and 100', error)

    def test_validate_team_schedule_json(self):
        TeamTag.objects.create(team=self.team, name='Training', target_min=60, target_max=80)
        weekly = {'Mon': TeamTag.objects.filter(team=self.team).first().id}
        valid, error = validate_team_schedule_json(weekly, self.team)
        self.assertTrue(valid)
        self.assertIsNone(error)

        invalid_weekly = {'Monday': 1}
        valid, error = validate_team_schedule_json(invalid_weekly, self.team)
        self.assertFalse(valid)
        self.assertIn('Invalid weekday', error)

    def test_validate_numeric_range(self):
        valid, parsed, _ = validate_numeric_range('5', 0, 10, 'test_value')
        self.assertTrue(valid)
        self.assertEqual(parsed, 5)

        valid, _, error = validate_numeric_range('20', 0, 10, 'test_value')
        self.assertFalse(valid)
        self.assertIn('between 0 and 10', error)

    def test_validate_weekday(self):
        valid, error = validate_weekday('Mon')
        self.assertTrue(valid)
        self.assertIsNone(error)

        valid, error = validate_weekday('Monday')
        self.assertFalse(valid)
        self.assertIn('weekday must be one of', error)

    def test_validate_date_overrides_json(self):
        tag = TeamTag.objects.create(team=self.team, name='Match', target_min=70, target_max=90)
        overrides = {'2025-11-05': tag.id}
        valid, error = validate_date_overrides_json(overrides, self.team)
        self.assertTrue(valid)
        self.assertIsNone(error)

        invalid = {'05-11-2025': tag.id}
        valid, error = validate_date_overrides_json(invalid, self.team)
        self.assertFalse(valid)
        self.assertIn('Invalid date', error)

    def test_validate_tag_id(self):
        tag = TeamTag.objects.create(team=self.team, name='Rest', target_min=40, target_max=50)
        valid, tag_obj, error = validate_tag_id(tag.id, self.team)
        self.assertTrue(valid)
        self.assertEqual(tag_obj, tag)
        self.assertIsNone(error)

        valid, _, error = validate_tag_id(tag.id, create_test_team(name='Other', coach=create_test_coach(username='other2', email='other2@example.com')))
        self.assertFalse(valid)
        self.assertIn('does not belong', error)

