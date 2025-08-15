"""Settings package for the project.

Defaults to development settings. For production, set DJANGO_SETTINGS_MODULE to
"OpticorAI_project_management_system.settings.prod".
"""

# Default to development settings so that
# DJANGO_SETTINGS_MODULE=OpticorAI_project_management_system.settings works.
from .dev import *  # noqa: F401,F403


