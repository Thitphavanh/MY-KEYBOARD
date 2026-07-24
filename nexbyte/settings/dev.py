from .base import *

DEBUG = True

ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Local, gitignored overrides (real email credentials etc.) — see local_settings.py.example
try:
    from .local_settings import *
except ImportError:
    pass
