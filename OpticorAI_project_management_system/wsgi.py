"""
WSGI config for OpticorAI_project_management_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Default to production settings if explicitly set, otherwise fall back to
# the compatibility shim which imports dev by default.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'OpticorAI_project_management_system.settings')

application = get_wsgi_application()
