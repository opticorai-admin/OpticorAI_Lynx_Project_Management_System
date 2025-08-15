from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import TaskPriorityType, QualityType, TaskEvaluationSettings
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up the default task evaluation system with priority types and quality types'

    def handle(self, *args, **options):
        self.stdout.write('Setting up task evaluation system...')
        
        # Create default priority types (configurable via env)
        low_mult = float(os.environ.get('PRIORITY_MULTIPLIER_LOW', '1.0'))
        med_mult = float(os.environ.get('PRIORITY_MULTIPLIER_MEDIUM', '1.05'))
        high_mult = float(os.environ.get('PRIORITY_MULTIPLIER_HIGH', '1.2'))
        priority_types = [
            {
                'name': 'Low',
                'code': 'low',
                'multiplier': low_mult,
                'description': f'Low priority tasks - {int((low_mult-1)*100)}% bonus multiplier' if low_mult != 1.0 else 'Low priority tasks - no bonus multiplier (0%)',
                'sort_order': 1
            },
            {
                'name': 'Medium',
                'code': 'medium',
                'multiplier': med_mult,
                'description': f'Medium priority tasks - {int((med_mult-1)*100)}% bonus multiplier',
                'sort_order': 2
            },
            {
                'name': 'High',
                'code': 'high',
                'multiplier': high_mult,
                'description': f'High priority tasks - {int((high_mult-1)*100)}% bonus multiplier',
                'sort_order': 3
            }
        ]
        
        for priority_data in priority_types:
            priority_type, created = TaskPriorityType.objects.get_or_create(
                code=priority_data['code'],
                defaults=priority_data
            )
            if created:
                self.stdout.write(f'Created priority type: {priority_type.name}')
            else:
                self.stdout.write(f'Priority type already exists: {priority_type.name}')
        
        # Create default quality types
        # Create default quality types (configurable via env)
        q_poor = float(os.environ.get('QUALITY_POOR_PERCENTAGE', '40.0'))
        q_avg = float(os.environ.get('QUALITY_AVERAGE_PERCENTAGE', '60.0'))
        q_good = float(os.environ.get('QUALITY_GOOD_PERCENTAGE', '80.0'))
        q_exceed = float(os.environ.get('QUALITY_EXCEED_PERCENTAGE', '90.0'))
        q_exceptional = float(os.environ.get('QUALITY_EXCEPTIONAL_PERCENTAGE', '100.0'))
        quality_types = [
            {
                'name': 'Poor',
                'percentage': q_poor,
                'description': f'Poor quality work - ≤{q_poor:.0f}% base score',
                'sort_order': 1
            },
            {
                'name': 'Average',
                'percentage': q_avg,
                'description': f'Average quality work - range up to {q_avg:.0f}%',
                'sort_order': 2
            },
            {
                'name': 'Good',
                'percentage': q_good,
                'description': f'Good quality work - around {q_good:.0f}%',
                'sort_order': 3
            },
            {
                'name': 'Exceed',
                'percentage': q_exceed,
                'description': f'Exceed expectations - around {q_exceed:.0f}%',
                'sort_order': 4
            },
            {
                'name': 'Exceptional',
                'percentage': q_exceptional,
                'description': f'Exceptional quality - up to {q_exceptional:.0f}%',
                'sort_order': 5
            }
        ]
        
        # Get or create admin user for quality type creation
        admin_user = User.objects.filter(user_type='admin').first()
        if not admin_user:
            self.stdout.write('Warning: No admin user found. Creating quality types without created_by field.')
        
        for quality_data in quality_types:
            quality_type, created = QualityType.objects.get_or_create(
                name=quality_data['name'],
                defaults={
                    **quality_data,
                    'created_by': admin_user
                }
            )
            if created:
                self.stdout.write(f'Created quality type: {quality_type.name} ({quality_type.percentage}%)')
            else:
                self.stdout.write(f'Quality type already exists: {quality_type.name} ({quality_type.percentage}%)')
        
        # Update evaluation settings
        settings, created = TaskEvaluationSettings.objects.get_or_create(
            defaults={
                'formula_name': 'Enhanced Task Evaluation Formula',
                'use_quality_score': True,
                'use_priority_multiplier': True,
                'use_time_bonus_penalty': True,
                'use_manager_closure_penalty': True,
                'early_completion_bonus_per_day': 1.0,
                'max_early_completion_bonus': 5.0,
                'late_completion_penalty_per_day': 2.0,
                'max_late_completion_penalty': 20.0,
                'manager_closure_penalty': 20.0,
                'evaluation_formula': 'Final Score = (Quality Score × Priority Multiplier) ± Time Bonus/Penalty ± Manager Closure Penalty'
            }
        )
        
        if created:
            self.stdout.write('Created evaluation settings')
        else:
            self.stdout.write('Evaluation settings already exist')
        
        try:
            example_quality = q_good
            example_mult = high_mult
            base_calc = example_quality * example_mult
            final_calc = base_calc + 2
            self.stdout.write(
                self.style.SUCCESS(
                    'Task evaluation system setup complete!\n\n'
                    'Example calculation (based on current defaults/env):\n'
                    f'• Quality: Good ({example_quality:.0f}%)\n'
                    f'• Priority: High → × {example_mult} → {example_quality:.0f} × {example_mult} = {base_calc:.0f}\n'
                    '• Finished 2 days early → +2%\n'
                    f'• Final Score = {base_calc:.0f} + 2 = {final_calc:.0f}%'
                )
            )
        except Exception:
            self.stdout.write(self.style.SUCCESS('Task evaluation system setup complete!'))