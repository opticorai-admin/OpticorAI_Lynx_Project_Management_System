"""Development settings."""
from .base import *  # noqa
import os

DEBUG = False
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '6+0(p7z1ylv0g_a)*3inzmtq-1%#qh_zdj_kz&2lp$d0ccc##8')
ALLOWED_HOSTS = ['*']

# Email backend for dev (override with env to enable real SMTP in development)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')


# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'ashirfabtechsol@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'jyig urwj rtdi ptcy')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'ashirfabtechsol@gmail.com')


