from core.models import CustomUser, Notification
from django.core.cache import cache
from django.conf import settings

def logged_user_processor(request):
    """
    Context processor to provide logged_user to all templates
    """
    if request.user.is_authenticated:
        try:
            # Use select_related to optimize database queries
            logged_user = CustomUser.objects.select_related('under_supervision').get(id=request.user.id)
            return {'logged_user': logged_user}
        except CustomUser.DoesNotExist:
            return {'logged_user': None}
    return {'logged_user': None}


def notifications_processor(request):
    """
    Context processor to provide unread notifications to all templates
    """
    if request.user.is_authenticated:
        # Cached count for performance
        cache_key = f"unread_count:{request.user.id}"
        unread_count = cache.get(cache_key)
        if unread_count is None:
            unread_count = Notification.objects.filter(recipient=request.user, read=False).count()
            cache.set(cache_key, unread_count, 15)  # short cache to keep badges fresh
        # Show only the latest 10 items in the dropdown for performance
        unread_notifications = (
            Notification.objects.select_related('sender')
            .filter(recipient=request.user, read=False)
            .order_by('-created_at')[:10]
        )
        return {
            'unread_notifications': unread_notifications,
            'unread_count': unread_count,
        }
    return {'unread_notifications': [], 'unread_count': 0}


def debug_flag_processor(request):
    """Expose DEBUG to templates for safe conditional rendering (e.g., analytics)."""
    return {"DEBUG": settings.DEBUG}