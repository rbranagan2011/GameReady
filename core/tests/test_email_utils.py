from unittest import mock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from core.email_utils import (
    is_email_configured,
    send_verification_email,
    send_email_safely,
)


User = get_user_model()


class EmailUtilsConfigurationTests(TestCase):
    def test_is_email_configured_requires_default_from(self):
        with override_settings(
            EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
            EMAIL_HOST='smtp.example.com',
            EMAIL_HOST_USER='user',
            EMAIL_HOST_PASSWORD='pass',
            DEFAULT_FROM_EMAIL='',
        ):
            self.assertFalse(is_email_configured())

    def test_is_email_configured_console_backend(self):
        with override_settings(
            EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
            DEFAULT_FROM_EMAIL='noreply@example.com',
        ):
            self.assertTrue(is_email_configured())


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@example.com',
    BASE_URL='https://example.com',
)
class EmailUtilsSendTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='email-user',
            email='email-user@example.com',
            password='testpass123',
            first_name='Email',
            last_name='User',
        )

    @mock.patch('core.email_utils.EmailMessage')
    @mock.patch('core.email_utils.render_to_string', return_value='<p>verify</p>')
    def test_send_verification_email_success(self, render_mock, email_cls):
        email_instance = email_cls.return_value
        email_instance.send.return_value = 1

        success, error = send_verification_email(self.user, 'token-123')

        self.assertTrue(success)
        self.assertIsNone(error)
        render_mock.assert_called_once()
        email_instance.send.assert_called_once()

    def test_send_verification_email_requires_email(self):
        self.user.email = ''
        self.user.save()

        success, error = send_verification_email(self.user, 'token-123')

        self.assertFalse(success)
        self.assertIn('User email is missing', error)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST=None,
        EMAIL_HOST_USER='',
        EMAIL_HOST_PASSWORD='',
        DEFAULT_FROM_EMAIL='',
    )
    def test_send_verification_email_missing_config(self):
        success, error = send_verification_email(self.user, 'token-123')
        self.assertFalse(success)
        self.assertIn('Email service is not properly configured', error)

    @mock.patch('core.email_utils.send_mail')
    def test_send_email_safely_success(self, send_mail_mock):
        send_mail_mock.return_value = 1
        success, error = send_email_safely(
            subject='Hi',
            message='Body',
            recipient_list=['someone@example.com'],
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        send_mail_mock.assert_called_once()

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST=None,
        EMAIL_HOST_USER='',
        EMAIL_HOST_PASSWORD='',
        DEFAULT_FROM_EMAIL='',
    )
    def test_send_email_safely_missing_config(self):
        success, error = send_email_safely('Hi', 'Body', ['user@example.com'])
        self.assertFalse(success)
        self.assertIn('Email service is not properly configured', error)

    def test_send_email_safely_requires_recipients(self):
        success, error = send_email_safely('Hi', 'Body', [])
        self.assertFalse(success)
        self.assertEqual(error, 'No recipients specified')

