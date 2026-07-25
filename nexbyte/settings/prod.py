import os
from .base import *

DEBUG = False

# Comma-separated list of allowed hosts, e.g. "yourname.pythonanywhere.com"
_allowed_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '.pythonanywhere.com')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',') if h.strip()]

CSRF_TRUSTED_ORIGINS = [
    f'https://*{h}' if h.startswith('.') else f'https://{h}'
    for h in ALLOWED_HOSTS
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Override SECRET_KEY from environment in production for security
SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

# Serve static files directly via WhiteNoise (works without extra web-server config)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
] + [m for m in MIDDLEWARE if m != 'django.middleware.security.SecurityMiddleware']

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
