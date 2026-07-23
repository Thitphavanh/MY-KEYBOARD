import os
from .base import *

DEBUG = False

# In production, ALLOWED_HOSTS should contain domain names.
# For now we default to allow any, but this can be changed.
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Override SECRET_KEY from environment in production for security
SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)
