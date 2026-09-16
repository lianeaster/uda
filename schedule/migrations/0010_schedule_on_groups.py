"""Розклад переїжджає на групи: курс/предмет/викладач більше не зберігаються.

Записи, зроблені до появи груп, видаляються: у них немає групи, а стара
семантика («бронь курсу» без групи) більше не існує. Відкату для них немає —
видалені рядки не повернути.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def drop_entries_without_group(apps, schema_editor):
    ScheduleEntry = apps.get_model('schedule', 'ScheduleEntry')
    ScheduleEntry.objects.filter(group__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0009_drop_role_limits'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(drop_entries_without_group, migrations.RunPython.noop),
        migrations.AddField(
            model_name='scheduleentry',
            name='status',
            field=models.CharField(
                choices=[('proposed', 'На розгляді'), ('accepted', 'Прийнято'),
                         ('rejected', 'Відхилено')],
                default='accepted', max_length=10, verbose_name='Стан'),
        ),
        migrations.AddField(
            model_name='scheduleentry',
            name='reviewed_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_schedule_entries', to=settings.AUTH_USER_MODEL,
                verbose_name='Розглянув(ла)'),
        ),
        migrations.AddField(
            model_name='scheduleentry',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Коли розглянуто'),
        ),
        migrations.AlterField(
            model_name='scheduleentry',
            name='group',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='schedule_entries', to='schedule.group',
                verbose_name='Група'),
        ),
        migrations.AlterField(
            model_name='scheduleentry',
            name='group_subject',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='schedule_entries', to='schedule.groupsubject',
                help_text='Порожньо — день заброньовано під курс цілком.',
                verbose_name='Предмет у групі'),
        ),
        migrations.RemoveField(model_name='scheduleentry', name='title'),
        migrations.RemoveField(model_name='scheduleentry', name='teacher'),
        migrations.RemoveField(model_name='scheduleentry', name='course'),
        migrations.RemoveField(model_name='scheduleentry', name='subject'),
    ]
