"""Compatibility shim: keep import path working for existing references.

Defaults to development settings. For production, set DJANGO_SETTINGS_MODULE
to 'OpticorAI_project_management_system.settings.prod'.
"""



from .settings.dev import *  # noqa: F401,F403
