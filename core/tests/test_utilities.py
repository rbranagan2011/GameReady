import logging
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone

from core.validation import (
    validate_date_string,
    validate_month_string,
    validate_weekday,
    validate_target_readiness,
    validate_numeric_range,
    validate_team_schedule_json,
    validate_date_overrides_json,
)
from core.sanitization import (
    sanitize_text_field,
    sanitize_html_field,
    sanitize_filename,
    validate_no_html,
)
from core.email_utils import (
    is_email_configured,
    send_email_safely,
    send_verification_email,
)
from core.audit_logging import (
    log_user_action,
    log_team_action,
    log_data_modification,
    log_report_submission,
)
from core.security_logging import log_join_code_attempt
from core.tests.test_utils import create_test_coach, create_test_team
from core.models import TeamTag


class ValidationUtilityTests(TestCase):
    """Tests for core.validation helper functions."""

    def setUp(self):
        self.coach = create_test_coach(username='validation-coach', email='validation-coach@example.com')
        self.team = create_test_team(name='Validation Team', coach=self.coach)
        self.tag = TeamTag.objects.create(team=self.team, name='Practice', target_min=60, target_max=80)

    def test_validate_date_string(self):
        ok, parsed, error = validate_date_string('2025-11-17', 'test_date')
        self.assertTrue(ok)
        self.assertIsNotNone(parsed)
        self.assertIsNone(error)

        ok, parsed, error = validate_date_string('17-11-2025', 'test_date')
        self.assertFalse(ok)
        self.assertIn('YYYY-MM-DD', error)

    def test_validate_month_string(self):
        ok, year, month, error = validate_month_string('2025-11', 'test_month')
        self.assertTrue(ok)
        self.assertEqual((year, month), (2025, 11))

        ok, year, month, error = validate_month_string('2025-20', 'test_month')
        self.assertFalse(ok)
        self.assertIn('between 01 and 12', error)

    def test_validate_target_readiness_and_numeric_range(self):
        self.assertEqual(validate_target_readiness('75')[:2], (True, 75))
        self.assertFalse(validate_target_readiness('999')[0])

        ok, value, error = validate_numeric_range('5', 1, 10, 'rating')
        self.assertTrue(ok)
        self.assertEqual(value, 5)

        self.assertFalse(validate_numeric_range('20', 1, 10, 'rating')[0])

    def test_validate_weekday_and_schedule_json(self):
        self.assertTrue(validate_weekday('Mon')[0])
        ok, error = validate_weekday('Funday')
        self.assertFalse(ok)
        self.assertIn('weekday must be one of', error)

        weekly_schedule = {'Mon': self.tag.id, 'Tue': None}
        ok, error = validate_team_schedule_json(weekly_schedule, self.team)
        self.assertTrue(ok)

        invalid_schedule = {'Holiday': self.tag.id}
        ok, error = validate_team_schedule_json(invalid_schedule, self.team)
        self.assertFalse(ok)
        self.assertIn('Invalid weekday', error)

        overrides = {'2025-11-17': self.tag.id}
        ok, error = validate_date_overrides_json(overrides, self.team)
        self.assertTrue(ok)

        overrides_bad = {'2025/11/17': self.tag.id}
        ok, error = validate_date_overrides_json(overrides_bad, self.team)
        self.assertFalse(ok)
        self.assertIn('Invalid date', error)


class SanitizationUtilityTests(TestCase):
    """Tests for core.sanitization."""

    def test_sanitize_text_field_strips_html_and_whitespace(self):
        dirty = '   <script>alert("xss")</script>Hello   World   '
        cleaned = sanitize_text_field(dirty)
        self.assertNotIn('<', cleaned)
        self.assertTrue(cleaned.endswith('Hello World'))

    def test_sanitize_html_field_keeps_safe_tags(self):
        html = '<p>Hello <strong>World</strong><script>alert(1)</script></p>'
        sanitized = sanitize_html_field(html)
        self.assertEqual(sanitized, '<p>Hello <strong>World</strong>alert(1)</p>')

    def test_validate_no_html(self):
        ok, error = validate_no_html('Plain text', 'Comment')
        self.assertTrue(ok)
        self.assertIsNone(error)

        ok, error = validate_no_html('<b>bold</b>', 'Comment')
        self.assertFalse(ok)
        self.assertIn('cannot contain HTML', error)

    def test_sanitize_filename(self):
        filename = sanitize_filename('../etc/passwd.png')
        self.assertEqual(filename, '..etcpasswd.png')


class EmailUtilityTests(TestCase):
    """Tests for email utility helpers."""

    def setUp(self):
        self.user = create_test_coach(username='email-coach', email='coach-email@example.com')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        DEFAULT_FROM_EMAIL='admin@example.com',
    )
    def test_is_email_configured_console_backend(self):
        self.assertTrue(is_email_configured())

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.example.com',
        EMAIL_HOST_USER='apikey',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='admin@example.com',
    )
    def test_send_email_safely(self):
        with patch('core.email_utils.send_mail') as mock_send_mail:
            mock_send_mail.return_value = 1
            success, error = send_email_safely(
                subject='Test',
                message='Hello',
                recipient_list=['user@example.com'],
            )
        self.assertTrue(success)
        self.assertIsNone(error)
        mock_send_mail.assert_called_once()

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        DEFAULT_FROM_EMAIL='admin@example.com',
        BASE_URL='http://testserver',
    )
    def test_send_verification_email(self):
        with patch('core.email_utils.EmailMessage') as mock_message:
            mock_instance = mock_message.return_value
            mock_instance.send.return_value = 1
            success, error = send_verification_email(self.user, 'token123')
        self.assertTrue(success)
        self.assertIsNone(error)
        mock_instance.send.assert_called_once()

    @override_settings(DEFAULT_FROM_EMAIL=None)
    def test_send_verification_email_missing_config(self):
        success, error = send_verification_email(self.user, 'token123')
        self.assertFalse(success)
        self.assertIn('not properly configured', error)


class AuditLoggingTests(TestCase):
    """Ensure audit logging helpers emit structured log entries."""

    def setUp(self):
        self.user = create_test_coach(username='audit', email='audit@example.com')
        self.team = create_test_team(name='Audit Team', coach=self.user)

    def test_log_user_action(self):
        with self.assertLogs('core.audit_logging', level='INFO') as logs:
            log_user_action('user_login', self.user, success=True, details={'ip': '127.0.0.1'})
        self.assertIn('user_login', logs.output[0])

        with self.assertLogs('core.audit_logging', level='WARNING') as logs:
            log_user_action('user_login', self.user, success=False, error_message='Invalid password')
        self.assertIn('FAILED', logs.output[0])

    def test_log_team_and_data_actions(self):
        with self.assertLogs('core.audit_logging', level='INFO') as logs:
            log_team_action('team_joined', self.user, self.team.id, team_name=self.team.name)
        self.assertIn('team_joined', logs.output[0])

        with self.assertLogs('core.audit_logging', level='WARNING') as logs:
            log_data_modification('update', self.user, 'TeamTag', object_id=123, success=False, error_message='Denied')
        self.assertIn('FAILED', logs.output[0])

        with self.assertLogs('core.audit_logging', level='INFO') as logs:
            log_report_submission(self.user, report_id=10, readiness_score=85, date=str(timezone.now().date()))
        self.assertIn('report_submitted', logs.output[0])


class SecurityLoggingTests(TestCase):
    """Tests for join code security logging."""

    def test_join_code_logging_formats_entries(self):
        with self.assertLogs('core.security_logging', level='WARNING') as logs:
            log_join_code_attempt(
                event_type='join_code_invalid',
                ip_address='1.2.3.4',
                user_id=5,
                join_code='ABC123',
                success=False,
                error_message='Invalid code',
            )
        self.assertIn('join_code_invalid', logs.output[0])
        self.assertIn('FAILED', logs.output[0])

        with self.assertLogs('core.security_logging', level='INFO') as logs:
            log_join_code_attempt(
                event_type='join_success',
                ip_address='1.2.3.4',
                user_id=5,
                team_id=7,
                success=True,
            )
        self.assertIn('join_success', logs.output[0])

