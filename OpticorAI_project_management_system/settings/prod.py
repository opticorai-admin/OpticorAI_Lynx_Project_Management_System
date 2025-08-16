"""Production settings."""
from .base import *  # noqa
import os

DEBUG = False


SECRET_KEY = '6+0(p7z1ylv0g_a)*3inzmtq-1%#qh_zdj_kz&2lp$d0ccc##8'


ALLOWED_HOSTS = ['web-production-60bd4.up.railway.app']
CSRF_TRUSTED_ORIGINS = ['https://web-production-60bd4.up.railway.app']
print("CSRF_TRUSTED_ORIGINS = ", CSRF_TRUSTED_ORIGINS)

# Security hardening
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# WhiteNoise for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'ashirfabtechsol@gmail.com'
EMAIL_HOST_PASSWORD = 'jyig urwj rtdi ptcy'
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = 'ashirfabtechsol@gmail.com'

# Optional Redis cache (enabled if REDIS_URL is provided)
if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ['REDIS_URL'],
        }
    }

# Persistent DB connections for better throughput (safe default; override via env)
try:
    # If DATABASES exists from base, update default
    DATABASES['default']['CONN_MAX_AGE'] = int(os.environ.get('CONN_MAX_AGE', '60'))
except Exception:
    pass























