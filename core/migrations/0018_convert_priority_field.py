from django.db import migrations, models
import django.db.models.deletion

def convert_priority_data(apps, schema_editor):
    """Convert existing priority string values to TaskPriorityType foreign keys using raw SQL"""
    # Get the database connection
    db_alias = schema_editor.connection.alias
    
    # First, get the priority type mappings
    TaskPriorityType = apps.get_model('core', 'TaskPriorityType')
    priority_mapping = {}
    for priority_type in TaskPriorityType.objects.using(db_alias).all():
        priority_mapping[priority_type.code] = priority_type.id
    
    # Get default priority ID
    default_priority = TaskPriorityType.objects.using(db_alias).filter(is_active=True).first()
    default_priority_id = default_priority.id if default_priority else None
    
    # Use raw SQL to update the priority field
    with schema_editor.connection.cursor() as cursor:
        # First, add a temporary column
        cursor.execute("ALTER TABLE core_task ADD COLUMN priority_new INTEGER NULL")
        
        # Update the temporary column based on existing priority values
        for priority_code, priority_id in priority_mapping.items():
            cursor.execute(
                "UPDATE core_task SET priority_new = %s WHERE priority = %s",
                [priority_id, priority_code]
            )
        
        # Set default priority for any remaining NULL values
        if default_priority_id:
            cursor.execute(
                "UPDATE core_task SET priority_new = %s WHERE priority_new IS NULL",
                [default_priority_id]
            )
        
        # Drop the old column and rename the new one
        cursor.execute("ALTER TABLE core_task DROP COLUMN priority")
        cursor.execute("ALTER TABLE core_task RENAME COLUMN priority_new TO priority")

def reverse_convert_priority_data(apps, schema_editor):
    """Reverse the priority data conversion"""
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_create_priority_types_and_data'),
    ]

    operations = [
        # Convert the data first
        migrations.RunPython(convert_priority_data, reverse_convert_priority_data),
        
        # Then change the field type
        migrations.AlterField(
            model_name='task',
            name='priority',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='core.taskprioritytype',
                verbose_name='Priority'
            ),
        ),
    ] 