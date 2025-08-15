from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_add_task_field_indexes"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS core_task_responsible_status_idx "
                "ON core_task (responsible_id, status);"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS core_task_responsible_status_idx;"
            ),
        ),
    ]


