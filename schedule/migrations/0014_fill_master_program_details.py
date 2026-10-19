"""Модулі, години, екскурсія й ставки для вже занесеного «Майстра дистиляції».

На проді програма вже лежить у базі (`import_program`), тож дописуємо до неї
те, що з'явилося в 0013. Заповнюємо лише порожнє — як і сама команда.
Курсу немає (свіжа база, тести) — нічого не робимо: тоді все занесе
`import_program`, і `schedule.programs` тут навіть не імпортується.
"""

from django.db import migrations


def fill(apps, schema_editor):
    Course = apps.get_model('schedule', 'Course')
    Module = apps.get_model('schedule', 'Module')
    CourseSubject = apps.get_model('schedule', 'CourseSubject')
    User = apps.get_model('accounts', 'User')

    from schedule import programs

    course = Course.objects.filter(name=programs.COURSE).first()
    if course is None:
        return

    if course.excursion_price is None:
        course.excursion_price = programs.EXCURSION_PRICE
        course.save(update_fields=['excursion_price'])

    modules = {}
    for position, code, name, module_format in programs.modules():
        modules[code], _ = Module.objects.get_or_create(
            course=course, name=name,
            defaults={'code': code, 'format': module_format, 'position': position})

    for _position, _code, name, module_code, _lecturers, hours in programs.subjects():
        link = CourseSubject.objects.filter(course=course, subject__name=name).first()
        if link is None:
            continue
        if link.module_id is None:
            link.module = modules[module_code]
        if link.hours is None:
            link.hours = hours
        link.save(update_fields=['module', 'hours'])

    for username, rate in programs.RATES.items():
        User.objects.filter(username=username, hourly_rate__isnull=True).update(hourly_rate=rate)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_teacher_hourly_rate'),
        ('schedule', '0013_modules_and_hours'),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
