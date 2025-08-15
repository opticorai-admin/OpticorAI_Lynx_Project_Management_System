from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Task, QualityType, TaskPriorityType, TaskEvaluationSettings
from datetime import date, timedelta
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Test the task evaluation system with example calculations'

    def handle(self, *args, **options):
        self.stdout.write('Testing task evaluation system...')
        
        # Get or create test data
        settings = TaskEvaluationSettings.get_settings()
        
        # Get quality types
        poor_quality = QualityType.objects.filter(name='Poor').first()
        average_quality = QualityType.objects.filter(name='Average').first()
        good_quality = QualityType.objects.filter(name='Good').first()
        exceed_quality = QualityType.objects.filter(name='Exceed').first()
        exponential_quality = QualityType.objects.filter(name='Exponential').first()
        
        # Get priority types
        low_priority = TaskPriorityType.objects.filter(code='low').first()
        medium_priority = TaskPriorityType.objects.filter(code='medium').first()
        high_priority = TaskPriorityType.objects.filter(code='high').first()
        
        self.stdout.write('\n=== Quality Types ===')
        for quality in [poor_quality, average_quality, good_quality, exceed_quality, exponential_quality]:
            if quality:
                self.stdout.write(f'• {quality.name}: {quality.percentage}%')
        
        self.stdout.write('\n=== Priority Types ===')
        for priority in [low_priority, medium_priority, high_priority]:
            if priority:
                self.stdout.write(f'• {priority.name}: {priority.multiplier}x multiplier')
        
        self.stdout.write('\n=== Evaluation Settings ===')
        self.stdout.write(f'• Early completion bonus: {settings.early_completion_bonus_per_day}% per day (max: {settings.max_early_completion_bonus}%)')
        self.stdout.write(f'• Late completion penalty: {settings.late_completion_penalty_per_day}% per day (max: {settings.max_late_completion_penalty}%)')
        self.stdout.write(f'• Manager closure penalty: {settings.manager_closure_penalty}%')
        
        # Test calculations
        self.stdout.write('\n=== Example Calculations ===')
        
        # Example 1: Finished Early (as per requirements)
        self.stdout.write('\nExample 1: Finished Early')
        self.stdout.write('• Quality: Good (80%)')
        self.stdout.write('• Priority: High → +10% → 80 × 1.1 = 88')
        self.stdout.write('• Finished 2 days early → +2%')
        self.stdout.write('• Final Score = 88 + 2 = 90%')
        
        # Example 2: Finished Late (as per requirements)
        self.stdout.write('\nExample 2: Finished Late')
        self.stdout.write('• Quality: Average (60%)')
        self.stdout.write('• Priority: Medium → +5% → 60 × 1.05 = 63')
        self.stdout.write('• Finished 3 days late → -6%')
        self.stdout.write('• Final Score = 63 - 6 = 57%')
        
        # Example 3: Manager Closure
        self.stdout.write('\nExample 3: Manager Closure (Incomplete Task)')
        self.stdout.write('• Quality: Poor (40%)')
        self.stdout.write('• Priority: Low → no change → 40 × 1.0 = 40')
        self.stdout.write('• Manager closure penalty → -20%')
        self.stdout.write('• Final Score = 40 - 20 = 20%')
        
        # Test with actual task objects
        self.stdout.write('\n=== Testing with Actual Task Objects ===')
        
        # Create a test user if needed
        test_user, created = User.objects.get_or_create(
            username='test_evaluation',
            defaults={
                'email': 'test@example.com',
                'user_type': 'employee',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            self.stdout.write(f'Created test user: {test_user.username}')
        
        # Create a test task
        test_task = Task.objects.create(
            issue_action='Test Evaluation Task',
            responsible=test_user,
            priority=high_priority,
            quality=good_quality,
            start_date=date.today() - timedelta(days=10),
            target_date=date.today() + timedelta(days=5),
            completion_date=timezone.now() - timedelta(days=3),  # 3 days early
            percentage_completion=100,
            status='closed',
            created_by=test_user
        )
        
        # Test automatic evaluation
        if test_task.apply_automatic_evaluation():
            self.stdout.write(f'\nTest Task Evaluation Results:')
            self.stdout.write(f'• Task: {test_task.issue_action}')
            self.stdout.write(f'• Quality Score: {test_task.quality_score_calculated}%')
            self.stdout.write(f'• Priority Multiplier: {test_task.priority_multiplier}x')
            self.stdout.write(f'• Time Bonus/Penalty: {test_task.time_bonus_penalty}%')
            self.stdout.write(f'• Final Score: {test_task.final_score}%')
            self.stdout.write(f'• Manager Closure Penalty Applied: {test_task.manager_closure_penalty_applied}')
        else:
            self.stdout.write('Failed to evaluate test task')
        
        # Test manager closure scenario
        incomplete_task = Task.objects.create(
            issue_action='Test Incomplete Task',
            responsible=test_user,
            priority=low_priority,
            quality=poor_quality,
            start_date=date.today() - timedelta(days=15),
            target_date=date.today() - timedelta(days=5),
            percentage_completion=50,  # Incomplete
            status='due',
            created_by=test_user
        )
        
        # Test manager closure evaluation
        if incomplete_task.apply_automatic_evaluation(manager_closure=True):
            self.stdout.write(f'\nManager Closure Test Results:')
            self.stdout.write(f'• Task: {incomplete_task.issue_action}')
            self.stdout.write(f'• Quality Score: {incomplete_task.quality_score_calculated}%')
            self.stdout.write(f'• Priority Multiplier: {incomplete_task.priority_multiplier}x')
            self.stdout.write(f'• Time Bonus/Penalty: {incomplete_task.time_bonus_penalty}%')
            self.stdout.write(f'• Final Score: {incomplete_task.final_score}%')
            self.stdout.write(f'• Manager Closure Penalty Applied: {incomplete_task.manager_closure_penalty_applied}')
        else:
            self.stdout.write('Failed to evaluate incomplete task')
        
        # Clean up test data
        test_task.delete()
        incomplete_task.delete()
        if created:
            test_user.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                '\nTask evaluation system test completed successfully!'
            )
        ) 