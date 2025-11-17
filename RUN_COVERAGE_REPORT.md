# Running Test Coverage Report

## Quick Start

### 1. Install Coverage (if not already installed)
```bash
pip install coverage
```

### 2. Run Tests with Coverage
```bash
# Run all tests with coverage
coverage run --source='.' manage.py test core.tests

# Or run specific test files
coverage run --source='.' manage.py test core.tests.test_registration
coverage run --source='.' manage.py test core.tests.test_authentication
coverage run --source='.' manage.py test core.tests.test_readiness_reports
coverage run --source='.' manage.py test core.tests.test_authorization
coverage run --source='.' manage.py test core.tests.test_dashboards
coverage run --source='.' manage.py test core.tests.test_team_management
coverage run --source='.' manage.py test core.tests.test_rate_limiting
```

### 3. Generate Coverage Report

**Terminal Report:**
```bash
coverage report
```

**HTML Report (Recommended):**
```bash
coverage html
# Then open htmlcov/index.html in your browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 4. View Detailed Coverage

The HTML report shows:
- Line-by-line coverage
- Files with low coverage
- Missing branches
- Overall coverage percentage

## Coverage Targets

- **Overall**: 60%+ coverage
- **Critical Paths**: 80%+ coverage
  - User registration & email verification
  - Authentication
  - Readiness report submission
  - Authorization checks
- **Views**: 70%+ coverage
- **Models**: 80%+ coverage
- **Forms**: 70%+ coverage

## Interpreting Results

### Good Coverage
- ✅ 60%+ overall coverage
- ✅ 80%+ on critical user flows
- ✅ All critical paths tested

### Areas Needing More Coverage
- Views with < 50% coverage
- Models with missing edge cases
- Error handling paths
- Edge cases and boundary conditions

## Excluding Files from Coverage

If needed, create `.coveragerc` file:
```ini
[run]
omit =
    */migrations/*
    */venv/*
    */tests/*
    manage.py
    */settings/*
```

## Continuous Integration

For CI/CD, add to your pipeline:
```yaml
# Example GitHub Actions
- name: Run tests with coverage
  run: |
    coverage run --source='.' manage.py test core.tests
    coverage report
    coverage xml  # For coverage reporting services
```

## Next Steps After Coverage Report

1. **Identify gaps** - Find untested code paths
2. **Add missing tests** - Focus on critical paths first
3. **Improve edge cases** - Test error conditions
4. **Document findings** - Note areas with low coverage

---

**Status**: Ready to run coverage report  
**Expected Coverage**: 60%+ overall, 80%+ on critical paths

