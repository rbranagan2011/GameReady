"""
Django settings for GameReady project.

This file imports settings based on the DJANGO_SETTINGS_MODULE environment variable.
Default is development settings for local development.
"""

import os

# Determine which settings to use
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'GameReady.settings.development')

if settings_module == 'GameReady.settings.development':
    from .settings.development import *
elif settings_module == 'GameReady.settings.production':
    from .settings.production import *
else:
    # Fallback to development
    from .settings.development import *
