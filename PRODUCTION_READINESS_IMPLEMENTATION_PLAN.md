# Production Readiness Implementation Plan

This document outlines the step-by-step plan to implement the 5 critical production readiness features.

---

## Overview

**5 Critical Items to Implement:**
1. ✅ Password Reset (Forgot Password)
2. ✅ Custom Error Pages (404, 500)
3. ✅ Legal Pages (Privacy Policy & Terms of Service)
4. ✅ Admin Email Configuration
5. ✅ Rate Limiting / Brute Force Protection

**Estimated Time**: 1-2 days of focused work

---

## 1. Password Reset (Forgot Password)

### Current State
- Users can change password when logged in (`account_management` view)
- No password reset flow for forgotten passwords
- Django's built-in password reset views are not configured

### Implementation Steps

#### Step 1.1: Add Password Reset URLs
**File**: `GameReady/urls.py`
- Add Django's password reset URL patterns
- Include: password_reset, password_reset_done, password_reset_confirm, password_reset_complete

#### Step 1.2: Create Password Reset Templates
**Files to Create**:
- `templates/registration/password_reset_form.html` - Request reset form
- `templates/registration/password_reset_done.html` - Confirmation after request
- `templates/registration/password_reset_confirm.html` - Set new password form
- `templates/registration/password_reset_complete.html` - Success confirmation

#### Step 1.3: Customize Password Reset View (Optional)
**File**: `core/views.py` (if needed)
- Create custom `PasswordResetView` to integrate with email system
- Use existing `email_utils.py` for consistent email sending
- Handle inactive users (unverified emails)

#### Step 1.4: Add "Forgot Password?" Link to Login Page
**File**: `templates/registration/login.html`
- Add link below login form
- Style to match existing design

#### Step 1.5: Configure Password Reset Settings
**File**: `GameReady/settings/base.py`
- Set `PASSWORD_RESET_TIMEOUT` (default 3 days is fine)
- Ensure email backend is configured (already done)

### Testing Checklist
- [ ] Can request password reset from login page
- [ ] Email is sent with reset link
- [ ] Reset link works and allows setting new password
- [ ] Reset link expires after timeout
- [ ] Inactive users are handled appropriately
- [ ] Success messages follow NO_SUCCESS_MESSAGES_RULE (hide success, show errors)

---

## 2. Custom Error Pages (404, 500)

### Current State
- No custom error page templates
- Users see generic Django error pages in production

### Implementation Steps

#### Step 2.1: Create Error Page Templates
**Files to Create**:
- `templates/404.html` - Page not found
- `templates/500.html` - Server error
- `templates/403.html` - Permission denied (optional but good to have)

#### Step 2.2: Design Error Pages
- Match existing design (Bootstrap 5, same styling as base.html)
- Include helpful messages
- Add navigation back to home/login
- Make them mobile-friendly

#### Step 2.3: Configure Error Handlers (if needed)
**File**: `GameReady/urls.py`
- Add handler404, handler500, handler403 if custom views needed
- Django will automatically use templates if they exist

#### Step 2.4: Test Error Pages
- Test 404 by visiting non-existent URL
- Test 500 by temporarily causing an error (in development)
- Ensure pages render correctly

### Testing Checklist
- [ ] 404 page displays for non-existent URLs
- [ ] 500 page displays for server errors (test in dev)
- [ ] Error pages match app design
- [ ] Error pages are mobile-responsive
- [ ] Navigation works from error pages

---

## 3. Legal Pages (Privacy Policy & Terms of Service)

### Current State
- No legal pages exist
- Required for GDPR compliance and general legal protection

### Implementation Steps

#### Step 3.1: Create Legal Page Views
**File**: `core/views.py`
- Add `privacy_policy` view (simple render)
- Add `terms_of_service` view (simple render)
- Both should be accessible without login

#### Step 3.2: Create Legal Page Templates
**Files to Create**:
- `templates/core/privacy_policy.html`
- `templates/core/terms_of_service.html`

#### Step 3.3: Add Legal Page URLs
**File**: `core/urls.py`
- Add routes: `/privacy-policy/` and `/terms-of-service/`

#### Step 3.4: Write Legal Content
**Content to Include**:

**Privacy Policy:**
- What data is collected (wellness metrics, email, name)
- How data is used (coach dashboards, team management)
- Data sharing (coaches can see athlete data, team members)
- Data retention
- User rights (access, deletion, export)
- Cookies/sessions
- Contact information

**Terms of Service:**
- Service description
- User responsibilities
- Account rules
- Prohibited uses
- Limitation of liability
- Changes to terms
- Contact information

#### Step 3.5: Add Legal Links to Footer
**File**: `templates/base.html`
- Add links to Privacy Policy and Terms in footer
- Also add to signup page (required for compliance)

#### Step 3.6: Add Legal Checkbox to Signup
**File**: `templates/core/signup.html`
- Add checkbox: "I agree to the Terms of Service and Privacy Policy"
- Make it required
- Link to both pages

### Testing Checklist
- [ ] Privacy Policy page accessible and renders
- [ ] Terms of Service page accessible and renders
- [ ] Links in footer work
- [ ] Signup requires accepting terms
- [ ] Legal pages are mobile-responsive
- [ ] Content is clear and comprehensive

---

## 4. Admin Email Configuration

### Current State
- `ADMINS` setting not configured
- No error email notifications sent to admins

### Implementation Steps

#### Step 4.1: Add ADMINS Setting
**File**: `GameReady/settings/production.py`
- Add `ADMINS` list with admin email(s)
- Format: `[('Admin Name', 'admin@example.com')]`
- Read from environment variable for flexibility

#### Step 4.2: Configure Error Email Settings
**File**: `GameReady/settings/production.py`
- Ensure `SERVER_EMAIL` is set (use DEFAULT_FROM_EMAIL)
- Verify email backend is configured (already done)

#### Step 4.3: Test Error Emails (Optional)
- Temporarily cause a 500 error in production
- Verify admin receives error email
- Remove test error

### Testing Checklist
- [ ] ADMINS setting is configured
- [ ] Error emails are sent when 500 errors occur
- [ ] Admin email address is correct
- [ ] Email configuration works (uses existing SendGrid setup)

---

## 5. Rate Limiting / Brute Force Protection

### Current State
- No rate limiting on login, signup, or password reset
- Vulnerable to brute force attacks

### Implementation Steps

#### Step 5.1: Install django-ratelimit
**File**: `requirements.txt`
- Add `django-ratelimit==4.1.0` (or latest version)

#### Step 5.2: Add Rate Limiting Middleware
**File**: `GameReady/settings/base.py`
- Add `django_ratelimit` to `INSTALLED_APPS`
- Configure rate limit settings

#### Step 5.3: Add Rate Limiting to Login View
**File**: `core/views.py`
- Import `ratelimit` decorator
- Add `@ratelimit(key='ip', rate='5/m', method='POST')` to `CustomLoginView`
- Show user-friendly error message when rate limited

#### Step 5.4: Add Rate Limiting to Signup View
**File**: `core/views.py`
- Add rate limiting to `signup` view
- Rate: 3 signups per hour per IP (prevent spam accounts)

#### Step 5.5: Add Rate Limiting to Password Reset
**File**: `GameReady/urls.py` or custom view
- Rate limit password reset requests
- Rate: 3 requests per hour per IP

#### Step 5.6: Add Rate Limiting to Email Verification Resend
**File**: `core/views.py`
- Rate limit `resend_verification_email` view
- Rate: 3 requests per hour per user

#### Step 5.7: Create Rate Limit Error Template (Optional)
**File**: `templates/core/rate_limit_exceeded.html`
- User-friendly message when rate limited
- Explain why and when they can try again

### Testing Checklist
- [ ] Login rate limiting works (try 6+ login attempts)
- [ ] Signup rate limiting works (try 4+ signups)
- [ ] Password reset rate limiting works
- [ ] Error messages are user-friendly
- [ ] Rate limits reset after time period
- [ ] Legitimate users aren't blocked (limits are reasonable)

---

## Implementation Order

**Recommended Order:**
1. **Admin Email Configuration** (5 minutes) - Quick win
2. **Custom Error Pages** (1-2 hours) - Visual improvement
3. **Legal Pages** (2-3 hours) - Compliance requirement
4. **Password Reset** (2-3 hours) - User-facing feature
5. **Rate Limiting** (1-2 hours) - Security hardening

**Total Estimated Time**: 6-10 hours

---

## Files to Create/Modify

### New Files to Create:
```
templates/
  ├── 404.html
  ├── 500.html
  ├── 403.html (optional)
  └── registration/
      ├── password_reset_form.html
      ├── password_reset_done.html
      ├── password_reset_confirm.html
      └── password_reset_complete.html
  └── core/
      ├── privacy_policy.html
      ├── terms_of_service.html
      └── rate_limit_exceeded.html (optional)
```

### Files to Modify:
```
GameReady/
  ├── urls.py (add password reset URLs, error handlers)
  └── settings/
      ├── base.py (add rate limiting config)
      └── production.py (add ADMINS setting)

core/
  ├── urls.py (add legal page URLs)
  ├── views.py (add legal views, rate limiting decorators)
  └── forms.py (add terms acceptance to signup form)

templates/
  ├── base.html (add legal links to footer)
  ├── registration/login.html (add forgot password link)
  └── core/signup.html (add terms acceptance checkbox)

requirements.txt (add django-ratelimit)
```

---

## Testing Strategy

### Manual Testing
1. Test each feature individually
2. Test on mobile devices
3. Test error scenarios
4. Verify email delivery

### Production Testing
1. Deploy to staging first (if available)
2. Test password reset with real email
3. Verify error pages in production
4. Monitor rate limiting behavior

---

## Notes

- **NO_SUCCESS_MESSAGES_RULE**: Remember to hide success messages, only show errors
- **Email System**: Use existing `email_utils.py` for consistency
- **Design Consistency**: Match existing Bootstrap 5 styling
- **Mobile-First**: Ensure all new pages are mobile-responsive
- **Security**: Rate limits should be reasonable (not too strict, not too lenient)

---

## Post-Implementation Checklist

- [ ] All 5 features implemented
- [ ] All tests passing
- [ ] Legal pages linked from signup and footer
- [ ] Password reset works end-to-end
- [ ] Error pages display correctly
- [ ] Admin receives error emails
- [ ] Rate limiting prevents abuse
- [ ] Documentation updated (if needed)
- [ ] Deployed to production
- [ ] Production testing completed

---

**Ready to start?** Begin with Admin Email Configuration for a quick win, then proceed through the list in order.

