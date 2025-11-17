# Database Indexes Implementation - Summary

## ✅ Completed

### Step 1: Added Indexes to Models

All required indexes have been added to the models in `core/models.py`:

#### 1. ReadinessReport Model
```python
class Meta:
    indexes = [
        models.Index(fields=['athlete', 'date_created'], name='readinessreport_athlete_date_idx'),
        models.Index(fields=['date_created'], name='readinessreport_date_idx'),
    ]
```
**Purpose**: Optimize the most common query patterns:
- Finding reports for a specific athlete on a specific date
- Date range queries (last 7 days, last 30 days, etc.)
- Ordering by date

#### 2. PlayerPersonalLabel Model
```python
class Meta:
    indexes = [
        models.Index(fields=['athlete', 'date'], name='playerpersonallabel_athlete_date_idx'),
    ]
```
**Purpose**: Optimize queries for athlete-specific date ranges (monthly views)

#### 3. Profile Model
```python
class Meta:
    indexes = [
        models.Index(fields=['role'], name='profile_role_idx'),
    ]
```
**Purpose**: Speed up filtering by role (ATHLETE vs COACH) - used frequently in views

#### 4. FeatureRequest Model
```python
class Meta:
    indexes = [
        models.Index(fields=['created_at'], name='featurerequest_created_idx'),
        models.Index(fields=['request_type'], name='featurerequest_type_idx'),
    ]
```
**Purpose**: 
- Optimize ordering by creation date
- Speed up filtering by request type (FEATURE vs BUG)

#### 5. EmailVerification Model
```python
class Meta:
    indexes = [
        models.Index(fields=['expires_at'], name='emailverification_expires_idx'),
    ]
```
**Purpose**: Enable efficient cleanup queries for expired verification tokens

## ⏳ Next Steps

### Step 2: Create Migration

Run the following command to create the migration:

```bash
# Activate virtual environment first
source venv/bin/activate

# Create migration
python manage.py makemigrations core --name add_database_indexes
```

This will create a new migration file in `core/migrations/` (e.g., `0019_add_database_indexes.py`)

### Step 3: Review Migration File

Before applying, review the generated migration file to ensure:
- All indexes are included
- Index names match our specifications
- No unintended changes

### Step 4: Test Migration (Development)

```bash
# Apply migration to development database
python manage.py migrate core

# Verify indexes were created (PostgreSQL)
python manage.py dbshell
# Then in psql:
\d+ core_readinessreport
\d+ core_profile
\d+ core_featurerequest
# etc.
```

### Step 5: Verify Index Creation

Check that indexes exist in the database:

**PostgreSQL:**
```sql
SELECT 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename LIKE 'core_%'
ORDER BY tablename, indexname;
```

**SQLite (development):**
```sql
SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE '%_idx';
```

### Step 6: Test Query Performance

Before and after applying indexes, test query performance:

```python
# In Django shell
from django.db import connection
from core.models import ReadinessReport
from django.utils import timezone
from datetime import timedelta

# Reset query log
connection.queries_log.clear()

# Test query
reports = ReadinessReport.objects.filter(
    date_created__gte=timezone.now().date() - timedelta(days=30)
).order_by('-date_created')[:10]

# Check query count and time
print(f"Queries: {len(connection.queries)}")
for q in connection.queries:
    print(f"Time: {q['time']}s - {q['sql'][:100]}")
```

### Step 7: Apply to Production

Once tested in development:

1. Commit the migration file to git
2. Deploy to production
3. Run migration: `python manage.py migrate core`
4. Monitor query performance

## Expected Performance Improvements

### ReadinessReport Queries
- **Before**: Full table scan on large datasets (O(n))
- **After**: Index scan (O(log n))
- **Expected improvement**: 10-100x faster on datasets with 1000+ reports

### Profile Role Filtering
- **Before**: Sequential scan through all profiles
- **After**: Index scan
- **Expected improvement**: 5-10x faster

### FeatureRequest Ordering
- **Before**: Sort all records in memory
- **After**: Index scan (already sorted)
- **Expected improvement**: 2-5x faster

## Index Storage Impact

Indexes add minimal storage overhead:
- Typically 10-20% of table size
- Worth the trade-off for query performance
- Can be dropped if needed (no data loss)

## Rollback Plan

If issues occur, indexes can be safely removed:

```bash
# Rollback migration
python manage.py migrate core <previous_migration_number>

# Or manually drop indexes in database
# (Indexes don't affect data, only query performance)
```

## Verification Checklist

- [x] Indexes added to models.py
- [ ] Migration file created
- [ ] Migration tested in development
- [ ] Indexes verified in database
- [ ] Query performance tested
- [ ] Migration applied to production
- [ ] Performance improvements confirmed

## Notes

- ForeignKey fields automatically have indexes created by Django ✅
- unique_together constraints automatically create indexes ✅
- ManyToMany relationships are handled by Django automatically ✅
- OneToOne relationships automatically have indexes ✅

The indexes we added are for:
- Frequently queried fields that don't have automatic indexes
- Composite indexes for common query patterns
- Fields used in ordering operations

---

**Status**: ✅ Models updated, ready for migration creation  
**Next**: Create and test migration

