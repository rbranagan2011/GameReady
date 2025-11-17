# GameReady Monitoring and Alerting Setup Guide

This document describes the monitoring and alerting setup for GameReady production deployment.

---

## Overview

GameReady uses a multi-layered monitoring approach:

1. **Application Performance Monitoring (APM)** - Sentry for error tracking and performance
2. **Uptime Monitoring** - External service (UptimeRobot recommended)
3. **Database Monitoring** - Render.com dashboard + Sentry
4. **Email Alerts** - Django's built-in admin email notifications

---

## 1. Sentry Setup (Application Performance Monitoring)

Sentry provides:
- **Error tracking** - Automatic error capture with stack traces
- **Performance monitoring** - Track slow queries and endpoints
- **Release tracking** - Monitor errors by deployment
- **Alerting** - Email/Slack notifications for errors

### Step 1: Create Sentry Account

1. Go to https://sentry.io and sign up (free tier available)
2. Create a new project:
   - Platform: **Django**
   - Project name: **GameReady**
3. Copy your **DSN** (Data Source Name) from the project settings

### Step 2: Configure Environment Variables

Add these environment variables in Render.com dashboard:

```bash
# Required: Your Sentry DSN
SENTRY_DSN=https://your-key@sentry.io/your-project-id

# Optional: Environment name (defaults to 'production')
SENTRY_ENVIRONMENT=production

# Optional: Performance sampling rate (0.0 to 1.0)
# 0.1 = 10% of transactions, 1.0 = 100%
# Lower values reduce overhead but provide less data
SENTRY_TRACES_SAMPLE_RATE=0.1

# Optional: Performance profiling sampling rate
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

### Step 3: Verify Installation

After deploying with Sentry configured:

1. Check Render logs for: `"Sentry error tracking and performance monitoring enabled"`
2. Visit Sentry dashboard - you should see your project
3. Trigger a test error (optional) to verify error capture

### Step 4: Configure Sentry Alerts

In Sentry dashboard:

1. Go to **Alerts** → **Create Alert Rule**
2. Recommended alerts:
   - **New Issues** - Alert when new error types appear
   - **High Error Rate** - Alert if errors exceed threshold (e.g., 10 errors/minute)
   - **Slow Performance** - Alert if p95 response time > 2 seconds
   - **Database Slow Queries** - Alert if query time > 1 second

3. Configure notification channels:
   - Email notifications (default)
   - Slack integration (optional)
   - PagerDuty (optional, for critical alerts)

### Step 5: Set Up Release Tracking

Sentry automatically tracks releases using Render's `RENDER_GIT_COMMIT` environment variable.

To manually set a release:
```bash
SENTRY_RELEASE=your-release-version
```

---

## 2. Uptime Monitoring Setup

Uptime monitoring checks if your application is accessible and responding.

### Recommended: UptimeRobot (Free Tier Available)

1. **Sign up**: https://uptimerobot.com
2. **Create Monitor**:
   - Monitor Type: **HTTP(s)**
   - Friendly Name: `GameReady Production`
   - URL: `https://start.gamereadyapp.com`
   - Monitoring Interval: **5 minutes** (free tier)
   - Alert Contacts: Add your email

3. **Configure Alerts**:
   - Alert when down: ✅
   - Alert when up: ✅ (optional, for confirmation)
   - Alert after: **1 consecutive failure**

### Alternative: Pingdom, StatusCake, or Better Uptime

Similar setup process - configure HTTP monitoring for your production URL.

---

## 3. Database Performance Monitoring

### Render.com Dashboard

Render provides basic database metrics:
- Connection count
- Query performance
- Database size

Access via: Render Dashboard → Your Database Service → Metrics

### Sentry Database Monitoring

Sentry automatically tracks:
- Slow database queries (> 1 second by default)
- Database connection errors
- Query performance trends

View in Sentry: **Performance** → **Database** tab

### Recommended: Set Up Database Alerts

In Sentry, create alerts for:
- **Database Connection Errors** - Alert immediately
- **Slow Queries** - Alert if queries > 1 second
- **High Query Volume** - Alert if unusual spike

---

## 4. Email Alert Configuration

Django's built-in admin email notifications are already configured.

### Configure Admin Emails

Set `ADMINS` environment variable in Render:

```bash
# Single admin
ADMINS="Your Name,admin@example.com"

# Multiple admins (semicolon-separated)
ADMINS="Admin One,admin1@example.com;Admin Two,admin2@example.com"
```

### What Gets Emailed

- **500 errors** - Server errors with full traceback
- **404 errors** - Not found errors (if DEBUG=False)
- **Critical system errors** - Database connection failures, etc.

---

## 5. Monitoring Checklist

Before launch, verify:

- [ ] Sentry DSN configured and working
- [ ] Sentry alerts configured (new issues, high error rate)
- [ ] Uptime monitoring active (UptimeRobot or similar)
- [ ] Admin email notifications configured (`ADMINS` set)
- [ ] Test error capture (trigger test error, verify in Sentry)
- [ ] Test uptime alert (temporarily block URL, verify alert)
- [ ] Database monitoring visible in Sentry
- [ ] Performance monitoring showing data in Sentry

---

## 6. Monitoring Best Practices

### Error Monitoring

- **Review Sentry daily** - Check for new errors
- **Triage errors** - Fix critical errors immediately
- **Ignore noise** - Configure filters for known non-critical errors
- **Track trends** - Monitor error rate over time

### Performance Monitoring

- **Set baselines** - Know your normal response times
- **Track slow endpoints** - Optimize endpoints with p95 > 1 second
- **Monitor database** - Watch for slow queries
- **Review releases** - Compare performance before/after deployments

### Uptime Monitoring

- **Multiple monitors** - Monitor both main domain and API endpoints
- **Alert contacts** - Add multiple team members
- **Response time tracking** - Monitor not just uptime but response speed

---

## 7. Troubleshooting

### Sentry Not Capturing Errors

1. Check `SENTRY_DSN` is set correctly
2. Verify Sentry SDK is installed: `pip list | grep sentry`
3. Check Render logs for Sentry initialization messages
4. Test with: `raise Exception("Test error")` in a view

### Uptime Monitor False Positives

- Check if your site requires authentication (may need to monitor public endpoint)
- Verify monitor URL is correct
- Check if site is actually down or just slow

### Email Alerts Not Working

1. Verify `ADMINS` environment variable is set
2. Check email configuration (`EMAIL_HOST`, `EMAIL_HOST_PASSWORD`)
3. Check spam folder
4. Test with: `logger.error("Test error")` in a view

---

## 8. Cost Considerations

### Free Tiers

- **Sentry**: 5,000 events/month (free tier)
- **UptimeRobot**: 50 monitors, 5-minute intervals (free tier)
- **Render**: Basic metrics included

### Scaling Considerations

- If exceeding Sentry free tier, consider:
  - Reducing `SENTRY_TRACES_SAMPLE_RATE` to 0.05 (5%)
  - Filtering out non-critical errors
  - Upgrading to paid tier if needed

---

## 9. Additional Resources

- [Sentry Django Documentation](https://docs.sentry.io/platforms/python/guides/django/)
- [UptimeRobot Documentation](https://uptimerobot.com/api/)
- [Django Logging Documentation](https://docs.djangoproject.com/en/5.2/topics/logging/)

---

**Last Updated**: November 2025  
**Status**: ✅ Monitoring setup complete - ready for configuration

