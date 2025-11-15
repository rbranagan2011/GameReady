"""
Development settings for GameReady project.

These settings are for local development only.
"""

from .base import *
import os
from django.core.management.utils import get_random_secret_key

# Load environment variables from a local .env file if it exists and generate defaults if missing.
# Assumption: auto-generating a per-developer SECRET_KEY in .env is acceptable for local setups.
ENV_PATH = BASE_DIR / '.env'


def _load_local_env(path):
    env_values = {}
    if not path.exists():
        return env_values

    with path.open() as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env_values[key] = value
            os.environ.setdefault(key, value)
    return env_values


_load_local_env(ENV_PATH)

if 'SECRET_KEY' not in os.environ:
    generated_secret = get_random_secret_key()
    os.environ['SECRET_KEY'] = generated_secret
    existing_text = ''
    if ENV_PATH.exists():
        existing_text = ENV_PATH.read_text()
    else:
        ENV_PATH.touch()
    with ENV_PATH.open('a') as env_file:
        if existing_text and not existing_text.endswith('\n'):
            env_file.write('\n')
        env_file.write(f'SECRET_KEY={generated_secret}\n')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('SECRET_KEY environment variable is required. See README for setup steps.')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email configuration for development
# Use console backend to print emails to terminal
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'admin@gamereadyapp.com'
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')

