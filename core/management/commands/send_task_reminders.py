from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from core.models import Task, CustomUser, Notification
from core.utils.dates import business_localdate


class Command(BaseCommand):
    help = 'Send reminder emails: 5 days before task target date, on submission to manager, and 5-day manager follow-up.'

    def handle(self, *args, **options):
        today = business_localdate()
        self.stdout.write(f"Running task reminders for {today}...")

        # (a) Employee reminder 5 days before target date
        try:
            remind_date = today + timedelta(days=5)
            upcoming = Task.objects.filter(
                target_date=remind_date,
                percentage_completion__lt=100,
            ).select_related('responsible')
            for task in upcoming:
                if task.responsible and task.responsible.email:
                    Notification.objects.create(
                        recipient=task.responsible,
                        sender=None,
                        message=f"Reminder: Your task '{task.issue_action[:40]}...' is due on {task.target_date} (in 5 days).",
                        link=f"/projects/task/{task.id}/",
                    )
        except Exception:
            pass

        # (b) Immediate manager email on submission is handled at submission time via Notification; nothing to do here

        # (c) Manager follow-up 5 days after employee submission if no evaluation/approval
        try:
            five_days_ago = today - timedelta(days=5)
            pending = Task.objects.filter(
                employee_submitted_at__date=five_days_ago,
                evaluation_status='pending',
            ).select_related('responsible__under_supervision')
            for task in pending:
                manager = getattr(task.responsible, 'under_supervision', None)
                if manager and manager.email:
                    Notification.objects.create(
                        recipient=manager,
                        sender=None,
                        message=f"Reminder: Task '{task.issue_action[:40]}...' submitted by {task.responsible.get_full_name()} is awaiting your evaluation/approval.",
                        link=f"/projects/task/{task.id}/",
                    )
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS("Task reminders executed."))


