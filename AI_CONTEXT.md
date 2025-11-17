# GameReady - AI Assistant Context Document

**Purpose**: This document provides comprehensive context about the GameReady application for AI assistants working on the codebase. Reference this at the start of new conversations.

**⚠️ IMPORTANT: Update this document whenever major changes are made to the application!**
- Add new features, models, or workflows
- Update code patterns or conventions
- Document new environment variables or deployment changes
- Note any breaking changes or important gotchas
- Keep the "Recent Improvements" section current

---

## Application Overview

**GameReady** is a Django web application for tracking athlete wellness metrics to help coaches optimize training and reduce injury risk.

### Core Purpose
- Athletes log 7 daily wellness metrics (1-10 scale)
- Coaches view dashboards, track team readiness, and manage schedules
- System calculates readiness scores automatically using weighted averages
- Supports multiple teams, team branding, and personalized schedules

---

## Tech Stack

- **Backend**: Django 5.2.7
- **Database**: 
  - Development: SQLite
  - Production: PostgreSQL (on Render)
- **Frontend**: Bootstrap 5 with responsive design
- **Deployment**: Render.com
- **Email**: SendGrid (SMTP)
- **Analytics**: PostHog (optional)
- **Authentication**: Django's built-in auth with custom email backend

---

## Key Models & Relationships

### Core Models

1. **Team**
   - Groups athletes and coaches
   - Has `join_code` (6-character alphanumeric, auto-generated)
   - Supports team branding: logo, display modes (HEADER/BACKGROUND/BOTH), opacity, position
   - Has `target_readiness` (0-100)

2. **Profile** (extends Django User)
   - Roles: `ATHLETE` or `COACH`
   - Team relationships:
     - `team` (ForeignKey) - primary team (backward compatibility)
     - `teams` (ManyToMany) - supports multiple teams (primarily for athletes)
   - Player status: `AVAILABLE`, `INJURED`, `SICK`, `EXCUSED` (with status_note)
   - Timezone support for daily reminders
   - `daily_reminder_enabled` boolean

3. **ReadinessReport**
   - Daily wellness report submitted by athletes
   - 7 metrics (1-10 scale): sleep_quality, energy_fatigue, muscle_soreness, mood_stress, motivation, nutrition_quality, hydration
   - `readiness_score` (0-100) - calculated automatically using weighted average
   - Unique constraint: one report per athlete per day
   - Includes `get_personalized_feedback()` method for insights

4. **TeamTag**
   - Coach-defined day types (e.g., "Game Day", "Training", "Rest")
   - Has `target_min` and `target_max` (0-100) for acceptable readiness range
   - Color (HEX) for UI badges
   - Team-specific (visible only to owning team)

5. **TeamSchedule**
   - Weekly schedule pattern (JSON: {"Mon": tag_id, "Tue": tag_id, ...})
   - Date overrides (JSON: {"2025-10-26": tag_id, ...})
   - Methods: `get_day_tag()`, `set_day_tag()`, `get_day_tag_id()`

6. **EmailVerification**
   - Email verification tokens for new user accounts
   - Tokens expire after 24 hours
   - Users are inactive until email verified

7. **PlayerPersonalLabel**
   - Athletes can add personal labels to days (e.g., "Gym session")
   - Informational only (doesn't affect target ranges)
   - Coaches can see these

8. **FeatureRequest** & **FeatureRequestComment**
   - User-submitted feature requests and bug reports
   - Supports upvoting and comments

---

## Key Features & Workflows

### User Registration Flow
1. User selects role (ATHLETE or COACH) → `role_selection`
2. User signs up → `signup` (creates inactive user)
3. Email verification signal sends verification email (via `transaction.on_commit()`)
4. User clicks verification link → `verify_email` (activates user, auto-login)
5. Redirect based on role:
   - COACH → `team_setup_coach`
   - ATHLETE → `athlete_setup`

### Email Verification
- Uses `core/email_utils.py` for centralized email sending
- Signal: `create_email_verification` in `core/signals.py`
- Uses `transaction.on_commit()` to ensure email sent after DB commit
- Users can resend verification emails via `resend_verification_email` view
- Prominent spam folder reminder on verification pending page

### Daily Reporting
- Athletes submit one report per day via `submit_readiness_report`
- If already submitted today, redirects to dashboard (no message)
- Readiness score calculated automatically using weighted average
- Weights: sleep_quality (0.22), energy_fatigue (0.20), muscle_soreness (0.15), mood_stress (0.15), motivation (0.10), nutrition_quality (0.10), hydration (0.08)

### Coach Dashboard
- Shows team overview with color-coded readiness scores
- Weekly and monthly views
- Individual athlete detail pages
- Compliance tracking (who has/hasn't submitted)
- Team schedule management with tags

### Team Management
- Coaches can have multiple teams (via ManyToMany)
- Session stores `active_team_id` for coach's active team
- Team switching via `switch_team` view
- Team branding: logos can appear in header, background, or both

### Schedule System
- Weekly patterns: assign TeamTags to weekdays
- Date overrides: specific dates can override weekly pattern
- Athletes see colored dots on calendar showing scheduled activities
- Personal labels: athletes can add their own labels to days

---

## Important Code Patterns & Conventions

### Email Handling
- **Centralized utility**: `core/email_utils.py`
- **Functions**: `send_verification_email()`, `send_email_safely()`, `is_email_configured()`
- **Headers**: Friendly "From" name format: `"GameReady <admin@gamereadyapp.com>"`
- **Transaction safety**: Use `transaction.on_commit()` for emails in signals

### Authentication
- **Custom backend**: `core/backends.EmailBackend` - allows login with email or username
- **Inactive users**: Users are inactive until email verified
- **Login view**: `CustomLoginView` handles unverified email accounts

### Team Context
- **Helper function**: `get_coach_active_team(request)` - gets coach's active team
- **Context processor**: `coach_active_team` - available in all templates
- **Session storage**: `active_team_id` stores coach's active team

### Messages & UX
- **NO_SUCCESS_MESSAGES_RULE**: Success messages are hidden (app flows smoothly without confirmation boxes)
- **Error messages**: Only show errors, not success confirmations
- **Mobile-first**: Responsive design, prevents double-tap zoom

### Database Transactions
- **Email sending**: Always use `transaction.on_commit()` in signals
- **User creation**: Signals fire during user creation, emails must wait for commit

---

## File Structure

```
GameReady/
├── GameReady/              # Django project settings
│   ├── settings/
│   │   ├── base.py        # Common settings
│   │   ├── development.py # Local development
│   │   └── production.py  # Production (Render)
│   └── urls.py
├── core/                   # Main application
│   ├── models.py          # All database models
│   ├── views.py           # All view functions (4000+ lines)
│   ├── forms.py           # Form definitions
│   ├── urls.py            # URL routing
│   ├── signals.py         # Django signals (profile creation, email verification)
│   ├── backends.py        # Custom authentication backend
│   ├── email_utils.py     # Email sending utilities
│   ├── posthog_tracking.py # Analytics tracking
│   ├── context_processors.py # Template context
│   ├── management/commands/ # Custom management commands
│   │   ├── test_email.py
│   │   ├── delete_user.py
│   │   └── send_daily_reminders.py
│   └── templates/core/    # App-specific templates
├── templates/             # Base templates
│   ├── base.html         # Main base template
│   └── registration/     # Auth templates
├── static/               # Static files
└── manage.py
```

---

## Environment Variables (Production - Render)

Required environment variables:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Set to `False` in production
- `ALLOWED_HOSTS` - Comma-separated list
- `CSRF_TRUSTED_ORIGINS` - Comma-separated list
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - PostgreSQL
- `EMAIL_BACKEND` - `django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST` - `smtp.sendgrid.net`
- `EMAIL_PORT` - `587`
- `EMAIL_USE_TLS` - `True`
- `EMAIL_HOST_USER` - `apikey` (for SendGrid)
- `EMAIL_HOST_PASSWORD` - SendGrid API key
- `DEFAULT_FROM_EMAIL` - `admin@gamereadyapp.com` (verified in SendGrid)
- `BASE_URL` - `https://start.gamereadyapp.com`
- `ADMINS` - (optional but recommended) Admin email for error notifications. Format: `"Name,email@example.com"` or `"email@example.com"`. Multiple admins: `"Name1,email1@example.com;Name2,email2@example.com"`
- `POSTHOG_API_KEY` - (optional) PostHog analytics
- `POSTHOG_HOST` - (optional) PostHog host

---

## Recent Improvements & Important Notes

### Email System (Latest)
- **Bullet-proof email verification** with proper error handling
- **Transaction-safe**: Uses `transaction.on_commit()` to ensure emails sent after DB commit
- **Resend functionality**: Users can resend verification emails
- **Spam folder reminders**: Prominent reminders to check spam folder
- **Email deliverability**: Friendly "From" name, proper headers
- **Configuration validation**: Startup warnings if email not configured
- **Admin error notifications**: ADMINS setting configured for 500 error email alerts
- **Test command**: `python manage.py test_email` to test email setup

### User Experience
- **No success messages**: App flows smoothly without confirmation boxes (see NO_SUCCESS_MESSAGES_RULE)
- **Mobile optimization**: Prevents double-tap zoom, touch-friendly
- **Add to Home Screen**: Device-specific instructions (iOS/Android)
- **Team branding**: Logos can appear in header and/or background

### Code Quality
- **Centralized email utilities**: All email sending goes through `email_utils.py`
- **Proper logging**: All email errors logged with details
- **Error handling**: Graceful failures, user-friendly error messages

---

## Common Tasks & Patterns

### Adding a New View
1. Add view function to `core/views.py`
2. Add URL pattern to `core/urls.py`
3. Create template in `templates/core/`
4. Use `@login_required` decorator if authentication required
5. Check role if role-specific: `if request.user.profile.role != Profile.Role.COACH:`

### Sending Emails
```python
from core.email_utils import send_email_safely

success, error_msg = send_email_safely(
    subject='Subject',
    message='Plain text message',
    recipient_list=['user@example.com'],
    html_message='<p>HTML message</p>'
)
```

### Accessing Coach's Active Team
```python
from core.views import get_coach_active_team

active_team = get_coach_active_team(request)
# Or in templates: {{ coach_active_team.name }}
```

### Creating a User with Profile
```python
user = User.objects.create_user(
    username=email,
    email=email,
    password=password,
    is_active=False  # Must verify email first
)
# Profile created automatically via signal
profile = user.profile
profile.role = Profile.Role.ATHLETE
profile.save()
```

---

## Important Gotchas

1. **Email verification**: Users are inactive until email verified. Signal sends email using `transaction.on_commit()`.

2. **Multiple teams**: Athletes can belong to multiple teams via `teams` ManyToMany. Coaches typically have one team but can have multiple.

3. **Readiness score calculation**: Uses weighted average, not simple average. Weights are in `ReadinessReport.calculate_readiness_score()`.

4. **No success messages**: Success messages are hidden in templates. Only show errors/warnings.

5. **Team context**: Coaches have an "active team" stored in session. Use `get_coach_active_team(request)` helper.

6. **Email from address**: Must match verified sender in SendGrid (`admin@gamereadyapp.com`).

7. **Transaction safety**: Always use `transaction.on_commit()` when sending emails in signals.

8. **Mobile-first**: App is designed for mobile use. Prevent double-tap zoom, use touch-friendly controls.

---

## Testing & Debugging

### Test Email Configuration
```bash
python manage.py test_email --to your-email@example.com
```

### Delete User (for testing)
```bash
python manage.py delete_user --email user@example.com --force
```

### Check Email Logs
- Check Render logs for email sending errors
- Check SendGrid Activity Feed for delivery status

---

## Deployment

- **Platform**: Render.com
- **Database**: PostgreSQL (managed by Render)
- **Static files**: WhiteNoise
- **Media files**: Render persistent disk at `/opt/render/project/src/media`
- **Auto-deploy**: Enabled (deploys on git push to master)

---

## Key URLs

- `/` - Home (redirects based on role)
- `/login/` - Login page
- `/role-selection/` - Select role (ATHLETE/COACH)
- `/signup/` - User registration
- `/verify-email-pending/` - Email verification pending
- `/verify-email/<token>/` - Verify email link
- `/resend-verification/` - Resend verification email
- `/player-dashboard/` - Athlete dashboard
- `/coach-dashboard/` - Coach dashboard
- `/submit-report/` - Submit daily readiness report
- `/team-schedule/` - Team schedule management
- `/team-admin/` - Team administration

---

## Code Style & Best Practices

- **Clean, tested, production-ready code**
- **Minimal assumptions** - list any assumptions in comments
- **Simple explanations** - avoid jargon, break down complex concepts
- **Small code chunks** - don't overwhelm with large blocks
- **Comments in code** - explain what each part does
- **Step-by-step instructions** - break tasks into clear sequential steps

---

**Last Updated**: November 2025
**Django Version**: 5.2.7
**Python Version**: 3.8+

