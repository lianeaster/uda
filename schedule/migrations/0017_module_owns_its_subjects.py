"""Програма курсу — це модулі, модуль — предмети.

Видалений модуль тепер забирає свої предмети з програми курсу (CASCADE), а
не лишає їх «поза модулями». Предмети, що вже стоять без модуля, нікуди не
зникають: курс без жодного модуля отримує модуль «1. Програма курсу», курс
із модулями — модуль «Без модуля» наприкінці, звідки менеджер розкладе їх.
"""

import django.db.models.deletion
from django.db import migrations, models


def gather_loose_subjects(apps, schema_editor):
    Course = apps.get_model('schedule', 'Course')
    Module = apps.get_model('schedule', 'Module')
    CourseSubject = apps.get_model('schedule', 'CourseSubject')

    for course in Course.objects.filter(program__module__isnull=True).distinct():
        modules = Module.objects.filter(course=course)
        if modules.exists():
            last = modules.aggregate(models.Max('position'))['position__max'] or 0
            module, _ = Module.objects.get_or_create(
                course=course, name='Без модуля', defaults={'position': last + 1})
        else:
            module = Module.objects.create(
                course=course, code='1', name='Програма курсу', position=1)
        CourseSubject.objects.filter(course=course, module__isnull=True).update(module=module)


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0016_master_intro_and_group_price'),
    ]

    operations = [
        migrations.RunPython(gather_loose_subjects, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='coursesubject',
            name='module',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='program', to='schedule.module', verbose_name='Модуль'),
        ),
    ]
