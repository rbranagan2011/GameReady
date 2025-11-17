# Implementation Plan: Database Indexes (Critical Issue #1)

## Overview
Add database indexes to improve query performance as data grows. This is the first critical issue from the pre-launch audit.

## Analysis of Query Patterns

### ReadinessReport Model
**Current queries:**
- `filter(athlete=user, date_created=today)` - Check if report exists today
- `filter(athlete=user, date_created__gte=start, date_created__lte=end)` - Date range queries
- `filter(athlete__in=team_athletes, date_created=selected_date)` - Team reports for specific date
- `filter(athlete__in=team_athletes, date_created__gte=week_ago, date_created__lte=selected_date)` - Date ranges
- `order_by('-date_created')` - Most recent first (Meta.ordering)
- Unique constraint: `('athlete', 'date_created')` - Django creates index automatically

**Indexes needed:**
1. Composite index: `['athlete', 'date_created']` - For athlete-specific date queries
2. Single index: `['date_created']` - For date range queries and ordering
3. Note: ForeignKey on `athlete` already has implicit index ✅

### PlayerPersonalLabel Model
**Current queries:**
- `filter(athlete=user, date__gte=month_start, date__lte=month_end)` - Monthly labels
- Unique constraint: `('athlete', 'date')` - Django creates index automatically

**Indexes needed:**
1. Composite index: `['athlete', 'date']` - For athlete-specific date queries (may already exist from unique_together)

### Profile Model
**Current queries:**
- `filter(role=Profile.Role.ATHLETE)` - Filter by role
- `filter(role=Profile.Role.COACH)` - Filter by role
- `filter(team=coach_team)` - Filter by team (ForeignKey has index ✅)
- `filter(teams=team)` - ManyToMany (handled by Django ✅)

**Indexes needed:**
1. Index: `['role']` - For filtering athletes/coaches

### FeatureRequest Model
**Current queries:**
- `order_by('-created_at')` - Most recent first (Meta.ordering)
- `filter(request_type='FEATURE')` or `filter(request_type='BUG')` - Filter by type
- `order_by('created_at')` - Oldest first

**Indexes needed:**
1. Index: `['created_at']` - For ordering
2. Index: `['request_type']` - For filtering by type

### EmailVerification Model
**Current queries:**
- `filter(token=token)` - Token lookup (already has `db_index=True` ✅)
- Potential cleanup: `filter(expires_at__lt=now)` - Find expired tokens

**Indexes needed:**
1. Index: `['expires_at']` - For cleanup queries (optional but recommended)

### TeamTag Model
**Current queries:**
- `filter(team=team, id=tag_id)` - Get tag by team and ID
- Unique constraint: `('team', 'name')` - Django creates index automatically ✅

**Indexes needed:**
- None additional (ForeignKey and unique_together handle it)

### TeamSchedule Model
**Current queries:**
- `get(team=team)` - OneToOne lookup (Django creates index automatically ✅)

**Indexes needed:**
- None additional

## Implementation Steps

### Step 1: Update Models with Indexes
Add `Meta.indexes` to each model that needs indexes.

### Step 2: Create Migration
Generate Django migration for the new indexes.

### Step 3: Test Migration
- Test on development database
- Verify indexes are created correctly
- Test query performance improvement

### Step 4: Review Existing Indexes
- Verify ForeignKey indexes exist (they should automatically)
- Verify unique_together indexes exist (they should automatically)

## Indexes to Add

```python
# ReadinessReport
indexes = [
    models.Index(fields=['athlete', 'date_created'], name='readinessreport_athlete_date_idx'),
    models.Index(fields=['date_created'], name='readinessreport_date_idx'),
]

# PlayerPersonalLabel
indexes = [
    models.Index(fields=['athlete', 'date'], name='playerpersonallabel_athlete_date_idx'),
]

# Profile
indexes = [
    models.Index(fields=['role'], name='profile_role_idx'),
]

# FeatureRequest
indexes = [
    models.Index(fields=['created_at'], name='featurerequest_created_idx'),
    models.Index(fields=['request_type'], name='featurerequest_type_idx'),
]

# EmailVerification
indexes = [
    models.Index(fields=['expires_at'], name='emailverification_expires_idx'),
]
```

## Expected Impact

**Performance improvements:**
- ReadinessReport queries: 10-100x faster on large datasets
- Profile role filtering: 5-10x faster
- FeatureRequest ordering: 2-5x faster
- Date range queries: Significant improvement

**Storage impact:**
- Minimal (indexes are typically 10-20% of table size)
- Worth the trade-off for query performance

## Testing Plan

1. **Before migration:**
   - Document current query times on test data
   - Use Django's `connection.queries` to see query count

2. **After migration:**
   - Verify indexes exist: `\d+ table_name` in PostgreSQL
   - Re-run same queries and measure improvement
   - Test with larger datasets (1000+ reports)

3. **Verify no regressions:**
   - Run existing tests
   - Test all views that query these models
   - Check admin interface still works

## Rollback Plan

If issues occur:
1. Migration can be reversed: `python manage.py migrate core <previous_migration>`
2. Indexes can be dropped without data loss
3. No data migration required (indexes only)

## Next Steps

1. ✅ Create this plan
2. ⏳ Update models.py with indexes
3. ⏳ Create migration
4. ⏳ Test migration
5. ⏳ Verify performance improvement
6. ⏳ Document results

