"""Предмет може входити в програми кількох курсів.

Курс, номер і позиція переходять із самого предмета в `CourseSubject` —
рядок програми конкретного курсу. Наявні предмети переносяться як є: кожен
стає рядком програми свого курсу з тим самим номером і місцем.
"""

from django.db import migrations, models
import django.db.models.deletion


def move_course_to_program(apps, schema_editor):
    Subject = apps.get_model('schedule', 'Subject')
    CourseSubject = apps.get_model('schedule', 'CourseSubject')
    CourseSubject.objects.bulk_create([
        CourseSubject(course_id=s.course_id, subject_id=s.pk, code=s.code, position=s.position)
        for s in Subject.objects.exclude(course__isnull=True)
    ])


def move_program_back(apps, schema_editor):
    Subject = apps.get_model('schedule', 'Subject')
    CourseSubject = apps.get_model('schedule', 'CourseSubject')
    # Назад лізе лише перший курс предмета — у старій схемі місця на решту немає.
    for link in CourseSubject.objects.order_by('subject_id', 'course__name'):
        Subject.objects.filter(pk=link.subject_id, course__isnull=True).update(
            course_id=link.course_id, code=link.code, position=link.position)


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0011_proposal_seen'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='description',
            field=models.TextField(blank=True, verbose_name='Опис'),
        ),
        migrations.CreateModel(
            name='CourseSubject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(blank=True, max_length=20, verbose_name='Номер у програмі')),
                ('position', models.PositiveIntegerField(default=0, verbose_name='Порядок у програмі')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='program', to='schedule.course', verbose_name='Курс')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='course_links', to='schedule.subject', verbose_name='Предмет')),
            ],
            options={
                'verbose_name': 'Предмет у програмі курсу',
                'verbose_name_plural': 'Предмети в програмах курсів',
                'ordering': ['course__name', 'position', 'subject__name'],
                'constraints': [models.UniqueConstraint(fields=('course', 'subject'), name='unique_course_subject')],
            },
        ),
        migrations.RunPython(move_course_to_program, move_program_back),
        migrations.AlterModelOptions(
            name='subject',
            options={'ordering': ['name'], 'verbose_name': 'Предмет', 'verbose_name_plural': 'Предмети'},
        ),
        migrations.RemoveField(model_name='subject', name='course'),
        migrations.RemoveField(model_name='subject', name='code'),
        migrations.RemoveField(model_name='subject', name='position'),
        migrations.AddField(
            model_name='subject',
            name='courses',
            field=models.ManyToManyField(blank=True, related_name='subjects', through='schedule.CourseSubject', to='schedule.course', verbose_name='Курси'),
        ),
    ]
