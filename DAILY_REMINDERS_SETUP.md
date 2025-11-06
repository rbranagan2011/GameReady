# Daily Reminder Email Setup

This document explains how to set up daily reminder emails that send to athletes at 12pm in their local timezone.

## Overview

The system sends daily reminder emails to athletes who haven't submitted their readiness report for the day. Emails are sent at 12pm local time for each athlete based on their timezone setting.

## How It Works

1. **Timezone-Aware Scheduling**: Each athlete's Profile has a `timezone` field (defaults to UTC)
2. **Time Window**: The command runs periodically and checks if it's 12pm (±15 minutes) in each athlete's local timezone
3. **Smart Filtering**: Only sends reminders to athletes who:
   - Are active
   - Have a team assigned
   - Haven't submitted a report today
   - Are within the 12pm time window in their timezone

## Setting Up Athlete Timezones

### Via Django Admin

1. Go to `/admin/core/profile/`
2. Edit an athlete's profile
3. Set the `Timezone` field (e.g., `America/New_York`, `Europe/London`, `Australia/Sydney`)
4. Save

### Common Timezone Examples

- `America/New_York` - Eastern Time (US)
- `America/Chicago` - Central Time (US)
- `America/Denver` - Mountain Time (US)
- `America/Los_Angeles` - Pacific Time (US)
- `Europe/London` - UK Time
- `Europe/Paris` - Central European Time
- `Australia/Sydney` - Australian Eastern Time
- `Asia/Tokyo` - Japan Standard Time
- `UTC` - Coordinated Universal Time

Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

## Testing the Command

### Dry Run (Recommended First)

Test without sending emails:

```bash
python manage.py send_daily_reminders --dry-run --verbosity 2
```

This shows:
- Which athletes would receive reminders
- Which athletes are skipped (already submitted or outside time window)
- Local time for each athlete

### Actual Run

Send real emails:

```bash
python manage.py send_daily_reminders
```

### Custom Time Window

Adjust the time window (default is 15 minutes):

```bash
# Send reminders if it's between 11:45 AM and 12:15 PM
python manage.py send_daily_reminders --time-window 15

# Send reminders if it's between 11:30 AM and 12:30 PM
python manage.py send_daily_reminders --time-window 30
```

## Setting Up Cron Job

To run reminders automatically, set up a cron job that runs every 15-30 minutes.

### Option 1: Run Every 15 Minutes (Recommended)

This ensures reminders are sent promptly at 12pm for each timezone.

Create a script: `/var/www/gameready/send_reminders.sh`

```bash
#!/bin/bash
# Daily reminder email script for GameReady

cd /var/www/gameready  # Change to your project directory
source venv/bin/activate
python manage.py send_daily_reminders
deactivate
```

Make it executable:
```bash
chmod +x /var/www/gameready/send_reminders.sh
```

Add to crontab (run `crontab -e`):
```bash
# Run every 15 minutes to catch 12pm in all timezones
*/15 * * * * /var/www/gameready/send_reminders.sh >> /var/www/gameready/logs/reminders.log 2>&1
```

### Option 2: Run Every Hour

If you want to run less frequently, you can run every hour:

```bash
# Run at the top of every hour
0 * * * * /var/www/gameready/send_reminders.sh >> /var/www/gameready/logs/reminders.log 2>&1
```

**Note**: With hourly runs, reminders might be sent slightly after 12pm (up to 59 minutes late) depending on when the cron job runs.

### Logging

Logs are written to `/var/www/gameready/logs/reminders.log`. Make sure the logs directory exists:

```bash
mkdir -p /var/www/gameready/logs
```

## How Timezone Detection Works

1. The command runs periodically (via cron)
2. For each athlete:
   - Gets their timezone from their Profile
   - Converts current UTC time to their local timezone
   - Checks if it's between 11:45 AM and 12:15 PM (configurable)
   - If yes, and they haven't submitted today, sends reminder
   - If no, skips them

## Troubleshooting

### Reminders Not Being Sent

1. **Check athlete timezones**: Ensure athletes have valid timezone strings
2. **Check cron job**: Verify the cron job is running
   ```bash
   tail -f /var/www/gameready/logs/reminders.log
   ```
3. **Test manually**: Run the command manually to see what's happening
4. **Check email settings**: Ensure EMAIL_BACKEND and SMTP settings are configured correctly

### Timezone Issues

If you see warnings about invalid timezones:
- The system will default to UTC
- Update the athlete's profile with a valid timezone string
- Common issue: Using abbreviations (like "EST") instead of full names (like "America/New_York")

### Email Delivery Issues

- Check Django email settings in `settings/production.py`
- Verify SMTP credentials are correct
- Check spam folders
- Review email logs in Django

## Command Options

- `--dry-run`: Run without sending emails (for testing)
- `--time-window N`: Time window in minutes around 12pm (default: 15)
- `--verbosity 0|1|2`: Output verbosity level

## Example Output

```
==================================================
Daily Reminder Summary
==================================================
Reminders sent: 5
Reminders skipped (already submitted): 3
Reminders skipped (outside time window): 2
==================================================
```

