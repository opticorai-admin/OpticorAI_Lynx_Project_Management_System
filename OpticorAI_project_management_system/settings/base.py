"""Base settings shared by all environments."""
import dj_database_url
from pathlib import Path
import os
try:
    from decouple import config as env_config  # reads values from .env when available
except Exception:  # decouple is optional for these reads
    env_config = lambda key, default=None: os.environ.get(key, default)

BASE_DIR = Path(__file__).resolve().parents[2]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # local apps
    'core',
    
]



AUTH_USER_MODEL = 'core.CustomUser'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.BusinessTimezoneMiddleware',
]

ROOT_URLCONF = 'OpticorAI_project_management_system.urls'

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

WSGI_APPLICATION = 'OpticorAI_project_management_system.wsgi.application'

# Database: prefer DATABASE_URL if provided; otherwise fall back to SQLite.
DATABASES = {
    'default': dj_database_url.config(
        env='DATABASE_URL',
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=int(os.environ.get('CONN_MAX_AGE', '600')),
        conn_health_checks=True,
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Languages available (frontend uses its own switcher; backend remains opt-in)
LANGUAGES = [
    ('en', 'English'),
    ('ar', 'العربية'),
]

from pathlib import Path as _Path
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]
LANGUAGE_COOKIE_NAME = 'django_language'

# Business-local timezone for date-based business rules (e.g., task due checks)
# Example: 'Asia/Muscat' or leave unset to use default local timezone
BUSINESS_TIMEZONE = os.environ.get('BUSINESS_TIMEZONE', '') or None

# Static/media
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
# Allow overriding MEDIA_ROOT via env (e.g., when using Render Persistent Disk)
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))

# Optional Cloudinary media storage. If CLOUDINARY_URL is set (env or .env), store media on Cloudinary.
_cloudinary_url = os.environ.get('CLOUDINARY_URL') or env_config('CLOUDINARY_URL', default=None)
if _cloudinary_url:
    INSTALLED_APPS += ['cloudinary', 'cloudinary_storage']
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

# Base URL used in emails (fallback used if not set). Set this in prod env.
SITE_BASE_URL = os.environ.get('SITE_BASE_URL', 'https://opticorai-lynx-project-management-system.onrender.com')

# Custom Authentication Backend
AUTHENTICATION_BACKENDS = [
    'core.auth_backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Security: Email-based 2FA (can be disabled via env)
ENABLE_EMAIL_2FA = os.environ.get('ENABLE_EMAIL_2FA', 'true').lower() == 'true'


