"""Development settings."""
from .base import *  # noqa
import os

DEBUG = True
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dxnl0q@bvrj$x8b**h*088h7mro+nb!wl6mzumk9+1z4za4zq&')
ALLOWED_HOSTS = ['*']

# Email backend for dev (override with env to enable real SMTP in development)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# Optional SMTP configuration for dev when using SMTP backend
# EMAIL_HOST = os.environ.get('EMAIL_HOST', 'ashirfabtechsol@gmail.com')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'ashirfabtechsol@gmail.com')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'aszx1234')
# EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
# DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'ashirfabtechsol@gmail.com')


# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@example.com')


