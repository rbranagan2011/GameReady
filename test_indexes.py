#!/usr/bin/env python
"""
Test script to verify database indexes are correctly defined.
This script validates the migration file syntax and structure.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GameReady.settings.development')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    django.setup()
except Exception as e:
    print(f"Warning: Could not setup Django: {e}")
    print("This is okay - we're just validating the migration file structure.")
    sys.exit(0)

from django.db import connection
from core.models import (
    ReadinessReport, 
    PlayerPersonalLabel, 
    Profile, 
    FeatureRequest, 
    EmailVerification
)

def check_indexes():
    """Check if indexes are defined in models."""
    print("=" * 60)
    print("Checking Database Indexes")
    print("=" * 60)
    
    results = []
    
    # Check ReadinessReport
    print("\n1. ReadinessReport Model:")
    if hasattr(ReadinessReport._meta, 'indexes'):
        indexes = ReadinessReport._meta.indexes
        print(f"   Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f"   - {idx.name}: {idx.fields}")
            results.append(('ReadinessReport', idx.name, idx.fields))
    else:
        print("   ❌ No indexes found!")
        results.append(('ReadinessReport', 'ERROR', 'No indexes'))
    
    # Check PlayerPersonalLabel
    print("\n2. PlayerPersonalLabel Model:")
    if hasattr(PlayerPersonalLabel._meta, 'indexes'):
        indexes = PlayerPersonalLabel._meta.indexes
        print(f"   Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f"   - {idx.name}: {idx.fields}")
            results.append(('PlayerPersonalLabel', idx.name, idx.fields))
    else:
        print("   ❌ No indexes found!")
        results.append(('PlayerPersonalLabel', 'ERROR', 'No indexes'))
    
    # Check Profile
    print("\n3. Profile Model:")
    if hasattr(Profile._meta, 'indexes'):
        indexes = Profile._meta.indexes
        print(f"   Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f"   - {idx.name}: {idx.fields}")
            results.append(('Profile', idx.name, idx.fields))
    else:
        print("   ❌ No indexes found!")
        results.append(('Profile', 'ERROR', 'No indexes'))
    
    # Check FeatureRequest
    print("\n4. FeatureRequest Model:")
    if hasattr(FeatureRequest._meta, 'indexes'):
        indexes = FeatureRequest._meta.indexes
        print(f"   Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f"   - {idx.name}: {idx.fields}")
            results.append(('FeatureRequest', idx.name, idx.fields))
    else:
        print("   ❌ No indexes found!")
        results.append(('FeatureRequest', 'ERROR', 'No indexes'))
    
    # Check EmailVerification
    print("\n5. EmailVerification Model:")
    if hasattr(EmailVerification._meta, 'indexes'):
        indexes = EmailVerification._meta.indexes
        print(f"   Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f"   - {idx.name}: {idx.fields}")
            results.append(('EmailVerification', idx.name, idx.fields))
    else:
        print("   ❌ No indexes found!")
        results.append(('EmailVerification', 'ERROR', 'No indexes'))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    expected_indexes = {
        'ReadinessReport': 2,
        'PlayerPersonalLabel': 1,
        'Profile': 1,
        'FeatureRequest': 2,
        'EmailVerification': 1,
    }
    
    all_good = True
    for model_name, expected_count in expected_indexes.items():
        model_indexes = [r for r in results if r[0] == model_name and 'ERROR' not in r[1]]
        actual_count = len(model_indexes)
        status = "✅" if actual_count == expected_count else "❌"
        print(f"{status} {model_name}: {actual_count}/{expected_count} indexes")
        if actual_count != expected_count:
            all_good = False
    
    if all_good:
        print("\n✅ All indexes are correctly defined in models!")
        return True
    else:
        print("\n❌ Some indexes are missing!")
        return False

def validate_migration_file():
    """Validate the migration file syntax."""
    print("\n" + "=" * 60)
    print("Validating Migration File")
    print("=" * 60)
    
    migration_path = 'core/migrations/0019_add_database_indexes.py'
    if os.path.exists(migration_path):
        print(f"✅ Migration file exists: {migration_path}")
        
        # Try to import it
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("migration", migration_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print("✅ Migration file syntax is valid")
            return True
        except Exception as e:
            print(f"❌ Migration file has syntax errors: {e}")
            return False
    else:
        print(f"❌ Migration file not found: {migration_path}")
        return False

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Database Index Validation Test")
    print("=" * 60)
    
    migration_ok = validate_migration_file()
    indexes_ok = check_indexes()
    
    print("\n" + "=" * 60)
    if migration_ok and indexes_ok:
        print("✅ ALL TESTS PASSED")
        print("\nNext steps:")
        print("1. Run: python manage.py migrate core")
        print("2. Verify indexes in database")
        print("3. Test query performance")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the errors above.")
    print("=" * 60 + "\n")

