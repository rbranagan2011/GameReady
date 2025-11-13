# PostHog Analytics Setup Guide

PostHog has been integrated into GameReady to track user behavior and app popularity.

## Setup Instructions

### 1. Create a PostHog Account

1. Go to [https://posthog.com](https://posthog.com)
2. Sign up for a free account (generous free tier)
3. Create a new project for GameReady

### 2. Get Your API Key

1. In PostHog, go to **Project Settings** → **Project API Key**
2. Copy your **Project API Key** (starts with `phc_`)

### 3. Configure Environment Variables

#### For Local Development:
Add to your `.env` file:
```
POSTHOG_API_KEY=phc_your_api_key_here
POSTHOG_HOST=https://app.posthog.com
```

#### For Production (Render):
1. Go to your Render dashboard
2. Navigate to your service → **Environment**
3. Add environment variables:
   - `POSTHOG_API_KEY` = `phc_your_api_key_here`
   - `POSTHOG_HOST` = `https://app.posthog.com`

### 4. Restart Your Server

After adding the environment variables, restart your server:
- **Local**: Stop and restart `python manage.py runserver`
- **Production**: Render will automatically redeploy

## What's Being Tracked

PostHog automatically tracks:

### User Events:
- **user_signed_up** - When a new user creates an account
- **email_verified** - When a user verifies their email
- **user_logged_in** - When a user logs in
- **report_submitted** - When an athlete submits a daily readiness report
- **team_created** - When a coach creates a new team
- **team_joined** - When a user joins a team

### Automatic Tracking:
- Page views (all pages)
- User identification (links events to user profiles)
- User properties (email, username, role)

## Viewing Analytics

1. Log into your PostHog dashboard
2. Go to **Insights** to see:
   - Daily Active Users (DAU)
   - Weekly Active Users (WAU)
   - Monthly Active Users (MAU)
   - User retention
   - Event trends
   - Funnel analysis

## Key Metrics to Monitor

### Popularity Metrics:
- **Daily Active Users**: Users who submit reports or log in daily
- **New Signups**: Track `user_signed_up` events
- **User Retention**: See how many users come back after signing up

### Engagement Metrics:
- **Report Submission Rate**: Track `report_submitted` events
- **Team Creation**: Track `team_created` events
- **Login Frequency**: Track `user_logged_in` events

## Cost Management

PostHog's free tier includes:
- 1 million events per month
- Unlimited users
- 1 year of data retention

To manage costs:
1. Set up a monthly budget alert in PostHog
2. Monitor event volume in the dashboard
3. If needed, you can sample events (only track a percentage)

## Troubleshooting

### PostHog not tracking?
1. Check that `POSTHOG_API_KEY` is set in environment variables
2. Check browser console for JavaScript errors
3. Verify the API key is correct in PostHog dashboard
4. Check that PostHog is enabled: `POSTHOG_ENABLED` should be `True` when API key is set

### Events not showing up?
- Events may take a few seconds to appear in PostHog
- Check the PostHog dashboard → **Live Events** to see real-time events
- Verify the event names match what you're looking for

## Privacy

PostHog is privacy-friendly:
- GDPR compliant
- Data is stored securely
- Users can request data deletion
- No cookies required for basic tracking

