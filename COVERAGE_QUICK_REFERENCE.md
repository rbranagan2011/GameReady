# Test Coverage Quick Reference

## Current Status

```
Overall Coverage: 39% → Target: 60% (Gap: 21%)
Total Tests: 94 → Target: 150+ (Gap: 60+)
```

## Coverage by Component

| Component | Current | Target | Status | Priority |
|-----------|---------|--------|--------|----------|
| **Critical Flows** | 80%+ | 90%+ | ✅ Good | Maintain |
| **Views** | 26% | 50% | ❌ **Critical** | **Fix Now** |
| **Forms** | 46% | 70% | ⚠️ Needs Work | High |
| **Email Utils** | 19% | 60% | ❌ **Critical** | High |
| **Models** | 68% | 80% | ⚠️ Good | Medium |
| **Overall** | 39% | 60% | ❌ **Critical** | **Fix Now** |

## Quick Wins (Do First)

### 1. Fix Bleach API (1 hour) → Fixes 24 error tests
```python
# core/sanitization.py
# Change: bleach.utils.decode_entities(text)
# To: html.unescape(text) or use bleach.clean() properly
```

### 2. Add Form Tests (4 hours) → +8% coverage
- Create `core/tests/test_forms.py`
- Test validation logic
- Test edge cases

### 3. Add Email Tests (3 hours) → +8% coverage
- Create `core/tests/test_email_utils.py`
- Test email sending
- Test error handling

### 4. Add AJAX Tests (6 hours) → +5% coverage
- Create `core/tests/test_ajax_endpoints.py`
- Test frequently used endpoints

## Priority Order

### Week 1: Foundation
1. ✅ Fix bleach API
2. ✅ Fix failing tests
3. ✅ Add form tests
4. ✅ Add email utility tests
**Result**: 50% coverage

### Week 2: Critical Views
1. ✅ Add AJAX endpoint tests
2. ✅ Enhance dashboard tests
3. ✅ Enhance team management tests
4. ✅ Add player status tests
**Result**: 60% coverage

### Week 3: Edge Cases
1. ✅ Add error handling tests
2. ✅ Add edge case tests
3. ✅ Add integration tests
**Result**: 65% coverage

## Test Files to Create

```
core/tests/
├── test_forms.py              ⏳ NEW - Forms validation
├── test_email_utils.py        ⏳ NEW - Email functions
├── test_ajax_endpoints.py     ⏳ NEW - AJAX views
├── test_player_status.py      ⏳ NEW - Status management
├── test_feature_requests.py   ⏳ NEW - Feature requests
├── test_sanitization.py       ⏳ NEW - Security functions
└── test_error_handling.py     ⏳ NEW - Error paths
```

## Why Coverage Matters

✅ **Reduces Bugs** - Catch issues before users do  
✅ **Enables Refactoring** - Safe code improvements  
✅ **Faster Development** - Automated regression testing  
✅ **Better Documentation** - Tests show how code works  
✅ **Production Ready** - Industry standard 60-80%

## Success Metrics

- ✅ **0 failing tests** (Currently: 9 failing, 24 errors)
- ✅ **60%+ overall coverage** (Currently: 39%)
- ✅ **50%+ views coverage** (Currently: 26%)
- ✅ **90%+ critical flows** (Currently: 80%+)

## Commands

```bash
# Run all tests
python manage.py test core.tests

# Run with coverage
coverage run --source='.' manage.py test core.tests
coverage report
coverage html

# Run specific test file
python manage.py test core.tests.test_forms

# Run specific test
python manage.py test core.tests.test_forms.TestFormValidation.test_readiness_report_form
```

---

**Next Action**: Fix bleach API → Add form tests → Add email tests  
**Timeline**: 3 weeks to 60% coverage  
**Priority**: Views (26%) → Forms (46%) → Email (19%)

