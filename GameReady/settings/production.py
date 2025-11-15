"""
Production settings for GameReady project.

These settings are for production deployment.
"""

from .base import *
import os
from pathlib import Path

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set in production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

raw_allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')
extra_hosts = [host.strip() for host in raw_allowed_hosts.split(',') if host.strip()]

# Always allow the Render service hostname and primary custom domain by default.
DEFAULT_HOSTS = [
    'gameready.onrender.com',
    'start.gamereadyapp.com',
]

ALLOWED_HOSTS = DEFAULT_HOSTS.copy()

# Append any custom hosts provided via environment variables.
for host in extra_hosts:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

# Configure CSRF trusted origins from environment; default to HTTPS versions of allowed hosts.
raw_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in raw_csrf_origins.split(',') if origin.strip()]
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS]

# Honor the X-Forwarded-Proto header set by Render's proxy.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Static files configuration
# Ensure STATIC_ROOT is a string (not Path object) for Django compatibility
STATIC_ROOT = str(BASE_DIR / 'staticfiles')

# Media files configuration for Render persistent disk
# The persistent disk is mounted at /opt/render/project/src/media
# Always use the persistent disk path if it exists, otherwise fall back
PERSISTENT_DISK_MEDIA_PATH = '/opt/render/project/src/media'

# Check if persistent disk is mounted (try multiple times as it might mount after startup)
import time
media_root_set = False
for attempt in range(3):
    if os.path.exists(PERSISTENT_DISK_MEDIA_PATH):
        MEDIA_ROOT = PERSISTENT_DISK_MEDIA_PATH
        media_root_set = True
        break
    time.sleep(0.1)  # Brief pause in case disk is mounting

if not media_root_set:
    # Fallback to default location if persistent disk not mounted
    MEDIA_ROOT = str(BASE_DIR / 'media')

# Ensure MEDIA_ROOT is always a string (not Path object) for Django compatibility
MEDIA_ROOT = str(MEDIA_ROOT)

# Create media directory structure if it doesn't exist
media_path = Path(MEDIA_ROOT)
media_path.mkdir(parents=True, exist_ok=True)
# Also ensure team_logos subdirectory exists
TEAM_LOGOS_DIR = media_path / 'team_logos'
TEAM_LOGOS_DIR.mkdir(parents=True, exist_ok=True)

# Ensure write permissions (in case directory was created by root)
try:
    import stat
    # Make directory writable by owner and group
    media_path.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)  # 775
    TEAM_LOGOS_DIR.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)  # 775
except Exception:
    # If we can't change permissions, that's okay - might not have permission
    pass

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@gamereadyapp.com')
BASE_URL = os.environ.get('BASE_URL', 'https://start.gamereadyapp.com')

# Validate email configuration on startup (warn but don't fail)
# This helps catch configuration issues early
import logging
logger = logging.getLogger(__name__)

if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    logger.warning(
        "Email configuration incomplete: EMAIL_HOST_USER or EMAIL_HOST_PASSWORD not set. "
        "Email verification and reminders will not work. "
        "Set these environment variables in Render dashboard."
    )
elif not DEFAULT_FROM_EMAIL:
    logger.warning(
        "DEFAULT_FROM_EMAIL not set. Using default value. "
        "Set DEFAULT_FROM_EMAIL environment variable in Render dashboard."
    )

