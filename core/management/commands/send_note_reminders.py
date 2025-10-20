from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta

from core.models import Note, NoteReminder, Notification
from core.utils.dates import business_localdate


class Command(BaseCommand):
    help = 'Send reminder emails for notes scheduled for today.'

    def handle(self, *args, **options):
        today = business_localdate()
        self.stdout.write(f"Running note reminders for {today}...")

        # Get all note reminders scheduled for today that haven't been sent yet
        try:
            reminders = NoteReminder.objects.filter(
                scheduled_for=today,
                sent_at__isnull=True
            ).select_related('note', 'recipient', 'created_by')
            
            sent_count = 0
            for reminder in reminders:
                if reminder.recipient and reminder.recipient.email:
                    message = reminder.message or f"Reminder: Note '{reminder.note.title}'"
                    try:
                        # Create notification (this triggers the email signal)
                        Notification.objects.create(
                            recipient=reminder.recipient,
                            sender=reminder.created_by,
                            message=message,
                            link=f"/my-notes/{reminder.note.id}/",
                        )
                        # Mark reminder as sent
                        reminder.mark_sent()
                        # Auto-create next occurrence if repeating
                        try:
                            if reminder.repeat_interval and reminder.repeat_interval != 'none':
                                if reminder.repeat_interval == 'weekly':
                                    next_date = reminder.scheduled_for + timedelta(weeks=1)
                                elif reminder.repeat_interval == 'monthly':
                                    # Add 1 month safely
                                    year = reminder.scheduled_for.year
                                    month = reminder.scheduled_for.month + 1
                                    if month > 12:
                                        month = 1
                                        year += 1
                                    # Keep same day where possible, clamp to month-end
                                    from calendar import monthrange
                                    day = min(reminder.scheduled_for.day, monthrange(year, month)[1])
                                    next_date = reminder.scheduled_for.replace(year=year, month=month, day=day)
                                else:
                                    next_date = None
                                if next_date:
                                    NoteReminder.objects.create(
                                        note=reminder.note,
                                        recipient=reminder.recipient,
                                        scheduled_for=next_date,
                                        message=reminder.message,
                                        created_by=reminder.created_by,
                                        # carry forward repeat setting
                                        repeat_interval=reminder.repeat_interval,
                                    )
                        except Exception as e:
                            # Non-blocking: log to stdout only
                            self.stdout.write(self.style.WARNING(f"Could not create next repeated reminder: {str(e)}"))
                        sent_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Sent reminder to {reminder.recipient.get_full_name()} for note '{reminder.note.title}'"
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Failed to send reminder to {reminder.recipient.get_full_name()}: {str(e)}"
                            )
                        )
            
            self.stdout.write(
                self.style.SUCCESS(f"Note reminders completed. Sent {sent_count} reminders.")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error running note reminders: {str(e)}")
            )

