"""«Майстер дистиляції»: групова ціна (1200 €) і вступне слово Катерини
Камишевої перед курсом — новий модуль «0» на початку програми.

Як і 0014: курсу немає (свіжа база, тести) — нічого не робимо, все занесе
`import_program`. Решта програми зсувається на одне місце вниз, щоб
вступне слово стало першим.
"""

from django.db import migrations
from django.db.models import F

INTRO_MODULE = ('0', 'Перед початком курсу')
INTRO_SUBJECT = ('0.1', 'Вступне слово: як проходить курс, випускна робота')


def fill(apps, schema_editor):
    Course = apps.get_model('schedule', 'Course')
    Module = apps.get_model('schedule', 'Module')
    Subject = apps.get_model('schedule', 'Subject')
    CourseSubject = apps.get_model('schedule', 'CourseSubject')
    User = apps.get_model('accounts', 'User')

    course = Course.objects.filter(name='Майстер дистиляції').first()
    if course is None:
        return

    if course.group_price_eur is None:
        course.group_price_eur = 1200
        course.save(update_fields=['group_price_eur'])

    code, name = INTRO_MODULE
    module = Module.objects.filter(course=course, name=name).first()
    if module is None:
        Module.objects.filter(course=course).update(position=F('position') + 1)
        CourseSubject.objects.filter(course=course).update(position=F('position') + 1)
        module = Module.objects.create(course=course, code=code, name=name,
                                       format='online', position=1)

    code, name = INTRO_SUBJECT
    subject, _ = Subject.objects.get_or_create(name=name)
    CourseSubject.objects.get_or_create(
        course=course, subject=subject,
        defaults={'code': code, 'position': 1, 'module': module})
    # Як і `import_program`: предмет дістається лише тому, хто має роль викладача.
    kamysheva = User.objects.filter(username='manager', role_links__role='teacher').first()
    if kamysheva is not None:
        subject.teachers.add(kamysheva)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_teacher_hourly_rate'),
        ('schedule', '0015_group_price_and_euro_rate'),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
