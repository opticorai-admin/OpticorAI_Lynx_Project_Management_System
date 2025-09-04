from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_alter_task_approval_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='employee_submitted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Employee Submission Timestamp', help_text='When the employee last submitted content for manager evaluation/approval'),
        ),
    ]


