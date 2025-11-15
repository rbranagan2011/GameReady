# Email Configuration Guide for GameReady

This guide explains how to configure email for the GameReady application, especially for Render deployments.

## Why Email is Important

Email verification is required for new user accounts. Without proper email configuration:
- Users cannot verify their accounts
- Daily reminder emails won't be sent
- Password reset emails won't work

## Quick Setup for Render

### Option 1: SendGrid (Recommended for Render)

SendGrid is a popular email service that works well with Render. It offers a free tier with 100 emails/day.

1. **Sign up for SendGrid** (if you don't have an account):
   - Go to https://sendgrid.com
   - Create a free account
   - Verify your account

2. **Create an API Key**:
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Name it (e.g., "GameReady Production")
   - Select "Full Access" or "Mail Send" permissions
   - Copy the API key (you won't see it again!)

3. **Set Environment Variables in Render**:
   - Go to your Render service dashboard
   - Navigate to Environment
   - Add these variables:
     ```
     EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
     EMAIL_HOST=smtp.sendgrid.net
     EMAIL_PORT=587
     EMAIL_USE_TLS=True
     EMAIL_HOST_USER=apikey
     EMAIL_HOST_PASSWORD=<your-sendgrid-api-key>
     DEFAULT_FROM_EMAIL=noreply@gamereadyapp.com
     BASE_URL=https://start.gamereadyapp.com
     ```
   - Replace `<your-sendgrid-api-key>` with the API key you copied
   - Replace `noreply@gamereadyapp.com` with your verified sender email in SendGrid

4. **Verify Sender in SendGrid**:
   - Go to Settings → Sender Authentication
   - Verify a Single Sender or set up Domain Authentication
   - Use the verified email as your `DEFAULT_FROM_EMAIL`

### Option 2: Gmail SMTP

Gmail can be used for development or small deployments, but has limitations.

1. **Enable App Passwords**:
   - Go to your Google Account settings
   - Enable 2-Step Verification
   - Go to App Passwords
   - Generate a new app password for "Mail"

2. **Set Environment Variables in Render**:
   ```
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=<your-app-password>
   DEFAULT_FROM_EMAIL=your-email@gmail.com
   BASE_URL=https://start.gamereadyapp.com
   ```

### Option 3: Other SMTP Services

You can use any SMTP service (Mailgun, AWS SES, etc.) by setting the appropriate environment variables:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<your-smtp-host>
EMAIL_PORT=<your-smtp-port>
EMAIL_USE_TLS=True  # or False if using SSL
EMAIL_HOST_USER=<your-username>
EMAIL_HOST_PASSWORD=<your-password>
DEFAULT_FROM_EMAIL=<your-from-email>
BASE_URL=<your-app-url>
```

## Testing Email Configuration

After setting up email, test it using the management command:

```bash
python manage.py test_email --to your-email@example.com
```

This will:
- Check if email is properly configured
- Send a test email to verify everything works
- Show helpful error messages if something is wrong

## Troubleshooting

### "Email service is not properly configured"

This means one or more email environment variables are missing or incorrect.

**Solution**: Check that all required environment variables are set in Render:
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `BASE_URL`

### "Failed to send verification email"

This could be due to:
1. **Incorrect credentials**: Double-check your `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`
2. **Firewall blocking**: Some networks block SMTP ports
3. **Provider restrictions**: Some email providers require app-specific passwords
4. **Rate limiting**: Free tiers may have sending limits

**Solution**: 
- Run `python manage.py test_email` to see detailed error messages
- Check your email service provider's logs/dashboard
- Verify your API key or password is correct

### Emails going to spam

**Solution**:
- Set up SPF, DKIM, and DMARC records for your domain
- Use a verified sender email address
- Avoid spam trigger words in email content
- Consider using a professional email service like SendGrid

### Users not receiving verification emails

**Solution**:
1. Check if email is configured: Run `python manage.py test_email`
2. Check application logs for email errors
3. Users can resend verification emails from the verification pending page
4. Check spam folders

## Features Added for Email Reliability

The GameReady app now includes:

1. **Email Configuration Validation**: Checks if email is properly configured on startup
2. **Resend Verification Email**: Users can resend verification emails if they don't receive them
3. **Proper Error Logging**: All email errors are logged with details
4. **User-Friendly Error Messages**: Clear messages when email fails
5. **Test Command**: Easy way to verify email configuration

## Environment Variables Summary

Required for production:
- `EMAIL_HOST`: SMTP server hostname
- `EMAIL_PORT`: SMTP server port (usually 587 for TLS)
- `EMAIL_USE_TLS`: Set to `True` for TLS encryption
- `EMAIL_HOST_USER`: SMTP username or API key identifier
- `EMAIL_HOST_PASSWORD`: SMTP password or API key
- `DEFAULT_FROM_EMAIL`: Email address to send from
- `BASE_URL`: Your application URL (for verification links)

## Support

If you continue to have issues:
1. Check the application logs in Render
2. Run the test_email command
3. Verify all environment variables are set correctly
4. Check your email service provider's status page

