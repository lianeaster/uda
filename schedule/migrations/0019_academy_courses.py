"""Інші курси Академії на платформі: майстерні, Spirit Course, зернові,
бродіння й онлайн-потік фруктових — з модулями, предметами, годинами й
лекторами (`schedule.workshops`), плюс код «master» для «Майстра».

Як і 0014/0016: «Майстра» в базі немає (свіжа база, тести) — нічого не
робимо, усе занесе `import_program`.
"""

from django.db import migrations


def fill(apps, schema_editor):
    Course = apps.get_model('schedule', 'Course')
    master = Course.objects.filter(name='Майстер дистиляції').first()
    if master is None:
        return
    if not master.code:
        master.code = 'master'
        master.save(update_fields=['code'])

    from core import content
    from schedule import workshops

    workshops.apply(
        Course,
        apps.get_model('schedule', 'Module'),
        apps.get_model('schedule', 'Subject'),
        apps.get_model('schedule', 'CourseSubject'),
        apps.get_model('accounts', 'User'),
        descriptions={c['id']: c['text'] for c in content.COURSES},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_teacher_hourly_rate'),
        ('schedule', '0018_course_code'),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
