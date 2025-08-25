from __future__ import annotations

from datetime import date
from django.utils import timezone
from django.conf import settings
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover - very old Python fallback
    ZoneInfo = None  # type: ignore


def business_localdate() -> date:
    """
    Return today's date in the business timezone.

    - If settings.BUSINESS_TIMEZONE is set (e.g., 'Asia/Muscat'), compute the
      date in that timezone explicitly, independent of the server TZ.
    - Otherwise, fall back to Django's timezone.localdate().
    """
    tz_name = getattr(settings, 'BUSINESS_TIMEZONE', None)
    if tz_name and ZoneInfo is not None:
        try:
            tz = ZoneInfo(tz_name)
            return timezone.now().astimezone(tz).date()
        except Exception:
            pass
    return timezone.localdate()


