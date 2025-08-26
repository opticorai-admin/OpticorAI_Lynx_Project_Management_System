from __future__ import annotations

from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from core.utils.dates import business_localdate
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
        # Lightweight daily status refresh: ensures due/open/closed are up-to-date
        try:
            today = business_localdate()
            guard_key = f"task_status_auto_refresh:{today.isoformat()}"
            if cache.get(guard_key) is None:
                # Import lazily to avoid import-time issues
                from core.models import Task  # noqa
                Task.update_all_statuses()
                cache.set(guard_key, True, 60 * 60 * 24)
        except Exception:
            # Non-blocking if anything goes wrong
            pass
        response = self.get_response(request)
        if token is not None:
            timezone.deactivate()
        return response


