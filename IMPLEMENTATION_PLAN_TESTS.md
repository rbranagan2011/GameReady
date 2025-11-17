# Implementation Plan: Test Coverage (Critical Issue #2)

## Overview
Add comprehensive test coverage for critical user flows and functionality. Target: Minimum 60% code coverage for critical paths.

## Current State
- ✅ 1 test file (`core/tests.py`)
- ✅ Tests for PlayerStatus functionality (3 tests)
- ❌ No tests for critical user flows
- ❌ No tests for authorization
- ❌ No tests for rate limiting
- ❌ No tests for email verification
- ❌ No tests for report submission

## Test Categories to Implement

### 1. User Registration & Email Verification (HIGH PRIORITY)
**Test Cases:**
- Role selection flow
- User signup with valid data
- User signup with invalid data
- Email verification token creation
- Email verification success
- Email verification with expired token
- Email verification with invalid token
- Resend verification email
- User cannot login before email verification

### 2. Authentication & Authorization (HIGH PRIORITY)
**Test Cases:**
- Login with valid credentials
- Login with invalid credentials
- Login with unverified email
- Logout functionality
- Athlete cannot access coach dashboard
- Coach cannot access athlete dashboard
- Unauthenticated users redirected to login
- Profile creation on user creation (signal)

### 3. Readiness Report Submission (HIGH PRIORITY)
**Test Cases:**
- Submit report with valid data
- Submit report with invalid data
- Cannot submit duplicate report for same day
- Readiness score calculation
- Redirect after submission
- Report requires authentication
- Report requires athlete role

### 4. Coach Dashboard (MEDIUM PRIORITY)
**Test Cases:**
- Coach can access dashboard
- Dashboard shows team athletes
- Dashboard shows reports for selected date
- Dashboard calculates team averages
- Dashboard requires coach role
- Dashboard handles no team scenario

### 5. Player Dashboard (MEDIUM PRIORITY)
**Test Cases:**
- Athlete can access dashboard
- Dashboard shows today's report if exists
- Dashboard redirects to submit if no report
- Dashboard shows weekly data
- Dashboard requires athlete role

### 6. Team Management (MEDIUM PRIORITY)
**Test Cases:**
- Coach can create team
- Coach can update team name
- Coach can upload team logo
- Team join code generation
- Athlete can join team with code
- Team switching for coaches

### 7. Rate Limiting (MEDIUM PRIORITY)
**Test Cases:**
- Login rate limiting (5/m)
- Signup rate limiting (3/h)
- Password reset rate limiting (3/h)
- Email verification resend rate limiting (3/h)

### 8. File Upload Security (LOW PRIORITY)
**Test Cases:**
- Valid image upload
- File size validation
- File type validation
- Image dimension validation

## Implementation Strategy

### Phase 1: Critical User Flows (Week 1)
1. User registration & email verification
2. Authentication & authorization
3. Readiness report submission

### Phase 2: Dashboard & Team Management (Week 2)
4. Coach dashboard
5. Player dashboard
6. Team management

### Phase 3: Security & Edge Cases (Week 3)
7. Rate limiting
8. File upload security
9. Edge cases and error handling

## Test File Structure

```
core/
├── tests/
│   ├── __init__.py
│   ├── test_authentication.py      # Login, logout, auth
│   ├── test_registration.py        # Signup, email verification
│   ├── test_readiness_reports.py   # Report submission
│   ├── test_dashboards.py          # Coach & player dashboards
│   ├── test_team_management.py     # Teams, join codes
│   ├── test_authorization.py       # Role-based access
│   ├── test_rate_limiting.py       # Rate limit tests
│   └── test_file_uploads.py        # File upload security
```

## Test Utilities

Create helper functions for:
- Creating test users (athlete, coach)
- Creating test teams
- Creating test reports
- Mocking email sending

## Coverage Goals

- **Critical paths**: 80%+ coverage
- **Overall**: 60%+ coverage
- **Views**: 70%+ coverage
- **Models**: 80%+ coverage
- **Forms**: 70%+ coverage

## Tools Needed

- `coverage` package for coverage reporting
- Django's test client
- Mock for email testing

## Next Steps

1. ✅ Create this plan
2. ⏳ Set up test structure
3. ⏳ Create test utilities/helpers
4. ⏳ Implement Phase 1 tests
5. ⏳ Implement Phase 2 tests
6. ⏳ Implement Phase 3 tests
7. ⏳ Run coverage report
8. ⏳ Document test results

