from django.core.management.base import BaseCommand
from core.models import TaskPriorityType
import os


class Command(BaseCommand):
    help = 'Fix priority multipliers to match the requirements'

    def handle(self, *args, **options):
        self.stdout.write('Fixing priority multipliers...')
        
        # Update Low priority
        low_priority = TaskPriorityType.objects.filter(code='low').first()
        if low_priority:
            low_priority.multiplier = 1.0
            low_priority.description = 'Low priority tasks - no bonus multiplier (0%)'
            low_priority.save()
            self.stdout.write(f'Updated {low_priority.name}: {low_priority.multiplier}x multiplier')
        
        # Update Medium priority
        medium_priority = TaskPriorityType.objects.filter(code='medium').first()
        if medium_priority:
            med_mult = float(os.environ.get('PRIORITY_MULTIPLIER_MEDIUM', '1.05'))
            medium_priority.multiplier = med_mult
            medium_priority.description = f'Medium priority tasks - {int((med_mult-1)*100)}% bonus multiplier'
            medium_priority.save()
            self.stdout.write(f'Updated {medium_priority.name}: {medium_priority.multiplier}x multiplier')
        
        # Update High priority
        high_priority = TaskPriorityType.objects.filter(code='high').first()
        if high_priority:
            high_mult = float(os.environ.get('PRIORITY_MULTIPLIER_HIGH', '1.2'))
            high_priority.multiplier = high_mult
            high_priority.description = f'High priority tasks - {int((high_mult-1)*100)}% bonus multiplier'
            high_priority.save()
            self.stdout.write(f'Updated {high_priority.name}: {high_priority.multiplier}x multiplier')
        
        self.stdout.write(
            self.style.SUCCESS(
                'Priority multipliers updated successfully!\n\n'
                'Updated values:\n'
                f"• Low: {os.environ.get('PRIORITY_MULTIPLIER_LOW', '1.0')}x ({int((float(os.environ.get('PRIORITY_MULTIPLIER_LOW', '1.0'))-1)*100)}% bonus)\n"
                f"• Medium: {os.environ.get('PRIORITY_MULTIPLIER_MEDIUM', '1.05')}x ({int((float(os.environ.get('PRIORITY_MULTIPLIER_MEDIUM', '1.05'))-1)*100)}% bonus)\n"
                f"• High: {os.environ.get('PRIORITY_MULTIPLIER_HIGH', '1.2')}x ({int((float(os.environ.get('PRIORITY_MULTIPLIER_HIGH', '1.2'))-1)*100)}% bonus)"
            )
        ) 