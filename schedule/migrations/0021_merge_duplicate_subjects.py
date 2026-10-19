"""Один предмет — одна дисципліна на всі курси.

Майстерні заносилися зі своїми предметами, хоча це ті самі дисципліни, що й
у «Майстрі» («Вода у виробництві віскі» = «Вода»). Тут вони зливаються з
предметами «Майстра»; у кожному курсі лишаються свої номер, модуль, години
й лектор (`CourseSubject.teachers`).

1. Кожен рядок програми запам'ятовує, хто веде предмет у цьому курсі, —
   доки предмети ще не злиті, це рівно каталог предмета.
2. Дублікат переходить у предмет «Майстра». Якщо курс уже має той предмет
   (у фруктових «Асортимент сировини» й «Переробка сировини» обидва
   стають «Сировиною, що містить цукор»), рядки зливаються: години
   додаються, номери пишуться через кому.
3. Тестові предмети (лектор — тестовий Петро Іваненко) видаляються, якщо їх
   не викладають у жодній групі.

Предмета, якого немає, міграція просто не чіпає.
"""

from decimal import Decimal

from django.db import migrations

SUGAR = ('Сировина, що містить цукор (цукровий буряк, меласа, цукрова тростина, '
         'цукрове сорго, цукор), плоди, ягоди, соки')
FERMENTATION = 'Спиртове бродіння, вступ до біохімії та мікробіології'
DISTILLATION = 'Техніка та технологія дистиляції'
DESIGN = 'Проектування віскікурні (дистилерії): будівництво, проект, документація'
TASTINGS = 'Дегустації та сенсорні тренування різних видів напоїв'

# дублікат -> предмет «Майстра»
MERGES = {
    'Вода у виробництві віскі': 'Вода',
    'Спиртове бродіння зернових: режими, дріжджі. Практика в лабораторії': FERMENTATION,
    'Сировина й дріжджі для віскі: солод, затирання, ферментація, дистиляція зернових '
    'і солодових бражок': FERMENTATION,
    'Крохмалевмісна сировина й підготовка до зброджування: помол, гідроліз, затирання':
        'Сировина, що містить крохмаль (зерно, солод)',
    'Фруктова сировина — яблуко, слива, виноград: аналіз, обробка м’язги, підготовка '
    'сусла до бродіння': SUGAR,
    'Асортимент і характеристика сировини: фрукти та виноград': SUGAR,
    'Особливості переробки фруктової сировини': SUGAR,
    'Дистиляція віскі: теорія й перекурка солодової бражки': DISTILLATION,
    'Дистиляція зернових бражок: перегонна й дистиляційна колони, обладнання': DISTILLATION,
    'Виготовлення фруктових дистилятів': DISTILLATION,
    'Витримка в бочці та з альтернативою. Помилки при витримці': 'Витримка в бочці',
    'Витримка віскі в бочці та альтернатива': 'Витримка в бочці',
    'Витримка фруктових дистилятів': 'Витримка в бочці',
    'Організація виробництва віскі': DESIGN,
    'Вимоги до приміщення бродильного цеху: технологічна схема, обладнання': DESIGN,
    'Контроль зброджування крохмалевмісної сировини, аналіз бражки, вихід спирту':
        'Визначення показників під час спиртового бродіння та аналіз дозрілої бражки. '
        'Аналіз стану дріжджів та визначення інфекції',
    'Контроль бродіння фруктового сусла, якість виноматеріалів для дистиляції':
        'Аналіз показників якості цукровмісної сировини та напівпродуктів для дистиляції',
    'Водка й зернові дистиляти. Порівняльна дегустація': 'Водка',
    'Коньяк, арманьяк, бренді. Порівняльна дегустація «Великої четвірки»':
        'Коньяк, бренди, арманьяк',
    'Віскі світу: індустрія, стилі, етикетка, регіони Скотчу': 'Солодові та Віскі',
    'Віскі світу: історія, класифікація, стилі, ринок і закони. Дегустація': 'Солодові та Віскі',
    # та сама тема, інший лектор — лектор лишається в рядку програми свого курсу
    'Основи сенсорного аналізу фруктових дистилятів':
        'Основи дегустації продукції. Вимоги до дегустаторів',
    'Сенсорний аналіз, профіль віскі': TASTINGS,
    'Сенсорний аналіз зернових дистилятів і горілки. Сортування дистилятів': TASTINGS,
    'Джин: історія, стилі, класифікація. Дегустація світових брендів': 'Джини',
    'Джин: методи виробництва, історія, суміші ботанікалів': 'Джини',
    'Ром: історія, технологія, стилі': 'Ром, текіла',
    'Агавові: регіони, законодавство, категорії витримки': 'Ром, текіла',
    'Лікери й біттери: методи виробництва, ключові бренди':
        'Вермут, біттери, мацерати, ботанічні настої',
    'Розділення сумішей: домішки бражок, леткі домішки, ректифікація спирту':
        'Теоретичні основи розділення багатокомпонентних сумішей',
    'Купажування віскі. Дегустація й аналіз напоїв': 'Купажування',
    'Купажування й корегування витриманих напоїв': 'Купажування',
}

TEST_SUBJECTS = ['Історія дистилятів', 'Сенсорний аналіз', 'Крохмаловмістна сировина']


def _number(code):
    """«2.10» після «2.9», а не перед «2.2»."""
    return [int(part) if part.isdigit() else part for part in code.split('.')]


def merge(apps, schema_editor):
    Subject = apps.get_model('schedule', 'Subject')
    CourseSubject = apps.get_model('schedule', 'CourseSubject')
    GroupSubject = apps.get_model('schedule', 'GroupSubject')

    # 1. Хто веде в кожному курсі — поки що рівно каталог предмета.
    for link in CourseSubject.objects.prefetch_related('subject__teachers'):
        if not link.teachers.exists():
            link.teachers.set(link.subject.teachers.all())

    # 2. Дублікати — у предмети «Майстра».
    for name, target_name in MERGES.items():
        duplicate = Subject.objects.filter(name=name).first()
        target = Subject.objects.filter(name=target_name).first()
        if duplicate is None or target is None or duplicate.pk == target.pk:
            continue
        for link in CourseSubject.objects.filter(subject=duplicate).order_by('position'):
            same = CourseSubject.objects.filter(course_id=link.course_id, subject=target).first()
            if same is None:
                link.subject = target
                link.save(update_fields=['subject'])
                continue
            if link.hours is not None:
                same.hours = (same.hours or Decimal(0)) + link.hours
            codes = [c for c in (*same.code.split(', '), link.code) if c]
            same.code = ', '.join(sorted(codes, key=_number))
            same.position = min(same.position, link.position)
            same.save(update_fields=['hours', 'code', 'position'])
            same.teachers.add(*link.teachers.all())
            link.delete()
        for taught in GroupSubject.objects.filter(subject=duplicate):
            clash = GroupSubject.objects.filter(
                group_id=taught.group_id, subject=target, start_date=taught.start_date).exists()
            if not clash:
                taught.subject = target
                taught.save(update_fields=['subject'])
        target.teachers.add(*duplicate.teachers.all())
        if not GroupSubject.objects.filter(subject=duplicate).exists():
            duplicate.delete()

    # 3. Тестові предмети — якщо ніде не викладаються.
    Subject.objects.filter(name__in=TEST_SUBJECTS, group_subjects__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0020_teachers_per_course'),
    ]

    operations = [
        migrations.RunPython(merge, migrations.RunPython.noop),
    ]
