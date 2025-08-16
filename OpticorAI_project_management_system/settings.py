
"""
Django production-ready settings (merged into one file).
Supports environment-based config and is compatible with local dev and deployment platforms (e.g., Railway, PythonAnywhere).
"""

import os
from pathlib import Path

# BASE DIR
BASE_DIR = Path(__file__).resolve().parents[1]

# DEBUG/SECRET
DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() == 'true'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '6+0(p7z1ylv0g_a)*3inzmtq-1%#qh_zdj_kz&2lp$d0ccc##8' if DEBUG else None)
if not DEBUG and not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

# ALLOWED HOSTS / CSRF
ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    'web-production-60bd4.up.railway.app,127.0.0.1,localhost'
).split(',')

CSRF_TRUSTED_ORIGINS = os.environ.get(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'https://web-production-60bd4.up.railway.app'
).split(',')

# APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

# AUTH
AUTH_USER_MODEL = 'core.CustomUser'
AUTHENTICATION_BACKENDS = [
    'core.auth_backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URL/WGSI
ROOT_URLCONF = 'OpticorAI_project_management_system.urls'
WSGI_APPLICATION = 'OpticorAI_project_management_system.wsgi.application'

# TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.logged_user_processor',
                'core.context_processors.notifications_processor',
                'core.context_processors.debug_flag_processor',
            ],
        },
    },
]

# DATABASE
if os.environ.get("DATABASE_URL"):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(os.environ["DATABASE_URL"])
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
DATABASES['default']['CONN_MAX_AGE'] = int(os.environ.get('CONN_MAX_AGE', '60'))

# VALIDATORS
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# TIME/LOCALE
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# STATIC/MEDIA
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# STATIC FILE STORAGE
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# LOGIN
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

# 2FA Toggle
ENABLE_EMAIL_2FA = os.environ.get('ENABLE_EMAIL_2FA', 'true').lower() == 'true'

# EMAIL
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@example.com')

# REDIS
if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ['REDIS_URL'],
        }
    }

# PROD-HARDENING
if not DEBUG:
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
