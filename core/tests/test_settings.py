"""
Test-specific settings to override rate limiting cache warnings.
"""
from GameReady.settings.development import *

# Suppress rate limiting cache warnings for tests
# LocMemCache works for testing even though it's not shared
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.E003', 'django_ratelimit.W001']

# Allow Django test client host
ALLOWED_HOSTS = ['testserver', 'localhost']

