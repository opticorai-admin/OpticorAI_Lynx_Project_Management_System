from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Task


class Command(BaseCommand):
    help = 'Recompute and update task statuses (open/due/closed) using target_date and completion.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        self.stdout.write(f"Updating task statuses for today={today}...")
        updates = Task.update_all_statuses()
        self.stdout.write(self.style.SUCCESS(
            f"Updated: total={updates.get('total_updated', 0)}, "
            f"closed={updates.get('closed', 0)}, due={updates.get('due', 0)}, open={updates.get('open', 0)}"
        ))


