from django.db import migrations

def create_default_priority_types(apps, schema_editor):
    """Create default priority types if they don't exist"""
    TaskPriorityType = apps.get_model('core', 'TaskPriorityType')
    
    # Create default priority types
    defaults = [
        {'name': 'Low', 'code': 'low', 'multiplier': 1.0, 'sort_order': 1, 'description': 'Low priority tasks'},
        {'name': 'Medium', 'code': 'medium', 'multiplier': 1.0, 'sort_order': 2, 'description': 'Medium priority tasks'},
        {'name': 'High', 'code': 'high', 'multiplier': 1.2, 'sort_order': 3, 'description': 'High priority tasks'},
    ]
    
    for default in defaults:
        TaskPriorityType.objects.get_or_create(
            code=default['code'],
            defaults=default
        )

def create_default_quality_types(apps, schema_editor):
    """Create default quality types based on user requirements"""
    QualityType = apps.get_model('core', 'QualityType')
    
    # Create default quality types according to requirements
    defaults = [
        {'name': 'Poor', 'percentage': 40.0, 'sort_order': 1, 'description': 'Poor quality - 40% or less'},
        {'name': 'Average', 'percentage': 60.0, 'sort_order': 2, 'description': 'Average quality - 40-60%'},
        {'name': 'Good', 'percentage': 80.0, 'sort_order': 3, 'description': 'Good quality - 60-80%'},
        {'name': 'Exceed', 'percentage': 90.0, 'sort_order': 4, 'description': 'Exceed expectations - 80-90%'},
        {'name': 'Exceptional', 'percentage': 100.0, 'sort_order': 5, 'description': 'Exceptional quality - 90-100%'},
    ]
    
    for default in defaults:
        QualityType.objects.get_or_create(
            name=default['name'],
            defaults=default
        )

def create_default_evaluation_settings(apps, schema_editor):
    """Create default task evaluation settings"""
    TaskEvaluationSettings = apps.get_model('core', 'TaskEvaluationSettings')
    
    # Create default settings if none exist
    if not TaskEvaluationSettings.objects.exists():
        TaskEvaluationSettings.objects.create(
            formula_name="Standard Task Evaluation Formula",
            use_quality_score=True,
            use_priority_multiplier=True,
            use_time_bonus_penalty=True,
            use_manager_closure_penalty=True,
            early_completion_bonus_per_day=1.0,
            max_early_completion_bonus=5.0,
            late_completion_penalty_per_day=2.0,
            max_late_completion_penalty=20.0,
            manager_closure_penalty=20.0,
            evaluation_formula="Final Score = (Quality Score × Priority Multiplier) ± Time Bonus/Penalty ± Manager Closure Penalty"
        )

def reverse_migration(apps, schema_editor):
    """Reverse the migration (not needed for rollback)"""
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_taskprioritytype_alter_qualitytype_options_and_more'),
    ]

    operations = [
        # Create the default data
        migrations.RunPython(create_default_priority_types, reverse_migration),
        migrations.RunPython(create_default_quality_types, reverse_migration),
        migrations.RunPython(create_default_evaluation_settings, reverse_migration),
    ] 