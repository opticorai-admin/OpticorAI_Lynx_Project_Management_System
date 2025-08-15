from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_alter_kpi_options_kpi_description_kpi_is_active_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="start_date",
            field=models.DateField(blank=True, null=True, verbose_name="Start Date", db_index=True),
        ),
        migrations.AlterField(
            model_name="task",
            name="target_date",
            field=models.DateField(blank=True, null=True, verbose_name="Target Date", help_text="Expected completion date set at task creation", db_index=True),
        ),
        migrations.AlterField(
            model_name="task",
            name="close_date",
            field=models.DateField(blank=True, null=True, verbose_name="Close Date", help_text="Actual completion date set by manager during evaluation", db_index=True),
        ),
        migrations.AlterField(
            model_name="task",
            name="status",
            field=models.CharField(blank=True, choices=[('open', 'Open'), ('closed', 'Closed'), ('due', 'Due')], db_index=True, default='open', max_length=10, verbose_name="Status", null=True),
        ),
    ]


