from __future__ import annotations

from django.utils import timezone
from django.conf import settings
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore


class BusinessTimezoneMiddleware:
    """Activate BUSINESS_TIMEZONE for each request so UI uses local time."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._tz = getattr(settings, 'BUSINESS_TIMEZONE', None)

    def __call__(self, request):
        token = None
        if self._tz and ZoneInfo is not None:
            try:
                tz = ZoneInfo(self._tz)
                timezone.activate(tz)
                token = tz
            except Exception:
                pass
        response = self.get_response(request)
        if token is not None:
            timezone.deactivate()
        return response


