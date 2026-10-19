"""Програми курсів Академії, крім «Майстра дистиляції» (його — `schedule.programs`).

Джерело — сторінки курсів на старому сайті (distillingacademy.com.ua/courses/…,
жовтень 2026) і, для фруктових дистилятів, програма онлайн-потоку 21–30.10.2026.
Групова ціна (€ з людини) — як на сайті.

Години й хто що веде — **чернетка**, її треба звірити з Академією:
- офлайн-день — 8 годин навчання; онлайн-тема — 3 години (кратно 3);
- день по лекторах розписано на сайті лише у «Віскі»; в інших курсах
  відомий лише список лекторів, тож розподіл годин між ними прикинуто;
- Spirit Course — авторський курс Івана Бачуріна, усі години поставлено йому;
- у «Майстерні джину» програми на сайті немає — дні складено з того, що
  курс обіцяє розглянути, по одному лектору на день;
- онлайн-потік фруктових дистилятів має 5 вечорів на 8 тем: якщо вечір
  триває 3 години, а не кожна тема, годин буде 15, а не 24;
- групової ціни онлайн-потоку фруктових немає (445 € на сайті — офлайн).

Курс (модуль, предмет), який уже є на платформі, не переписується — далі
його правлять там. Лектори — за логіном на платформі; хто не викладач, той
предмета не отримує, як і в `import_program`.

Тема, яка є і в «Майстрі», стоїть тут під назвою предмета «Майстра»: один
предмет на всі курси, а номер, години й лектор — свої в кожному курсі.

Рядок предмета: (номер, назва, логіни лекторів, години).
"""

from decimal import Decimal

# Предмети «Майстра», у які стають теми майстерень (одна дисципліна — один
# предмет на всі курси; див. міграцію 0021).
WATER = 'Вода'
FERMENTATION = 'Спиртове бродіння, вступ до біохімії та мікробіології'
STARCH = 'Сировина, що містить крохмаль (зерно, солод)'
SUGAR = ('Сировина, що містить цукор (цукровий буряк, меласа, цукрова тростина, '
         'цукрове сорго, цукор), плоди, ягоди, соки')
DISTILLATION = 'Техніка та технологія дистиляції'
SEPARATION = 'Теоретичні основи розділення багатокомпонентних сумішей'
CASK = 'Витримка в бочці'
BLENDING = 'Купажування'
DESIGN = 'Проектування віскікурні (дистилерії): будівництво, проект, документація'
LAB_FERMENTATION = ('Визначення показників під час спиртового бродіння та аналіз дозрілої '
                    'бражки. Аналіз стану дріжджів та визначення інфекції')
LAB_SUGAR = 'Аналіз показників якості цукровмісної сировини та напівпродуктів для дистиляції'
TASTING_BASICS = 'Основи дегустації продукції. Вимоги до дегустаторів'
TASTINGS = 'Дегустації та сенсорні тренування різних видів напоїв'
WHISKY = 'Солодові та Віскі'
VODKA = 'Водка'
BRANDY = 'Коньяк, бренди, арманьяк'
RUM = 'Ром, текіла'
GIN = 'Джини'
VERMOUTH = 'Вермут, біттери, мацерати, ботанічні настої'

BACHURIN = 'ivan-bachurin'
RAZJABOV = 'tymur-razjabov'
TKACHENKO = 'lyubov-tkachenko'
BILKO = 'maryna-bilko'
KOROLYUK = 'kostyantyn-korolyuk'
CHEKHUN = 'maryna-chekhun'
KEPKANOV = 'yury-kepkanov'
BEDA = 'volodymyr-beda'
PRYDA = 'andre-pryda'
GROMOV = 'oleg-gromov'
RYABTSEV = 'olexandr-ryabtsev'
UMANSKYI = 'o-umanskyi'

COURSES = [
    {
        'code': 'whisky',
        'name': 'Майстерня віскі та солодові дистиляти',
        'group_price_eur': 580,
        'modules': [
            ('1', 'День 1. Історія віскі світу', 'offline', [
                ('1.1', WHISKY, [BACHURIN], 8),
            ]),
            ('2', 'День 2. Сировина та дріжджі', 'offline', [
                ('2.1', FERMENTATION, [TKACHENKO], 8),
            ]),
            ('3', 'День 3. Дистиляція, витримка та дозрівання', 'offline', [
                ('3.1', DISTILLATION, [KOROLYUK], 3),
                ('3.2', WATER, [CHEKHUN], 1),
                ('3.3', CASK, [KEPKANOV], 1),
                ('3.4', DESIGN, [BEDA], 1),
                ('3.5', TASTINGS, [BILKO], 2),
            ]),
            ('4', 'День 4. Купажування', 'offline', [
                ('4.1', BLENDING, [BACHURIN], 8),
            ]),
        ],
    },
    {
        'code': 'ferm',
        'name': 'Правила спиртового бродіння',
        'group_price_eur': 395,
        'modules': [
            ('1', 'День 1. Крохмалевмісна сировина', 'offline', [
                ('1.1', 'Крохмалевмісна сировина: контроль якості, підготовка до зброджування, '
                        'оцукрювання, дріжджі й живлення', [TKACHENKO], 8),
            ]),
            ('2', 'День 2. Фруктова сировина. Вимоги до приміщення', 'offline', [
                ('2.1', SUGAR, [BILKO], 6),
                ('2.2', DESIGN, [BEDA], 2),
            ]),
            ('3', 'День 3. Контроль бродіння', 'offline', [
                ('3.1', LAB_FERMENTATION, [TKACHENKO], 4),
                ('3.2', LAB_SUGAR, [BILKO], 4),
            ]),
        ],
    },
    {
        'code': 'aging',
        'name': 'Майстерня витримки',
        'group_price_eur': 395,
        'modules': [
            ('1', 'День 1. Бочка та альтернатива', 'offline', [
                ('1.1', 'Бочка: технологія виробництва, типи дуба, об’єми, обжарка. '
                        'Рекомендації Seguin Moreau', [PRYDA], 4),
                ('1.2', 'Логістика, складування й обслуговування бочок. Як обрати бочку '
                        'чи альтернативу', [KEPKANOV], 4),
            ]),
            ('2', 'День 2. Технологія витримки', 'offline', [
                ('2.1', CASK, [KEPKANOV, BILKO], 5),
                ('2.2', BLENDING, [BACHURIN], 3),
            ]),
            ('3', 'День 3. Дегустація та аналіз', 'offline', [
                ('3.1', 'Дегустація, дослідження й аналіз напоїв студентів', [BACHURIN], 8),
            ]),
        ],
    },
    {
        'code': 'spirit',
        'name': 'Спецкурс-інтенсив Spirit Course',
        'group_price_eur': 670,
        'modules': [
            ('1', 'Технологія та велика родина міцного алкоголю', 'offline', [
                ('1.1', 'Технологія дистиляції й витримки: обладнання, сировина, методи',
                 [BACHURIN], 3),
                ('1.2', 'Велика родина міцного алкоголю: категорії, світовий ринок, ключові гравці',
                 [BACHURIN], 2),
            ]),
            ('2', 'Категорії міцних напоїв', 'offline', [
                ('2.1, 2.2', RUM, [BACHURIN], 4),       # агавові й ром
                ('2.3', GIN, [BACHURIN], 2),
                ('2.4', 'Кальвадос: історія й стилі', [BACHURIN], 2),
                ('2.5', BRANDY, [BACHURIN], 3),
                ('2.6', VODKA, [BACHURIN], 3),
                ('2.7', WHISKY, [BACHURIN], 4),
                ('2.8', VERMOUTH, [BACHURIN], 2),
            ]),
            ('3', 'Дегустація та іспит', 'offline', [
                ('3.1', 'Дегустація понад 100 зразків: смаковий і ароматний профіль', [BACHURIN], 5),
                ('3.2', 'Іспит Spirit Course: теорія й практика', [BACHURIN], 2),
            ]),
        ],
    },
    {
        'code': 'grain',
        'name': 'Зернові дистиляти / горілка',
        # Так курс могли завести на платформі раніше — знайдемо й перейменуємо.
        'aliases': ['Зернові дистиляти'],
        'group_price_eur': 445,
        'modules': [
            ('1', 'Сировина й бродіння', 'offline', [
                ('1.1', STARCH, [KOROLYUK], 4),
                ('1.2', FERMENTATION, [TKACHENKO], 4),
            ]),
            ('2', 'Дистиляція й ректифікація', 'offline', [
                ('2.1', DISTILLATION, [KOROLYUK], 4),
                ('2.2', SEPARATION, [KOROLYUK], 4),
            ]),
            ('3', 'Горілка', 'offline', [
                ('3.1', 'Основа для горілки й перетворення НДРФ на горілку', [KOROLYUK], 4),
                ('3.2', 'Контроль якості дистиляції. Практика в лабораторії', [KOROLYUK], 2),
                ('3.3', 'Проєктування дистилерії зернових дистилятів', [KOROLYUK], 2),
            ]),
            ('4', 'Витримка, категорії й дегустація', 'offline', [
                ('4.1', 'Витримка зернових дистилятів і вода для напоїв', [KOROLYUK], 2),
                ('4.2', 'Зернові дистиляти й горілка: категорії та стилі', [RAZJABOV], 2),
                ('4.3', TASTINGS, [BACHURIN], 4),
            ]),
        ],
    },
    {
        'code': 'gin',
        'name': 'Майстерня джину та настоянок',
        'group_price_eur': 445,
        'modules': [
            ('1', 'День 1. Історія та класифікація джину', 'offline', [
                ('1.1', GIN, [RAZJABOV], 8),
            ]),
            ('2', 'День 2. Методи виробництва', 'offline', [
                ('2.1', 'Методи виробництва джину: мацерація, парова інфузія, ботанічний спирт',
                 [KOROLYUK], 4),
                ('2.2', 'Лабораторні й виробничі потужності для виробництва джину', [KOROLYUK], 4),
            ]),
            ('3', 'День 3. Ботанічна рецептура', 'offline', [
                ('3.1', 'Розроблення ботанічної рецептури джину', [RYABTSEV], 8),
            ]),
            ('4', 'День 4. Оцінка ботанікалів і настоянки', 'offline', [
                ('4.1', 'Оцінка ботанічної суміші й дистилятів. Вермути й міцні настоянки',
                 [GROMOV], 8),
            ]),
        ],
    },
    {
        'code': 'fruit',
        'name': 'Майстерня фруктових дистилятів та бренді',
        'group_price_eur': None,
        'modules': [
            ('1', 'Сировина та підготовка до бродіння', 'online', [
                ('1', 'Класифікація плодових дистилятів і стандарти ідентифікації', [BILKO], 3),
                ('2, 3', SUGAR, [BILKO], 6),            # асортимент і переробка сировини
            ]),
            ('2', 'Бродіння та дистиляція', 'online', [
                ('4', 'Зброджування сусла або м’язги', [BILKO], 3),
                ('5', DISTILLATION, [UMANSKYI], 3),
            ]),
            ('3', 'Витримка, сенсорика та постобробка', 'online', [
                ('8', CASK, [KEPKANOV], 3),
                ('6', TASTING_BASICS, [BILKO], 3),
                ('7', 'Постобробка фруктових дистилятів: стабілізація, купажування, розлив',
                 [CHEKHUN], 3),
            ]),
        ],
    },
]


def apply(Course, Module, Subject, CourseSubject, User, descriptions=None):
    """Заносить курси з `COURSES`, чого ще немає. Повертає звіт рядками.

    Приймає класи моделей, щоб те саме могли робити й команда
    `import_program` (справжні моделі), й міграція (історичні).
    `descriptions` — {код: опис} для курсів, у яких опису ще немає.
    """
    report = []
    for data in COURSES:
        names = [data['name'], *data.get('aliases', [])]
        course = Course.objects.filter(name__in=names).order_by('pk').first()
        if course is None:
            course = Course.objects.create(name=data['name'])
            report.append(f'курс «{data["name"]}» створено')
        changes = []
        if course.name != data['name']:
            course.name = data['name']
            changes.append('name')
        for field, value in (('code', data['code']),
                             ('group_price_eur', data['group_price_eur']),
                             ('description', (descriptions or {}).get(data['code']))):
            if value and not getattr(course, field):
                setattr(course, field, value)
                changes.append(field)
        if changes:
            course.save(update_fields=changes)

        last_module = Module.objects.filter(course=course).count()
        last_link = CourseSubject.objects.filter(course=course).count()
        for code, name, module_format, items in data['modules']:
            module = Module.objects.filter(course=course, name=name).first()
            if module is None:
                last_module += 1
                module = Module.objects.create(course=course, code=code, name=name,
                                               format=module_format, position=last_module)
            for subject_code, subject_name, logins, hours in items:
                subject, _ = Subject.objects.get_or_create(name=subject_name)
                teachers = User.objects.filter(username__in=logins, role_links__role='teacher')
                link = CourseSubject.objects.filter(course=course, subject=subject).first()
                if link is None:
                    last_link += 1
                    link = CourseSubject.objects.create(
                        course=course, subject=subject, code=subject_code, module=module,
                        position=last_link, hours=Decimal(str(hours)))
                    link.teachers.set(teachers)
                subject.teachers.add(*teachers)
                missing = set(logins) - set(teachers.values_list('username', flat=True))
                if missing:
                    report.append(f'«{subject_name}»: немає викладача {", ".join(sorted(missing))}')
    return report
