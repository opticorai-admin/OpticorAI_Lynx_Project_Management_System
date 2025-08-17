import logging
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification, CustomUser


logger = logging.getLogger(__name__)


def _build_email_subject(message: str) -> str:
    base = "New notification"
    preview = message.strip().replace("\n", " ")
    if preview:
        # Keep subject concise
        return f"{base}: {preview[:60]}" if len(preview) > 60 else f"{base}: {preview}"
    return base


def _build_email_body(message: str, link: Optional[str]) -> str:
    lines = [
        "You have a new notification:",
        "",
        message.strip(),
    ]
    if link:
        # Ensure absolute URL for emails
        if str(link).startswith("http://") or str(link).startswith("https://"):
            absolute = link
        else:
            absolute = getattr(settings, "SITE_BASE_URL", "https://opticorai-project-management-system.onrender.com") + str(link)
        lines.extend(["", f"Link: {absolute}"])
    return "\n".join(lines)


@receiver(post_save, sender=Notification)
def send_notification_email(sender, instance: Notification, created: bool, **kwargs) -> None:
    """Send an email to the recipient when a Notification is created.

    This is synchronous by design to avoid adding infra right now. If needed,
    we can switch to enqueueing an async task later without changing callers.
    """
    if not created:
        return

    recipient = instance.recipient
    recipient_email = getattr(recipient, "email", None)
    if not recipient_email:
        return

    try:
        subject = _build_email_subject(instance.message or "")
        # Prefer absolute links if provided; otherwise, include relative
        link_value = instance.link or None
        body = _build_email_body(instance.message or "", link_value)

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None) or "no-reply@example.com"

        result = send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[recipient_email],
            fail_silently=True,  # Never break the request flow
        )
        if not result:
            logger.warning(
                "Notification email reported as not sent (send_mail returned 0). To=%s",
                recipient_email,
            )
    except Exception:  # noqa: BLE001 - best-effort; log and continue
        logger.exception("Failed to send notification email for Notification id=%s", instance.id)


@receiver(post_save, sender=CustomUser)
def send_welcome_on_user_created(sender, instance: CustomUser, created: bool, **kwargs) -> None:
    """Notify and email a user when their account is created by an admin/manager.

    Keeps current flows untouched by listening to model creation only.
    """
    if not created:
        return

    # Avoid emailing superusers created via management commands
    if instance.is_superuser:
        return

    # Create an in-app notification for the new user
    try:
        Notification.objects.create(
            recipient=instance,
            sender=getattr(instance, "created_by", None),
            message=(
                "Your account has been created. You can now log in to the system."
            ),
            link="/accounts/login/",
        )
    except Exception:
        logger.exception("Failed to create welcome Notification for user id=%s", instance.id)

    # Send a welcome email (skip if view already sent a credential email)
    if getattr(instance, "_skip_welcome_email", False):
        return

    recipient_email = getattr(instance, "email", None)
    if not recipient_email:
        return

    try:
        subject = "Welcome to the system"
        lines = [
            f"Hello {instance.get_full_name() or instance.username},",
            "",
            "Your account has been created and is ready to use.",
            "",
            "Login page:",
            (
                (getattr(settings, "SITE_BASE_URL", "https://opticorai-project-management-system.onrender.com") + "/accounts/login/")
            ),
        ]
        body = "\n".join(lines)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None) or "no-reply@example.com"

        result = send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[recipient_email],
            fail_silently=True,
        )
        if not result:
            logger.warning(
                "Welcome email reported as not sent (send_mail returned 0). To=%s",
                recipient_email,
            )
    except Exception:
        logger.exception("Failed to send welcome email for user id=%s", instance.id)

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task


@receiver(post_save, sender=Task)
def update_task_status_on_save(sender, instance, created, **kwargs):
    """
    Automatically update task status when a task is saved
    This ensures status is always current when tasks are modified
    """
    # The status is already updated in the model's save() method
    # This signal is for any additional logic if needed in the future
    pass 









