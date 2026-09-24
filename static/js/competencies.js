/* Матриця компетенцій Академії — спільна база для всіх курсів.
   Сторінка: /dashboard/competencies/ (супер-адмін і менеджер).

   Предмети й лектори продубльовано з schedule/programs.py (графік 8-ї групи
   «Майстра дистиляції»), з виправленою нумерацією 8.1/8.2. Склад курсів,
   крім «Майстра», — чернетка за описами на сайті (core/content.py). */
(() => {
  // --- дані: програма курсу (schedule/programs.py, графік 8-ї групи) -------
  const MODULES = [
    { n: '1',  short: 'Вступ',            name: 'Вступна частина', fmt: 'офлайн' },
    { n: '2',  short: 'Категорії напоїв', name: 'Алкогольні напої. Класифікація. Світовий досвід', fmt: 'офлайн' },
    { n: '3',  short: 'Сировина',         name: 'Характеристика сировини, технологія бродіння, основні та допоміжні матеріали', fmt: 'онлайн' },
    { n: '4',  short: 'Дистиляція',       name: 'Технологія дистиляції', fmt: 'офлайн' },
    { n: '5',  short: 'Постобробка',      name: 'Постобробка дистилятів, купажування, стабілізація, розлив', fmt: 'офлайн' },
    { n: '6',  short: 'Сенсорика',        name: 'Сенсорний аналіз. Дегустаційна оцінка', fmt: 'офлайн' },
    { n: '7',  short: 'Лабораторія',      name: 'Лабораторний день', fmt: 'офлайн' },
    { n: '8',  short: 'Витримка',         name: 'Процеси при витримці в бочках, альтернативні методи, регулювання старіння', fmt: 'офлайн' },
    { n: '9',  short: 'Якість',           name: 'Контроль якості, управління ризиками, облік спирту', fmt: 'онлайн' },
    { n: '10', short: 'Бізнес',           name: 'Комерційні основи виробництва та реалізації дистилятів', fmt: 'онлайн' },
  ];

  // Курси й майстер-класи Академії (core/content.py). Глобальна матриця
  // охоплює їх усі; «Майстер дистиляції» — повна програма з предметами.
  const COURSES = [
    { id: 'master',    short: 'Майстер',       name: 'Майстер дистиляції' },
    { id: 'grain',     short: 'Зернові',       name: 'Зернові дистиляти / горілка' },
    { id: 'whisky',    short: 'Віскі',         name: 'Майстерня віскі та солодові дистиляти' },
    { id: 'gin',       short: 'Джин',          name: 'Майстерня джину та настоянок' },
    { id: 'sensory',   short: 'Сенсорика',     name: 'Майстерня сенсорного аналізу' },
    { id: 'aging',     short: 'Витримка',      name: 'Майстерня витримки' },
    { id: 'ferm',      short: 'Бродіння',      name: 'Правила спиртового бродіння' },
    { id: 'fruit',     short: 'Фрукти',        name: 'Майстерня фруктових дистилятів та бренді' },
    { id: 'spirit',    short: 'Spirit Course', name: 'Спецкурс-інтенсив Spirit Course' },
    { id: 'mc-org',    short: 'МК Виробництво', name: 'Майстер-клас «Основи організації виробництва дистилятів»' },
    { id: 'mc-starch', short: 'МК Крохмаль',   name: 'Майстер-клас «Зброджування крохмалевмісної сировини»' },
    { id: 'mc-fruit',  short: 'МК Фрукти',     name: 'Майстер-клас «Зброджування фруктів та винограду»' },
  ];

  // Які курси розвивають компетентність. «Майстер» — за програмою; решта —
  // чернетка за описами курсів на сайті, її треба звірити з програмами.
  const COVERAGE = {
    K1:  ['master', 'grain', 'whisky', 'gin', 'fruit'],
    K2a: ['master', 'grain', 'whisky', 'ferm', 'mc-starch'],
    K2b: ['master', 'fruit', 'ferm', 'mc-fruit'],
    K2c: ['master', 'ferm'],
    K3:  ['master', 'grain', 'whisky', 'ferm', 'fruit'],
    K4:  ['master', 'grain', 'whisky', 'ferm', 'fruit', 'mc-starch', 'mc-fruit'],
    K5:  ['master', 'grain'],
    K6:  ['master', 'grain', 'whisky', 'gin', 'fruit', 'mc-org'],
    K7:  ['master', 'grain', 'whisky', 'gin', 'fruit'],
    K8:  ['master', 'whisky', 'aging', 'fruit'],
    K9:  ['master', 'gin', 'aging'],
    K10: ['master', 'grain', 'gin'],
    BOT: ['gin'],
    C1:  ['master', 'fruit', 'aging', 'sensory', 'spirit'],
    C2:  ['master', 'grain', 'whisky', 'aging', 'sensory', 'spirit'],
    C6:  ['master', 'sensory', 'spirit'],
    C7:  ['master', 'gin', 'sensory', 'spirit'],
    C8:  ['master', 'gin', 'sensory', 'spirit'],
    K12: ['master', 'grain', 'whisky', 'gin', 'sensory', 'aging', 'fruit', 'spirit'],
    K13: ['master', 'ferm'],
    K14: ['master', 'spirit'],
    K15: ['master', 'mc-org'],
    K16: ['master', 'mc-org'],
    K17: ['master'],
    K18: ['master', 'mc-org'],
    K19: ['master'],
  };

  // id -> [модуль, номер у програмі, назва, викладачі]
  const SUBJECTS = {
    '1.1':  ['1', '1.1', 'Техніка безпеки на виробництві дистилятів', ['Расулов']],
    '2.1':  ['2', '2.1', 'Плодові та фруктові дистиляти', ['Тимур Ражабов']],
    '2.2':  ['2', '2.2', 'Солодові та віскі', ['Іван Бачурін']],
    '2.3':  ['2', '2.3', 'Зернові дистиляти', ['Іван Бачурін']],
    '2.4':  ['2', '2.4', 'Водка', ['Іван Бачурін']],
    '2.5':  ['2', '2.5', 'Коньяк, бренді, арманьяк', ['Іван Бачурін']],
    '2.6':  ['2', '2.6', 'Ром, текіла', ['Тимур Ражабов']],
    '2.7':  ['2', '2.7', 'Джини', ['Тимур Ражабов']],
    '2.8':  ['2', '2.8', 'Вермут, біттери, мацерати, ботанічні настої', ['Тимур Ражабов']],
    '3.1':  ['3', '3.1', 'Вода', ['Марина Чехун']],
    '3.2':  ['3', '3.2', 'Спиртове бродіння, вступ до біохімії та мікробіології', ['Любов Ткаченко']],
    '3.3':  ['3', '3.3', 'Цукровмісна сировина: буряк, меласа, тростина, сорго, цукор, плоди, ягоди, соки', ['Марина Білько']],
    '3.4':  ['3', '3.4', 'Крохмалевмісна сировина: зерно, солод', ['Костянтин Королюк']],
    '3.5':  ['3', '3.5', 'Мед', ['Наташа Кравчук']],
    '3.6':  ['3', '3.6', 'Виноград, виноградарство', ['Марина Білько']],
    '4.1':  ['4', '4.1', 'Теоретичні основи розділення багатокомпонентних сумішей', ['В. П. Ковальчук']],
    '4.2':  ['4', '4.2', 'Обладнання цехів дистиляції', ['А. Мушаков', 'О. Уманський']],
    '4.3':  ['4', '4.3', 'Техніка та технологія дистиляції', ['Костянтин Королюк', 'О. Уманський']],
    '5.1':  ['5', '5.1', 'Стабілізація та фільтрація напоїв', ['Костянтин Королюк']],
    '5.2':  ['5', '5.2', 'Купажування', ['Марина Чехун']],
    '6.1':  ['6', '6.1', 'Основи дегустації продукції. Вимоги до дегустаторів', ['Марина Чехун']],
    '6.2':  ['6', '6.2', 'Організація сенсорного аналізу: лабораторія, продукти, посуд', ['Марина Чехун']],
    '6.3':  ['6', '6.3', 'Основні методи сенсорного аналізу', ['Марина Чехун']],
    '6.4':  ['6', '6.4', 'Дегустації та сенсорні тренування різних видів напоїв', ['Марина Чехун']],
    '7.1':  ['7', '7.1', 'Фізико-хімічні показники якості води, дистилятів і напоїв', ['Марина Чехун']],
    '7.2':  ['7', '7.2', 'Показники бродіння, аналіз дозрілої бражки, стан дріжджів та інфекції', ['Любов Ткаченко']],
    '7.3':  ['7', '7.3', 'Аналіз цукровмісної сировини та напівпродуктів для дистиляції', ['Марина Білько']],
    '8.1':  ['8', '8.1', 'Альтернативна витримка', ['Юрій Кепканов']],
    '8.2':  ['8', '8.2', 'Витримка в бочці', ['Юрій Кепканов', 'Марина Білько']],
    '9.1':  ['9', '9.1', 'Класифікація міцних алкогольних напоїв в Україні та ЄС', ['Олена Назаренко']],
    '9.2':  ['9', '9.2', 'Управління якістю та безпечністю харчової продукції', ['Оксана Вітряк']],
    '10.1': ['10', '10.1', 'Проєктування віскікурні: будівництво, проєкт, документація', ['Володимир Бєда']],
    '10.2': ['10', '10.2', 'Менеджмент відходів', ['Костянтин Королюк']],
    '10.3': ['10', '10.3', 'Генеральний план, будівельна частина', ['Володимир Бєда']],
    '10.4': ['10', '10.4', 'Законодавство, облік дистиляту та напоїв', ['Катерина Камишева', 'Валентина Попова']],
    '10.5': ['10', '10.5', 'Маркетингова складова', ['Катерина Камишева']],
    '10.6': ['10', '10.6', 'Бренд. Дизайн. Етикетка', ['Катерина Камишева']],
    '10.7a':['10', '10.7', 'Авторське право', ['Л. Черепов']],
    '10.7b':['10', '10.7', 'Дистрибуція', ['Юлія Пелих']],
    '10.8': ['10', '10.8', 'Економічна складова (бізнес-план)', ["Леся Слобод'ян"]],
    '10.9': ['10', '10.9', 'Розроблення власного проєкту. Випускна робота', []],
  };

  const DOMAINS = {
    base:    { name: 'Основа',               color: 'var(--d-base)',
               clip: 'polygon(50% 0, 78% 38%, 92% 60%, 88% 82%, 72% 96%, 50% 100%, 28% 96%, 12% 82%, 8% 60%, 22% 38%)' },
    raw:     { name: 'Сировина і бродіння',  color: 'var(--d-raw)', clip: 'circle(50%)' },
    dist:    { name: 'Дистиляція',           color: 'var(--d-dist)', clip: 'polygon(50% 0, 100% 50%, 50% 100%, 0 50%)' },
    craft:   { name: 'Витримка й доведення', color: 'var(--d-craft)', clip: 'inset(6%)' },
    cats:    { name: 'Категорії напоїв',     color: 'var(--d-cats)',
               clip: 'polygon(30% 0, 70% 0, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0 70%, 0 30%)' },
    quality: { name: 'Якість і сенсорика',   color: 'var(--d-quality)', clip: 'polygon(50% 4%, 100% 94%, 0 94%)' },
    biz:     { name: 'Бізнес і запуск',      color: 'var(--d-biz)', clip: 'polygon(25% 6%, 75% 6%, 100% 50%, 75% 94%, 25% 94%, 0 50%)' },
  };
  const dvars = d => `--c:${d.color};--clip:${d.clip}`;
  const LEVELS = ['Знає', 'Вміє', 'Володіє'];

  // col/row — клітинка сітки за замовчуванням; далі блоки можна тягати.
  const COMPS = [
    { id: 'K1', domain: 'base', col: 0, row: 0, title: 'Безпека виробництва',
      main: ['1.1'], sup: ['4.2'],
      can: ['Організовує робоче місце з урахуванням пожежо- і вибухонебезпеки спиртових парів',
            'Знає порядок дій в аварійних ситуаціях на дільниці дистиляції'],
      levels: ['Знає правила техніки безпеки на виробництві дистилятів',
               'Працює на обладнанні без порушень і помічає небезпечні ситуації',
               'Складає інструкції з безпеки та навчає персонал'] },

    { id: 'K2a', domain: 'raw', col: 0, row: 1, title: 'Крохмалевмісна сировина',
      main: ['3.4'], sup: [],
      can: ['Оцінює зерно й солод за вологістю, крохмалистістю та ферментативною активністю',
            'Проводить розварювання й оцукрювання крохмалю перед бродінням'],
      levels: ['Знає види зерна й солоду та їхній вплив на стиль дистиляту',
               'Готує зерно й солод: подрібнення, затирання, оцукрювання',
               'Складає зерновий засип і режим оцукрювання під продукт'] },
    { id: 'K2b', domain: 'raw', col: 0, row: 2, title: 'Цукровмісна сировина',
      main: ['3.3', '3.6'], sup: ['7.3'],
      can: ['Оцінює плоди, ягоди, виноград, меласу й соки за цукристістю, кислотністю та зрілістю',
            'Готує сусло й мезгу до бродіння'],
      levels: ['Розрізняє види цукровмісної сировини',
               'Приймає партію сировини й готує сусло або мезгу',
               'Формує вимоги до постачальників і сортів під продукт'] },
    { id: 'K2c', domain: 'raw', col: 0, row: 3, title: 'Мед',
      main: ['3.5'], sup: [],
      can: ['Оцінює мед за походженням, вологістю та складом цукрів',
            'Готує медове сусло до бродіння'],
      levels: ['Знає види меду та його властивості як сировини',
               'Готує медове сусло за рецептурою',
               'Розробляє рецептури медових дистилятів'] },
    { id: 'K3', domain: 'raw', col: 0, row: 4, title: 'Водопідготовка',
      main: ['3.1'], sup: ['7.1'],
      can: ['Оцінює воду за жорсткістю, мінералізацією та мікробіологією',
            'Обирає воду для затирання, бродіння та зниження міцності'],
      levels: ['Знає вимоги до технологічної води',
               'Читає аналіз води й обирає спосіб підготовки',
               'Налаштовує схему водопідготовки для виробництва'] },
    { id: 'K4', domain: 'raw', col: 1, row: 3, title: 'Керування спиртовим бродінням',
      main: ['3.2'], sup: ['7.2', '3.4'],
      can: ['Підбирає дріжджі, температуру й живлення для бродіння',
            'Розпізнає інфекцію та зупинку бродіння і знає, як їх виправити'],
      levels: ['Розуміє біохімію та мікробіологію бродіння',
               'Веде бродіння за регламентом і фіксує показники',
               'Діагностує проблеми й коригує процес під продукт'] },

    { id: 'K5', domain: 'dist', col: 2, row: 1, title: 'Теорія розділення сумішей',
      main: ['4.1'], sup: [],
      can: ['Пояснює поведінку етанолу, води й домішок під час перегонки',
            'Розуміє рівновагу пара–рідина та принципи ректифікації'],
      levels: ['Знає фізичні основи перегонки',
               'Прогнозує склад фракцій за режимом перегонки',
               'Розраховує режими для нових продуктів'] },
    { id: 'K6', domain: 'dist', col: 1, row: 1, title: 'Обладнання дистиляції',
      main: ['4.2'], sup: ['10.1'],
      can: ['Розрізняє аламбіки, колони й гібридні установки та їхній вплив на стиль',
            'Обирає обладнання під обсяги й асортимент'],
      levels: ['Знає будову й призначення апаратів',
               'Експлуатує та обслуговує установку',
               'Формує технічне завдання на обладнання цеху'] },
    { id: 'K7', domain: 'dist', col: 2, row: 2, title: 'Перегонка й відбір фракцій',
      main: ['4.3'], sup: ['4.1'],
      can: ['Веде першу й другу перегонку, відбирає голови, серце й хвости',
            'Керує міцністю та чистотою дистиляту через режим апарата'],
      levels: ['Знає етапи перегонки й поняття фракцій',
               'Проводить перегонку й відбір фракцій на практиці',
               'Налаштовує режими під стиль і стабільну якість'] },

    { id: 'K8', domain: 'craft', col: 3, row: 1, title: 'Витримка дистилятів',
      main: ['8.1', '8.2'], sup: [],
      can: ['Обирає бочку, деревину й умови складу під продукт',
            'Застосовує альтернативні методи витримки й дубову продукцію'],
      levels: ['Знає процеси, що відбуваються в бочці',
               'Закладає й контролює витримку',
               'Планує програму витримки та регулює старіння'] },
    { id: 'K9', domain: 'craft', col: 3, row: 2, title: 'Купажування',
      main: ['5.2'], sup: ['6.4'],
      can: ['Складає купаж із дистилятів різного віку та походження',
            'Відтворює смак продукту від партії до партії'],
      levels: ['Знає принципи купажування',
               'Складає купаж за заданим профілем',
               'Створює рецептури нових продуктів'] },
    { id: 'K10', domain: 'craft', col: 3, row: 3, title: 'Стабілізація, фільтрація й розлив',
      main: ['5.1'], sup: [],
      can: ['Обирає способи фільтрації та стабілізації, щоб напій не мутнів',
            'Готує напій до розливу й тривалого зберігання'],
      levels: ['Знає причини нестабільності напоїв',
               'Проводить фільтрацію та стабілізацію партії',
               'Добирає схему обробки під кожен продукт'] },
    { id: 'BOT', domain: 'craft', col: 2, row: 3, title: 'Ботанічні спирти й настоянки',
      main: [], sup: [],
      can: ['Складає композицію ботанікалів для джину та настоянок',
            'Застосовує мацерацію та парову інфузію'],
      levels: ['Знає основні ботанікали та способи екстракції',
               'Готує ботанічний спирт за рецептурою',
               'Розробляє власні рецептури джину й настоянок'] },

    { id: 'C1', domain: 'cats', col: 0, row: 5, title: 'Фруктові дистиляти та бренді',
      main: ['2.1', '2.5'], sup: [],
      can: ['Знає стилі плодових дистилятів і бренді: палінку, кальвадос, кірш, граппу, коньяк, арманьяк',
            'Пояснює, як сировина, перегонка й витримка формують стиль'],
      levels: ['Знає історію, стилі й класифікацію категорії «фруктові дистиляти та бренді»',
               'Розпізнає стилі на дегустації й пояснює, як їх створює технологія',
               'Консультує та проєктує продукт у цій категорії'] },
    { id: 'C2', domain: 'cats', col: 1, row: 5, title: 'Зернові дистиляти і водка',
      main: ['2.2', '2.3', '2.4'], sup: [],
      can: ['Розрізняє віскі різних країн, зернові дистиляти та водку',
            'Пояснює вплив зерна, солоду, ректифікації й витримки на стиль'],
      levels: ['Знає історію, стилі й класифікацію категорії «зернові дистиляти і водка»',
               'Розпізнає стилі на дегустації й пояснює, як їх створює технологія',
               'Консультує та проєктує продукт у цій категорії'] },
    { id: 'C6', domain: 'cats', col: 2, row: 5, title: 'Ром і текіла',
      main: ['2.6'], sup: [],
      can: ['Знає стилі рому з меляси й тростинного соку та категорії текіли',
            'Пояснює вплив сировини й витримки на стиль'],
      levels: ['Знає історію, стилі й класифікацію категорії «ром, текіла»',
               'Розпізнає стилі на дегустації й пояснює, як їх створює технологія',
               'Консультує та проєктує продукт у цій категорії'] },
    { id: 'C7', domain: 'cats', col: 3, row: 5, title: 'Джин',
      main: ['2.7'], sup: [],
      can: ['Знає стилі джину: London Dry, Old Tom, New Western',
            'Розуміє роль ялівцю та інших ботанікалів'],
      levels: ['Знає історію, стилі й класифікацію категорії «джин»',
               'Розпізнає стилі на дегустації й пояснює, як їх створює технологія',
               'Консультує та проєктує продукт у цій категорії'] },
    { id: 'C8', domain: 'cats', col: 4, row: 5, title: 'Вермут, біттери, настоянки',
      main: ['2.8'], sup: [],
      can: ['Знає ароматизовані вина, біттери, мацерати й ботанічні настої',
            'Пояснює роль гіркоти, цукру й ботанікалів у рецептурі'],
      levels: ['Знає історію, стилі й класифікацію категорії «вермут, біттери»',
               'Розпізнає стилі на дегустації й пояснює, як їх створює технологія',
               'Консультує та проєктує продукт у цій категорії'] },
    { id: 'K12', domain: 'quality', col: 2, row: 4, title: 'Сенсорний аналіз',
      main: ['6.1', '6.2', '6.3', '6.4'], sup: [],
      can: ['Проводить дегустацію за методикою й описує напій професійною мовою',
            'Знаходить дефекти аромату й смаку'],
      levels: ['Знає вимоги до дегустатора й умов дегустації',
               'Оцінює напої стандартними методами сенсорного аналізу',
               'Організовує дегустаційну комісію та сенсорну лабораторію'] },
    { id: 'K13', domain: 'quality', col: 1, row: 2, title: 'Лабораторний контроль',
      main: ['7.1', '7.2', '7.3'], sup: [],
      can: ['Визначає міцність, кислотність, цукри та інші фізико-хімічні показники',
            'Аналізує дозрілу бражку й стан дріжджів'],
      levels: ['Знає методики й прилади лабораторії',
               'Самостійно аналізує сировину, бражку й дистилят',
               'Будує план контролю по всьому виробництву'] },
    { id: 'K14', domain: 'quality', col: 3, row: 4, title: 'Якість і безпечність продукції',
      main: ['9.1', '9.2'], sup: [],
      can: ['Класифікує міцні напої за вимогами України та ЄС',
            'Впроваджує систему управління безпечністю харчової продукції'],
      levels: ['Знає класифікацію та вимоги до безпечності',
               'Веде документацію системи якості',
               'Будує систему якості й управління ризиками на виробництві'] },

    { id: 'K15', domain: 'biz', col: 1, row: 0, title: 'Проєктування дистилерії',
      main: ['10.1', '10.3', '10.2'], sup: [],
      can: ['Готує проєкт, генплан і документацію для будівництва дистилерії',
            'Планує поводження з відходами виробництва'],
      levels: ['Знає етапи проєктування й дозвільні вимоги',
               'Складає технічне завдання для проєктувальників',
               'Веде проєкт від ідеї до запуску виробництва'] },
    { id: 'K16', domain: 'biz', col: 2, row: 0, title: 'Законодавство та облік',
      main: ['10.4', '10.7a'], sup: ['9.1'],
      can: ['Веде облік спирту й алкогольних напоїв за вимогами законодавства',
            'Захищає назву, етикетку та рецептуру засобами авторського права'],
      levels: ['Знає ключові норми регулювання галузі',
               'Веде облік і звітність виробництва',
               'Вибудовує юридичну модель бізнесу'] },
    { id: 'K17', domain: 'biz', col: 3, row: 0, title: 'Бренд, маркетинг і збут',
      main: ['10.5', '10.6', '10.7b'], sup: [],
      can: ['Формує бренд, дизайн і етикетку продукту',
            'Будує канали дистрибуції та просування'],
      levels: ['Розуміє ринок міцних напоїв',
               'Готує маркетинговий план продукту',
               'Виводить бренд на ринок'] },
    { id: 'K18', domain: 'biz', col: 4, row: 0, title: 'Економіка виробництва',
      main: ['10.8'], sup: [],
      can: ['Складає бізнес-план і рахує собівартість продукту',
            'Оцінює окупність інвестицій у дистилерію'],
      levels: ['Знає структуру витрат виробництва',
               'Складає бізнес-план',
               'Керує фінансовою моделлю дистилерії'] },

    { id: 'K19', domain: 'base', col: 4, row: 3, title: 'Власний проєкт (випускна робота)',
      main: ['10.9'], sup: [],
      can: ['Поєднує технологію, якість і бізнес у проєкті власного продукту чи дистилерії',
            'Обґрунтовує та захищає свої рішення'],
      levels: ['Формулює ідею продукту',
               'Розробляє технологію та бізнес-модель',
               'Готовий запустити виробництво'] },
  ];

  // from -> to: «дає основу для».
  // 'req' — обов'язкова передумова; 'any:<група>' — достатньо однієї з групи.
  // Усі 'req' та 'any' однієї цілі потрібні разом (на схемі — вузол «І»).
  const EDGES = [
    ['K1', 'K6'], ['K15', 'K6'],
    ['K15', 'K16'], ['K16', 'K17'], ['K17', 'K18'], ['K18', 'K19'],
    ['K2a', 'K4', 'any:raw'], ['K2b', 'K4', 'any:raw'], ['K2c', 'K4', 'any:raw'], ['K3', 'K4', 'req'], ['K13', 'K4'], ['K13', 'K7'],
    ['K4', 'K7'], ['K5', 'K7'], ['K6', 'K7'],
    ['K7', 'K8'], ['K7', 'K9'], ['K8', 'K9'], ['K12', 'K9'], ['K7', 'BOT'], ['BOT', 'K9'],
    ...['C1', 'C2', 'C6', 'C7', 'C8'].map(c => [c, 'K12', 'any:cats']),
    ['K9', 'K10'], ['K14', 'K10'], ['K10', 'K19'], ['K14', 'K19'],
  ];
  const GROUPS = {
    raw: { label: 'Сировина · достатньо однієї', members: ['K2a', 'K2b', 'K2c'] },
    cats: { label: 'Категорії напоїв · достатньо однієї', members: ['C1', 'C2', 'C6', 'C7', 'C8'] },
  };

  COMPS.forEach(c => { c.courses = COVERAGE[c.id] || []; });

  // --- геометрія -----------------------------------------------------------
  const NODE_W = 240, ROW = 200, PAD = 30;
  // Ширший проміжок після першої колонки — там стоїть вузол «І».
  const COLS = [30, 380, 670, 960, 1250];
  const CANVAS_W = COLS[4] + NODE_W + PAD;
  const BAND = 40; // додатковий відступ перед смугою категорій
  const CANVAS_H = PAD * 2 + ROW * 5 + BAND + 170;
  const byId = Object.fromEntries(COMPS.map(c => [c.id, c]));
  const CODE = Object.fromEntries(COMPS.map((c, i) => [c.id, 'К' + (i + 1)]));
  const defaultPos = id => ({ x: COLS[byId[id].col], y: PAD + byId[id].row * ROW + (byId[id].row >= 5 ? BAND : 0) });

  // --- пам'ять глядача (лише зручність; сторінка працює і без неї) --------
  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem('uda-matrix:' + k)); } catch { return null; } },
    set(k, v) { try { localStorage.setItem('uda-matrix:' + k, JSON.stringify(v)); } catch {} },
    del(k) { try { localStorage.removeItem('uda-matrix:' + k); } catch {} },
  };

  const pos = {};
  const saved = store.get('pos-v6') || {};
  COMPS.forEach(c => {
    const s = saved[c.id];
    pos[c.id] = s && Number.isFinite(s.x) && Number.isFinite(s.y) ? s : defaultPos(c.id);
  });

  const state = { selected: null, module: null, scale: 1 };

  // --- утиліти -------------------------------------------------------------
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
  const code = sid => SUBJECTS[sid][1];
  const modOf = sid => SUBJECTS[sid][0];
  const compModules = c => new Set([...c.main, ...c.sup].map(modOf));
  const kindOf = (a, b) => (EDGES.find(e => e[0] === a && e[1] === b) || [])[2] || '';
  const isGate = kind => kind === 'req' || kind.startsWith('any:');
  const neighbours = id => ({
    from: EDGES.filter(e => e[1] === id).map(e => e[0]),
    to: EDGES.filter(e => e[0] === id).map(e => e[1]),
  });

  // --- зведення ------------------------------------------------------------
  const covered = new Set(COMPS.flatMap(c => [...c.main, ...c.sup]));
  const plural = (n, forms) => {
    const a = n % 10, b = n % 100;
    return forms[a === 1 && b !== 11 ? 0 : a >= 2 && a <= 4 && (b < 12 || b > 14) ? 1 : 2];
  };
  const nSubj = Object.keys(SUBJECTS).length;
  $('#summary').innerHTML =
    `<b>${COURSES.length}</b> курсів і майстер-класів · ` +
    `у «Майстрі» <b>${MODULES.length}</b> ${plural(MODULES.length, ['модуль', 'модулі', 'модулів'])} і <b>${nSubj}</b> ${plural(nSubj, ['предмет', 'предмети', 'предметів'])} · ` +
    `<b>${COMPS.length}</b> ${plural(COMPS.length, ['компетентність', 'компетентності', 'компетентностей'])} · кожна оцінюється за шкалою «${LEVELS.join(' → ')}»`;

  // --- фільтр модулів ------------------------------------------------------
  const modNav = $('#modules');
  MODULES.forEach(m => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'cm-chip'; b.dataset.mod = m.n;
    b.setAttribute('aria-pressed', 'false');
    b.title = m.name;
    b.innerHTML = `<span class="n">${m.n}</span>${esc(m.short)}<span class="fmt">${m.fmt}</span>`;
    b.addEventListener('click', () => {
      state.module = state.module === m.n ? null : m.n;
      refresh();
    });
    modNav.appendChild(b);
  });

  // --- схема ---------------------------------------------------------------
  const canvas = $('#canvas'), svg = $('#edges'), sizer = $('#sizer'), viewport = $('#viewport');
  canvas.style.width = CANVAS_W + 'px';
  canvas.style.height = CANVAS_H + 'px';
  svg.setAttribute('width', CANVAS_W);
  svg.setAttribute('height', CANVAS_H);

  // «Потрібно: К5 і одна з К2, К3, К4»
  function gateText(id) {
    const inc = EDGES.filter(e => e[1] === id && isGate(e[2] || ''));
    if (!inc.length) return '';
    const parts = inc.filter(e => e[2] === 'req').map(e => CODE[e[0]]);
    const groups = [...new Set(inc.filter(e => e[2] !== 'req').map(e => e[2]))];
    groups.forEach(g => {
      const codes = inc.filter(e => e[2] === g).map(e => CODE[e[0]]);
      parts.push('одна з ' + (codes.length > 2 ? `${codes[0]}–${codes[codes.length - 1]}` : codes.join(', ')));
    });
    return `<div class="node-req">Потрібно: ${parts.join(' і ')}</div>`;
  }

  const nodeEls = {};
  COMPS.forEach(c => {
    const d = DOMAINS[c.domain];
    const el = document.createElement('div');
    el.className = 'node';
    el.tabIndex = 0;
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', `${CODE[c.id]} ${c.title}. Перетягніть, щоб перемістити; стрілки теж рухають блок.`);
    el.style.cssText = dvars(d);
    el.innerHTML =
      `<div class="node-top"><span class="node-code">${CODE[c.id]}</span><span class="node-domain">${esc(d.name)}</span></div>` +
      `<div class="node-title">${esc(c.title)}</div>` +
      `<div class="node-subj">${c.main.map(s => `<span>${code(s)}</span>`).join('')}` +
      `${c.sup.map(s => `<span class="sup">${code(s)}</span>`).join('')}` +
      `${c.main.length ? '' : '<span class="only">поза програмою «Майстра»</span>'}` +
      `<span class="cnt">${c.courses.length} ${plural(c.courses.length, ['курс', 'курси', 'курсів'])}</span></div>` +
      gateText(c.id);
    canvas.appendChild(el);
    nodeEls[c.id] = el;
    place(c.id);
    bindDrag(el, c.id);
  });

  const SVGNS = 'http://www.w3.org/2000/svg';
  const svgEl = (tag, cls) => { const e = document.createElementNS(SVGNS, tag); if (cls) e.setAttribute('class', cls); return e; };

  // Рамки груп: «достатньо однієї з».
  const groupEls = Object.entries(GROUPS).map(([key, g]) => {
    const rect = svgEl('rect', 'group'), label = svgEl('text', 'group-label');
    rect.setAttribute('rx', 10);
    label.textContent = g.label;
    svg.append(rect, label);
    return { id: 'G:' + key, members: g.members, rect, label };
  });

  // Лінії: звичайні — напряму; передумови сходяться у вузлі «І» перед ціллю,
  // а сировина з однієї групи входить у нього однією лінією від рамки.
  const drawn = [];
  const junctions = [];
  // Скільки окремих передумов у цілі (група рахується як одна).
  const gateSources = b => new Set(EDGES.filter(e => e[1] === b && isGate(e[2] || ''))
    .map(e => e[2] === 'req' ? e[0] : 'G:' + e[2].slice(4)));
  EDGES.forEach(([a, b, kind = '']) => {
    if (!isGate(kind)) { drawn.push({ from: a, to: b, ids: [a, b], cls: '' }); return; }
    if (gateSources(b).size === 1) {
      const src = kind === 'req' ? a : 'G:' + kind.slice(4);
      const ex = drawn.find(d => d.from === src && d.to === b);
      if (ex) ex.ids.push(a); else drawn.push({ from: src, to: b, ids: [a, b], cls: 'req' });
      return;
    }
    const j = 'J:' + b;
    if (!junctions.some(x => x.id === j)) {
      junctions.push({ id: j, target: b });
      drawn.push({ from: j, to: b, ids: EDGES.filter(e => e[1] === b && isGate(e[2] || '')).map(e => e[0]).concat(b), cls: 'req' });
    }
    const src = kind === 'req' ? a : 'G:' + kind.slice(4);
    const ex = drawn.find(d => d.from === src && d.to === j);
    if (ex) ex.ids.push(a); else drawn.push({ from: src, to: j, ids: [a, b], cls: 'req', noArrow: true });
  });
  const junctionEls = junctions.map(jn => {
    const g = svgEl('g', 'junction'), c = svgEl('circle'), t = svgEl('text');
    c.setAttribute('r', 13);
    t.textContent = 'І';
    t.setAttribute('text-anchor', 'middle');
    t.setAttribute('dy', '0.35em');
    g.append(c, t);
    svg.appendChild(g);
    return { ...jn, el: g };
  });
  const edgeEls = drawn.map(d => {
    const p = svgEl('path', d.cls);
    svg.insertBefore(p, junctionEls[0] ? junctionEls[0].el : null);
    return { ...d, el: p };
  });
  const markerFor = (e, on) => e.noArrow ? '' : e.cls === 'req' ? 'url(#arrow-req)' : on ? 'url(#arrow-on)' : 'url(#arrow)';

  function place(id) {
    const el = nodeEls[id];
    el.style.left = pos[id].x + 'px';
    el.style.top = pos[id].y + 'px';
  }

  function box(id) {
    if (id.startsWith('G:')) {
      const bs = GROUPS[id.slice(2)].members.map(box);
      const x = Math.min(...bs.map(b => b.x)) - 12, y = Math.min(...bs.map(b => b.y)) - 30;
      return { x, y, w: Math.max(...bs.map(b => b.x + b.w)) + 12 - x, h: Math.max(...bs.map(b => b.y + b.h)) + 12 - y };
    }
    if (id.startsWith('J:')) {
      const t = box(id.slice(2));
      return { x: t.x - 58, y: t.y + t.h / 2 - 13, w: 26, h: 26 };
    }
    const el = nodeEls[id];
    return { x: pos[id].x, y: pos[id].y, w: el.offsetWidth, h: el.offsetHeight };
  }

  function edgePath(a, b) {
    const A = box(a), B = box(b);
    const ac = { x: A.x + A.w / 2, y: A.y + A.h / 2 };
    const bc = { x: B.x + B.w / 2, y: B.y + B.h / 2 };
    const dx = bc.x - ac.x, dy = bc.y - ac.y;
    // Блоки в різних колонках з'єднуються збоку (лінія огинає сусідів проміжком
    // між колонками), блоки в одній колонці — зверху/знизу.
    const horizontal = A.x + A.w + 16 <= B.x || B.x + B.w + 16 <= A.x;
    // Кінці зсуваються вздовж сторони в бік сусіда, щоб стрілки не сходилися в одну точку.
    const spread = (d, size) => Math.max(-size * 0.3, Math.min(size * 0.3, d * 0.3));
    let p1, p2, n1, n2, k;
    if (horizontal) {
      const s = Math.sign(dx) || 1;
      p1 = { x: ac.x + s * A.w / 2, y: ac.y + spread(dy, A.h) };
      p2 = { x: bc.x - s * B.w / 2, y: bc.y - spread(dy, B.h) };
      n1 = { x: s, y: 0 }; n2 = { x: -s, y: 0 };
      k = Math.abs(p2.x - p1.x) * 0.5;
    } else {
      const s = Math.sign(dy) || 1;
      p1 = { x: ac.x + spread(dx, A.w), y: ac.y + s * A.h / 2 };
      p2 = { x: bc.x - spread(dx, B.w), y: bc.y - s * B.h / 2 };
      n1 = { x: 0, y: s }; n2 = { x: 0, y: -s };
      k = Math.abs(p2.y - p1.y) * 0.5;
    }
    k = Math.max(24, k);
    return `M${p1.x},${p1.y} C${p1.x + n1.x * k},${p1.y + n1.y * k} ${p2.x + n2.x * k},${p2.y + n2.y * k} ${p2.x},${p2.y}`;
  }

  function drawEdges() {
    groupEls.forEach(g => {
      const b = box(g.id);
      g.rect.setAttribute('x', b.x); g.rect.setAttribute('y', b.y);
      g.rect.setAttribute('width', b.w); g.rect.setAttribute('height', b.h);
      g.label.setAttribute('x', b.x + 12); g.label.setAttribute('y', b.y + 19);
    });
    junctionEls.forEach(j => {
      const b = box(j.id);
      j.el.setAttribute('transform', `translate(${b.x + 13},${b.y + 13})`);
    });
    edgeEls.forEach(e => e.el.setAttribute('d', edgePath(e.from, e.to)));
  }

  function bindDrag(el, id) {
    let start = null;
    el.addEventListener('pointerdown', ev => {
      if (ev.button !== 0) return;
      start = { px: ev.clientX, py: ev.clientY, x: pos[id].x, y: pos[id].y, moved: false };
      el.setPointerCapture(ev.pointerId);
    });
    el.addEventListener('pointermove', ev => {
      if (!start) return;
      const dx = (ev.clientX - start.px) / state.scale;
      const dy = (ev.clientY - start.py) / state.scale;
      if (!start.moved && Math.hypot(dx, dy) < 4) return;
      start.moved = true;
      el.classList.add('dragging');
      moveTo(id, start.x + dx, start.y + dy);
    });
    const end = () => {
      if (!start) return;
      const wasClick = !start.moved;
      start = null;
      el.classList.remove('dragging');
      if (wasClick) select(state.selected === id ? null : id);
      else savePos();
    };
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
    el.addEventListener('keydown', ev => {
      const step = ev.shiftKey ? 50 : 10;
      const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(state.selected === id ? null : id); }
      else if (moves[ev.key]) {
        ev.preventDefault();
        moveTo(id, pos[id].x + moves[ev.key][0], pos[id].y + moves[ev.key][1]);
        savePos();
      }
    });
  }

  function moveTo(id, x, y) {
    const el = nodeEls[id];
    pos[id] = {
      x: Math.round(Math.min(Math.max(0, x), CANVAS_W - el.offsetWidth)),
      y: Math.round(Math.min(Math.max(0, y), CANVAS_H - el.offsetHeight)),
    };
    place(id);
    drawEdges();
  }

  function savePos() { store.set('pos-v6', pos); }

  $('#reset').addEventListener('click', () => {
    COMPS.forEach(c => { pos[c.id] = defaultPos(c.id); place(c.id); });
    store.del('pos-v6');
    drawEdges();
  });

  // --- масштаб -------------------------------------------------------------
  function setScale(s) {
    state.scale = Math.min(1.4, Math.max(0.4, Math.round(s * 100) / 100));
    canvas.style.transform = `scale(${state.scale})`;
    sizer.style.width = CANVAS_W * state.scale + 'px';
    sizer.style.height = CANVAS_H * state.scale + 'px';
    $('#zoom-val').textContent = Math.round(state.scale * 100) + '%';
  }
  const fitScale = () => Math.min(1, Math.max(0.55, (viewport.clientWidth - 4) / CANVAS_W));
  $('#zoom-in').addEventListener('click', () => setScale(state.scale + 0.1));
  $('#zoom-out').addEventListener('click', () => setScale(state.scale - 0.1));
  $('#zoom-fit').addEventListener('click', () => setScale(fitScale()));

  // --- таблиця -------------------------------------------------------------
  function buildTable() {
    const t = $('#matrix');
    let html = '<thead><tr><th class="comp">Компетентність</th><th>Предмети «Майстра»</th>' +
      COURSES.map(k => `<th class="course" title="${esc(k.name)}"><span class="n">${esc(k.short)}</span></th>`).join('') +
      '</tr></thead><tbody>';
    Object.entries(DOMAINS).forEach(([key, d]) => {
      const rows = COMPS.filter(c => c.domain === key);
      html += `<tr class="dom" style="${dvars(d)}"><td colspan="${COURSES.length + 2}">${esc(d.name)}</td></tr>`;
      rows.forEach(c => {
        html += `<tr class="row" data-id="${c.id}" tabindex="0" style="${dvars(d)}"><td><span class="code">${CODE[c.id]}</span>${esc(c.title)}</td>` +
          `<td><div class="cell">` +
          c.main.map(s => `<span class="pill" title="${esc(SUBJECTS[s][2])}">${code(s)}</span>`).join('') +
          c.sup.map(s => `<span class="pill sup" title="${esc(SUBJECTS[s][2])} (підсилює)">${code(s)}</span>`).join('') +
          '</div></td>' +
          COURSES.map(k => `<td class="course">${c.courses.includes(k.id) ? `<span class="dotc" title="${esc(k.name)}"></span>` : ''}</td>`).join('') +
          '</tr>';
      });
    });
    t.innerHTML = html + '</tbody>';
    t.querySelectorAll('tr.row').forEach(tr => {
      const go = () => select(state.selected === tr.dataset.id ? null : tr.dataset.id);
      tr.addEventListener('click', go);
      tr.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); go(); } });
    });
  }

  // --- панель --------------------------------------------------------------
  const panel = $('#panel');

  function linkBtn(id, tag) {
    const c = byId[id];
    return `<button type="button" class="link" data-go="${id}" style="${dvars(DOMAINS[c.domain])}"><span class="code">${CODE[id]}</span>${esc(c.title)}${tag ? `<span class="cm-tag">${tag}</span>` : ''}</button>`;
  }

  function subjItem(sid, sup) {
    const [m, cd, name, who] = SUBJECTS[sid];
    const mod = MODULES.find(x => x.n === m);
    return `<div class="subj-item${sup ? ' sup' : ''}"><span class="code">${cd}</span><div>${esc(name)}` +
      `<div class="subj-meta">${who.length ? esc(who.join(', ')) : 'Керівник проєкту'}` +
      `<span class="cm-tag">${mod.fmt}</span>${sup ? '<span class="cm-tag">підсилює</span>' : ''}</div></div></div>`;
  }

  function renderPanel() {
    const c = state.selected && byId[state.selected];
    if (!c) {
      const counts = Object.fromEntries(Object.keys(DOMAINS).map(k => [k, COMPS.filter(x => x.domain === k).length]));
      const mod = state.module && MODULES.find(m => m.n === state.module);
      panel.style.removeProperty('--c');
      panel.style.removeProperty('--clip');
      panel.innerHTML =
        (mod ? `<div><h3>Модуль ${mod.n} · ${mod.fmt}</h3><p>${esc(mod.name)}</p></div>
          <div><h3>Предмети модуля</h3><div class="subj">${Object.keys(SUBJECTS).filter(s => modOf(s) === mod.n).map(s => subjItem(s, false)).join('')}</div></div>
          <div><h3>Розвиває компетентності</h3><div class="links">${COMPS.filter(x => compModules(x).has(mod.n)).map(x => linkBtn(x.id, false)).join('')}</div></div>`
        : `<div class="p-head"><h2>Як читати схему</h2>
          <p class="hint">Це спільна база для всіх курсів Академії. Кожен блок — компетентність. Під назвою — номери предметів програми «Майстер дистиляції», які її формують (бліді лише підсилюють), і кількість курсів, де її розвивають. Натисніть блок, щоб побачити рівні, курси й викладачів. Блоки можна перетягувати.</p></div>
          <p class="draft">Склад курсів, крім «Майстра дистиляції», поки чернетка за описами на сайті. Її треба звірити з програмами курсів.</p>
          <div><h3>Напрями</h3><div class="cm-legend">${Object.entries(DOMAINS).map(([k, d]) =>
            `<div style="${dvars(d)}"><span class="dot"></span>${esc(d.name)}<span class="count">${counts[k]}</span></div>`).join('')}</div></div>
          <div><h3>Лінії</h3><div class="edge-key"><svg width="48" height="12" viewBox="0 0 48 12"><path d="M2 6 H40" stroke="var(--edge)" stroke-width="1.6" fill="none"/><path d="M38 2 L46 6 L38 10 z" fill="var(--edge)"/></svg>одна компетентність дає основу для іншої</div>
            <div class="edge-key"><svg width="48" height="12" viewBox="0 0 48 12"><path d="M2 6 H40" stroke="var(--copper)" stroke-width="3" fill="none"/><path d="M38 1.5 L47 6 L38 10.5 z" fill="var(--copper)"/></svg>передумова: без неї не опанувати наступну</div>
            <div class="edge-key"><svg width="48" height="28" viewBox="0 0 48 28"><circle cx="24" cy="14" r="12" fill="var(--surface)" stroke="var(--copper)" stroke-width="2"/><text x="24" y="14" dy="0.35em" text-anchor="middle" fill="var(--text)" font-size="13" font-weight="700" font-family="PT Sans, sans-serif">І</text></svg>потрібні всі передумови, що сходяться у вузлі</div>
            <div class="edge-key"><svg width="48" height="28" viewBox="0 0 48 28"><rect x="2" y="3" width="44" height="22" rx="6" fill="none" stroke="var(--copper)" stroke-width="1.4" stroke-dasharray="4 3"/></svg>пунктирна рамка: достатньо однієї компетентності з групи</div></div>
          <div><h3>Шкала рівнів</h3><div class="levels">${LEVELS.map((l, i) =>
            `<div class="level"><span class="level-tag">${l}<span class="meter">${[0, 1, 2].map(j => `<i class="${j <= i ? 'f' : ''}"></i>`).join('')}</span></span><span>${
              ['Розуміє теорію, називає поняття й вимоги', 'Виконує роботу самостійно за регламентом', 'Налаштовує процес під продукт і навчає інших'][i]}</span></div>`).join('')}</div></div>
          <p class="hint">Усі ${nSubj} ${plural(nSubj, ['предмет', 'предмети', 'предметів'])} програми розподілено по компетентностях: без прив'язки не лишився жоден (${covered.size} з ${Object.keys(SUBJECTS).length}).</p>`);
      bindPanelLinks();
      return;
    }
    const d = DOMAINS[c.domain];
    const nb = neighbours(c.id);
    panel.style.setProperty('--c', d.color);
    panel.style.setProperty('--clip', d.clip);
    panel.innerHTML =
      `<div class="p-head"><span class="p-kicker">${CODE[c.id]} · ${esc(d.name)}</span><h2>${esc(c.title)}</h2></div>
      <div><h3>Після курсу випускник</h3><ul>${c.can.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
      <div><h3>Рівні</h3><div class="levels">${c.levels.map((l, i) =>
        `<div class="level"><span class="level-tag">${LEVELS[i]}<span class="meter">${[0, 1, 2].map(j => `<i class="${j <= i ? 'f' : ''}"></i>`).join('')}</span></span><span>${esc(l)}</span></div>`).join('')}</div></div>
      <div><h3>Курси</h3><ul class="course-list">${COURSES.filter(k => c.courses.includes(k.id)).map(k => `<li>${esc(k.name)}</li>`).join('')}</ul></div>
      ${c.main.length || c.sup.length ? `<div><h3>Предмети «Майстра дистиляції»</h3><div class="subj">${c.main.map(s => subjItem(s, false)).join('')}${c.sup.map(s => subjItem(s, true)).join('')}</div></div>` : ''}
      ${prereqHtml(c.id, nb.from)}
      ${nb.to.length ? `<div><h3>Дає основу для</h3><div class="links">${nb.to.map(x => linkBtn(x, toTag(kindOf(c.id, x)))).join('')}</div></div>` : ''}
      <button type="button" class="cm-btn close" id="deselect">Закрити</button>`;
    $('#deselect').addEventListener('click', () => select(null));
    bindPanelLinks();
  }

  const toTag = kind => kind === 'req' ? 'обов\'язково' : kind.startsWith('any:') ? 'одна з групи' : '';

  // Передумови: обов'язкові, «хоча б одна з» і решта — окремими рядками.
  function prereqHtml(id, from) {
    if (!from.length) return '';
    const req = from.filter(x => kindOf(x, id) === 'req');
    const any = from.filter(x => kindOf(x, id).startsWith('any:'));
    const rest = from.filter(x => !isGate(kindOf(x, id)));
    const row = (title, ids) => ids.length ? `<div><h3>${title}</h3><div class="links">${ids.map(x => linkBtn(x)).join('')}</div></div>` : '';
    if (!req.length && !any.length) return row('Спирається на', rest);
    return `<div class="gate">${row('Обов\'язково', req)}${any.length ? `${req.length ? '<p class="gate-and">і</p>' : ''}${row('Хоча б одна з', any)}` : ''}</div>` +
      row('Також спирається на', rest);
  }

  function bindPanelLinks() {
    panel.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => select(b.dataset.go)));
  }

  // --- стан і підсвічування ------------------------------------------------
  function select(id) {
    state.selected = id;
    refresh();
    if (id && !$('#graph-view').hidden) {
      const el = nodeEls[id], r = el.getBoundingClientRect(), v = viewport.getBoundingClientRect();
      if (r.left < v.left || r.right > v.right || r.top < v.top || r.bottom > v.bottom) {
        viewport.scrollTo({ left: pos[id].x * state.scale - v.width / 3, top: pos[id].y * state.scale - v.height / 3, behavior: 'smooth' });
      }
    }
  }

  function refresh() {
    const sel = state.selected, mod = state.module;
    const nb = sel ? neighbours(sel) : null;
    const near = nb ? new Set([...nb.from, ...nb.to]) : new Set();

    COMPS.forEach(c => {
      const el = nodeEls[c.id];
      const inMod = !mod || compModules(c).has(mod);
      el.classList.toggle('sel', c.id === sel);
      el.classList.toggle('near', near.has(c.id));
      el.classList.toggle('off', (sel && c.id !== sel && !near.has(c.id)) || (!sel && !inMod));
    });
    const touches = ids => sel ? ids.includes(sel) : !mod || ids.some(id => compModules(byId[id]).has(mod));
    edgeEls.forEach(e => {
      const on = !!sel && e.ids.includes(sel);
      e.el.classList.toggle('on', on);
      e.el.classList.toggle('off', !touches(e.ids));
      const m = markerFor(e, on);
      if (m) e.el.setAttribute('marker-end', m); else e.el.removeAttribute('marker-end');
    });
    groupEls.forEach(g => {
      const ids = g.members.concat(EDGES.filter(e => g.members.includes(e[0])).map(e => e[1]));
      g.rect.classList.toggle('off', !touches(ids));
      g.label.classList.toggle('off', !touches(ids));
    });
    junctionEls.forEach(j => {
      const ids = EDGES.filter(e => e[1] === j.target).map(e => e[0]).concat(j.target);
      j.el.classList.toggle('off', !touches(ids));
    });

    document.querySelectorAll('#modules .cm-chip').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mod === mod)));
    document.querySelectorAll('#matrix [data-mod]').forEach(x => x.classList.toggle('hl', x.dataset.mod === mod));
    document.querySelectorAll('#matrix tr.row').forEach(tr => tr.classList.toggle('sel', tr.dataset.id === sel));

    renderPanel();
  }

  // --- вигляд і тема -------------------------------------------------------
  function setView(v) {
    const graph = v !== 'table';
    $('#graph-view').hidden = !graph;
    $('#table-view').hidden = graph;
    $('#reset').hidden = !graph;
    $('#view-graph').setAttribute('aria-pressed', String(graph));
    $('#view-table').setAttribute('aria-pressed', String(!graph));
    store.set('view', graph ? 'graph' : 'table');
    if (graph) {
      if (!state.fitted) { setScale(fitScale()); state.fitted = true; }
      drawEdges();
    }
  }
  $('#view-graph').addEventListener('click', () => setView('graph'));
  $('#view-table').addEventListener('click', () => setView('table'));

  // --- старт ---------------------------------------------------------------
  buildTable();
  setScale(1);
  setView(store.get('view') || 'graph');
  refresh();
  // Шрифти змінюють висоту блоків — перемалювати лінії, коли вони завантажаться.
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => drawEdges());
  window.addEventListener('resize', () => drawEdges());
})();
