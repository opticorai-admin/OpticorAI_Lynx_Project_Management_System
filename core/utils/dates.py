from __future__ import annotations

from datetime import date
from django.utils import timezone
from django.conf import settings


def business_localdate() -> date:
    """
    Returns the business-local current date. If BUSINESS_TIMEZONE is configured
    (e.g., 'Asia/Muscat'), use timezone.localdate() which respects USE_TZ and
    current time zone. This wrapper exists to centralize 'today' so status logic
    behaves consistently regardless of server timezone.
    """
    # If a specific business timezone is set, Django's timezone handling will
    # be configured elsewhere; we simply return localdate to avoid drift.
    _ = getattr(settings, 'BUSINESS_TIMEZONE', None)
    return timezone.localdate()


