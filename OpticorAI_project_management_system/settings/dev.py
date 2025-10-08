"""Development settings."""
from .base import *  # noqa
import os
from decouple import config

DEBUG = True
SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-secret-key')
ALLOWED_HOSTS = ['*']

# Email backend for dev (override with env to enable real SMTP in development)
# Email backend configuration
# Use console backend if no credentials provided to avoid authentication errors
if os.environ.get('EMAIL_HOST_PASSWORD'):
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    # Uncomment the line below to suppress the warning
    # print('WARNING: No EMAIL_HOST_PASSWORD found. Using console backend. Emails will only print to console.')

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
# Gmail SMTP Configuration
# IMPORTANT: Use App Password, not regular password!
# 1. Enable 2-Factor Authentication on Gmail account
# 2. Generate App Password: https://myaccount.google.com/apppasswords
# 3. Use the 16-character App Password below
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')  # Set your App Password here
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@example.com')



# Temporarily disable email-based 2FA in development without touching app code
ENABLE_EMAIL_2FA = True