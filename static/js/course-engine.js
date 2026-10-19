/* Конструктор курсів — підбір. Чиста логіка без DOM: її ж ганяє
   tests/course-engine.test.js (node), а сторінку малює static/js/constructor.js.

   Усе тримається на матриці компетенцій (static/js/competency-data.js):
   з відповідей людини складається індивідуальна програма, а готові курси
   оцінюються тим, наскільки вони цю програму закривають.

   Правила, які тут зашито:
   - індивідуальний курс завжди підходить на 100%;
   - курси, що підходять менше ніж на SHOW_FROM %, не показуються — крім
     курсу про обраний напій: він показується завжди;
   - серед готових першим стоїть «Майстер дистиляції» — Академія насамперед
     набирає на великий курс, — далі за відсотком;
   - програма = те, що людина обрала, плюс модулі, на які це спирається,
     рівно на один крок назад по матриці (DEPTH);
   - новачкові модулі про підприємство самі не додаються — лише якщо він
     обрав їх сам, — і «Майстер дистиляції» не стає для нього першим. */
(root => {
  const SHOW_FROM = 70;
  const DEPTH = 1;
  const FLAGSHIP = 'master';

  // Вага модуля в оцінці готового курсу: що людина обрала сама — 1,
  // модуль про її напій — DRINK_WEIGHT, основа — залежить від рівня (PERSON).
  // Тобто оцінка — це передусім «чи є в курсі те, що я просив».
  const DRINK_WEIGHT = 0.2;
  // Ціль, яку курс зачіпає, але сам не про неї (див. COURSE_FOCUS).
  const PASSING = 0.8;
  // Курс, що дає значно більше, ніж просили, підходить гірше: штраф росте
  // з часткою «зайвих» компетентностей у матриці, і що далі, то крутіше.
  const BREADTH = { weight: 0.6, power: 1.5 };
  // Курс про інший напій, ніж обрала людина.
  const OTHER_DRINK = 0.85;
  // «Майстер» для новачка: множник і стеля у відсотках.
  const NOVICE_FLAGSHIP = { factor: 0.9, cap: 89 };

  // Рівень людини. goal/base/drink — цільовий рівень модуля за шкалою
  // матриці (0 «Знає», 1 «Вміє», 2 «Володіє»). baseWeight — наскільки готовий
  // курс має закривати ще й основу: новачкові вона потрібна, профі — майже ні.
  const PERSON = [
    { id: 'novice', name: 'Новачок', rank: 'Шукач',
      text: 'Ще не переганяю або тільки пробую вдома',
      goal: 1, base: 0, drink: 0, baseWeight: 0.25, noBusiness: true },
    { id: 'practitioner', name: 'Практик', rank: 'Практик',
      text: 'Уже виробляю й хочу стабільної якості',
      goal: 2, base: 1, drink: 1, baseWeight: 0.15 },
    { id: 'pro', name: 'Профі', rank: 'Майстер',
      text: 'Технолог або власник виробництва',
      goal: 2, base: 2, drink: 2, baseWeight: 0.05 },
  ];

  // Напій. cats/raw — хто з групи «достатньо однієї» йому відповідає;
  // ctx — модуль «про ваш напій»; core — що означає сам напій як ключове слово;
  // tone — відтінок рідини в пляшці (лише тінти міді).
  // Без raw — напій без власного бродіння: джин і настоянки роблять на
  // готовому спирті й ботанікалах, сировина для бражки їм не потрібна.
  const DRINKS = [
    { id: 'whisky',  name: 'Віскі',                        adj: 'Солодовий',  tone: 'var(--copper)',
      cats: 'C2', raw: 'K2a', ctx: ['C2'], core: ['C2', 'K2a', 'K8'] },
    { id: 'vodka',   name: 'Водка й зернові дистиляти',    adj: 'Зерновий',   tone: 'var(--accent-200)',
      cats: 'C2', raw: 'K2a', ctx: ['C2'], core: ['C2', 'K2a', 'K5', 'K10'] },
    { id: 'gin',     name: 'Джин',                         adj: 'Ботанічний', tone: 'var(--accent-300)',
      cats: 'C7', ctx: ['C7'], core: ['C7', 'BOT'] },
    { id: 'bitters', name: 'Настоянки, вермут, біттери',   adj: 'Трав\'яний', tone: 'var(--accent-600)',
      cats: 'C8', ctx: ['C8'], core: ['C8', 'BOT'] },
    { id: 'fruit',   name: 'Фруктові дистиляти й бренді',  adj: 'Плодовий',   tone: 'var(--accent-700)',
      cats: 'C1', raw: 'K2b', ctx: ['C1'], core: ['C1', 'K2b', 'K8'] },
    { id: 'rum',     name: 'Ром і текіла',                 adj: 'Тростинний', tone: 'var(--accent-800)',
      cats: 'C6', raw: 'K2b', ctx: ['C6'], core: ['C6', 'K2b', 'K8'] },
    { id: 'honey',   name: 'Медовий дистилят',             adj: 'Медовий',    tone: 'var(--accent-400)',
      raw: 'K2c', ctx: ['K2c'], core: ['K2c'] },
  ];

  // Основа, якій не кожен напій дає сенс: джину бочка не потрібна, віскі —
  // ботанікали, а бродіння й сировина для бражки — лише напоям, які
  // зброджують самі (у матриці перегонка спирається на бродіння, і без цього
  // джин тягнув би за перегонкою зерно). Діє лише на модулі, які конструктор
  // додає сам: обрав людина бродіння — воно в програмі.
  const FERMENTED = DRINKS.filter(d => d.raw).map(d => d.id);
  const ONLY_FOR = {
    BOT: ['gin', 'bitters'],
    K8: ['whisky', 'fruit', 'rum', 'honey'],
    K4: FERMENTED, K2a: FERMENTED, K2b: FERMENTED, K2c: FERMENTED,
  };

  // Про що курс насамперед — за його описом на сайті (core/content.py).
  // Матриця каже лише «курс розвиває компетентність»; без цього «Майстерня
  // витримки» програвала б запиту «витримка» майстерні віскі, де бочка —
  // один із днів. «Майстер» — про все одразу, тому його тут немає.
  const COURSE_FOCUS = {
    grain: ['C2', 'K2a', 'K3', 'K4', 'K5'],
    whisky: ['C2', 'K2a', 'K4', 'K6', 'K7'],
    gin: ['C7', 'C8', 'BOT', 'K9'],
    sensory: ['K12'],
    aging: ['K8'],
    ferm: ['K4', 'K13'],
    fruit: ['C1', 'K2b', 'K4'],
    spirit: ['C1', 'C2', 'C6', 'C7', 'C8'],
    'mc-org': ['K15', 'K16', 'K18'],
    'mc-starch': ['K2a', 'K4'],
    'mc-fruit': ['K2b', 'K4'],
  };

  // Курс, присвячений самому напою: обрала людина напій — цей курс показується
  // завжди, навіть нижче SHOW_FROM. Майстер-класи про сировину сюди не входять.
  const DRINK_COURSE = { whisky: 'whisky', vodka: 'grain', gin: 'gin', bitters: 'gin', fruit: 'fruit' };

  // Готові курси, присвячені певному напою (ідентифікатори — з матриці).
  const COURSE_DRINKS = {
    grain: ['vodka'],
    whisky: ['whisky'],
    gin: ['gin', 'bitters'],
    fruit: ['fruit'],
    'mc-starch': ['whisky', 'vodka'],
    'mc-fruit': ['fruit'],
  };

  // Станції маршруту «від сировини до полиці» — перший спосіб вибору.
  // 'raw' у comps означає «сировина під обраний напій» (група матриці).
  const STAGES = [
    { id: 'raw',     icon: 'ic-grain',     name: 'Сировина й вода',        text: 'Зерно, плоди чи мед — і вода, на якій усе тримається', comps: ['@raw', 'K3'] },
    { id: 'ferm',    icon: 'ic-ferment',   name: 'Бродіння',               text: 'Дріжджі, температура, бражка без інфекцій', comps: ['K4'] },
    { id: 'dist',    icon: 'ic-still',     name: 'Перегонка',              text: 'Куб чи колона, голови, серце й хвости', comps: ['K7'] },
    { id: 'botan',   icon: 'ic-botanical', name: 'Ботанікали',             text: 'Мацерація, парова інфузія, власна рецептура', comps: ['BOT'] },
    { id: 'aging',   icon: 'ic-cask',      name: 'Витримка',               text: 'Бочка, деревина, альтернативні методи', comps: ['K8'] },
    { id: 'blend',   icon: 'ic-flask',     name: 'Купаж',                  text: 'Скласти смак і повторити його від партії до партії', comps: ['K9'] },
    { id: 'finish',  icon: 'ic-drop',      name: 'Фільтрація й розлив',    text: 'Щоб напій не мутнів і доїхав до полиці', comps: ['K10'] },
    { id: 'sensory', icon: 'ic-nose',      name: 'Дегустація',             text: 'Мова опису, методики, пошук дефектів', comps: ['K12'] },
    { id: 'lab',     icon: 'ic-lab',       name: 'Лабораторія та якість',  text: 'Аналізи, класифікація, безпечність продукції', comps: ['K13', 'K14'] },
    { id: 'biz',     icon: 'ic-factory',   name: 'Власна дистилерія',      text: 'Проєкт, ліцензії, бренд і бізнес-план', comps: ['K15', 'K16', 'K17', 'K18'] },
  ];

  // Ключові слова — другий спосіб. Кожне прив'язане до модулів матриці;
  // назва напою тягне ще й сам напій як контекст.
  const WORD_GROUPS = [
    { name: 'Сировина', words: [
      ['grain', 'зерно', ['K2a', 'C2']], ['malt', 'солод', ['K2a', 'C2']],
      ['fruits', 'фрукти', ['K2b', 'C1']], ['grape', 'виноград', ['K2b', 'C1']],
      ['honey', 'мед', ['K2c']], ['water', 'вода', ['K3']],
    ] },
    { name: 'Бродіння', words: [
      ['yeast', 'дріжджі', ['K4']], ['mash', 'бражка', ['K4']], ['ferment', 'бродіння', ['K4']],
    ] },
    { name: 'Перегонка', words: [
      ['run', 'перегонка', ['K7']], ['cuts', 'голови й хвости', ['K7']],
      ['alembic', 'аламбік', ['K6']], ['column', 'колона', ['K6', 'K5']],
      ['rectify', 'ректифікація', ['K5']], ['gear', 'обладнання', ['K6']],
    ] },
    { name: 'Доведення', words: [
      ['cask', 'бочка', ['K8']], ['aging', 'витримка', ['K8']], ['blend', 'купаж', ['K9']],
      ['filter', 'фільтрація', ['K10']], ['bottling', 'розлив', ['K10']],
      ['botanicals', 'ботанікали', ['BOT']], ['maceration', 'мацерація', ['BOT']],
      ['tincture', 'настоянки', ['BOT', 'C8']],
    ] },
    { name: 'Напої', words: [
      ['whisky', 'віскі', null, 'whisky'], ['vodka', 'водка', null, 'vodka'],
      ['gin', 'джин', null, 'gin'], ['vermouth', 'вермут і біттери', null, 'bitters'],
      ['brandy', 'бренді й коньяк', null, 'fruit'], ['rum', 'ром', null, 'rum'],
    ] },
    { name: 'Якість', words: [
      ['tasting', 'дегустація', ['K12']], ['faults', 'дефекти смаку', ['K12']],
      ['lab', 'лабораторія', ['K13']], ['analysis', 'аналізи', ['K13']],
      ['haccp', 'безпечність і HACCP', ['K14']], ['classes', 'класифікація напоїв', ['K14']],
      ['safety', 'техніка безпеки', ['K1']],
    ] },
    { name: 'Бізнес', words: [
      ['distillery', 'відкрити дистилерію', ['K15', 'K16', 'K18']], ['project', 'проєкт цеху', ['K15']],
      ['licence', 'ліцензія', ['K16']], ['excise', 'облік спирту', ['K16']],
      ['brand', 'бренд', ['K17']], ['label', 'етикетка', ['K17']], ['sales', 'збут', ['K17']],
      ['plan', 'бізнес-план', ['K18']], ['cost', 'собівартість', ['K18']],
    ] },
  ];
  const DRINK_BY = Object.fromEntries(DRINKS.map(d => [d.id, d]));
  const WORDS = WORD_GROUPS.flatMap(g => g.words.map(([id, name, comps, drink]) =>
    ({ id, name, group: g.name, drink: drink || null, comps: comps || DRINK_BY[drink].core })));

  // «Увесь шлях» — усе виробництво без бізнесу й без станцій, яким обрані
  // напої не дають сенсу (ботанікали для віскі, бочка для джину).
  const fullPath = drinks => STAGES.filter(s => s.id !== 'biz' && s.comps.some(id =>
    !ONLY_FOR[id] || !drinks.length || drinks.some(d => ONLY_FOR[id].includes(d)))).map(s => s.id);

  const PERSON_BY = Object.fromEntries(PERSON.map(p => [p.id, p]));
  const STAGE_BY = Object.fromEntries(STAGES.map(s => [s.id, s]));
  const WORD_BY = Object.fromEntries(WORDS.map(w => [w.id, w]));
  const uniq = list => [...new Set(list)];

  function create(M) {
    const byId = Object.fromEntries(M.COMPS.map(c => [c.id, c]));
    const groupOf = {};
    Object.entries(M.GROUPS).forEach(([g, { members }]) => members.forEach(id => { groupOf[id] = g; }));
    const total = M.COMPS.length;

    // Порядок у програмі — як у «Майстрі»: за модулем першого предмета.
    // Ботанікали в «Майстра» не входять, тож стоять одразу після перегонки.
    const place = Object.fromEntries(M.COMPS.map((c, i) => {
      const mod = c.main.length ? Number(M.SUBJECTS[c.main[0]][0]) : 4.5;
      return [c.id, mod * 100 + i];
    }));

    // Хто з групи «достатньо однієї» потрапляє в програму: вибір людини,
    // інакше — під її напої, інакше — перший у групі.
    function choose(group, drinks, pick) {
      const members = M.GROUPS[group].members;
      if (members.includes(pick[group])) return [pick[group]];
      const mine = uniq(drinks.map(d => DRINK_BY[d][group]).filter(Boolean));
      return mine.length ? mine : [members[0]];
    }

    /* Індивідуальна програма з відповідей.
       answers: { level, drinks[], stages[], words[], extra[], drop[], pick{} } —
       extra/drop/pick це правки людини вже в готовій програмі. */
    function programme(answers) {
      const person = PERSON_BY[answers.level] || PERSON_BY.practitioner;
      const words = (answers.words || []).map(id => WORD_BY[id]).filter(Boolean);
      const drinks = uniq([...(answers.drinks || []), ...words.map(w => w.drink)].filter(d => DRINK_BY[d]));
      const drop = new Set(answers.drop || []);
      const pick = answers.pick || {};
      const mods = new Map();
      const held = [];

      const add = (id, role, extra) => {
        if (!byId[id] || drop.has(id) || mods.has(id)) return false;
        mods.set(id, { id, role, via: [], ...extra });
        return true;
      };
      const addGroup = (group, role, extra) => {
        const ids = choose(group, drinks, pick);
        ids.forEach(id => add(id, role, { ...extra, choice: ids.length === 1 ? group : null }));
      };

      // 1. Цілі — те, що людина обрала сама. Сировина — під напій; напою
      // без бродіння (джин) зі станції «Сировина й вода» лишається вода.
      (answers.stages || []).map(id => STAGE_BY[id]).filter(Boolean).forEach(stage => {
        stage.comps.forEach(id => {
          if (id !== '@raw') add(id, 'goal');
          else if (pick.raw || drinks.some(d => DRINK_BY[d].raw)) addGroup('raw', 'goal');
          else if (!drinks.length) M.GROUPS.raw.members.forEach(m => add(m, 'goal'));
        });
      });
      words.forEach(w => w.comps.forEach(id => add(id, 'goal')));
      (answers.extra || []).forEach(id => add(id, 'goal'));

      // 2. Модуль про напій, який людина обрала.
      (answers.drinks || []).filter(d => DRINK_BY[d]).forEach(d => DRINK_BY[d].ctx.forEach(id => add(id, 'drink')));

      // 3. Основа: на що це спирається, DEPTH кроків назад по матриці.
      const fits = id => !drinks.length || !ONLY_FOR[id] || drinks.some(d => ONLY_FOR[id].includes(d));
      let front = [...mods.keys()];
      for (let depth = 1; depth <= DEPTH; depth++) {
        const next = [];
        const base = (id, target) => {
          if (mods.has(id)) { if (mods.get(id).role === 'base') mods.get(id).via.push(target); return; }
          if (drop.has(id) || !fits(id)) return;
          // Новачкові підприємство саме не додається — хіба що він уже там.
          if (person.noBusiness && byId[id].domain === 'biz' && byId[target].domain !== 'biz') {
            held.push(id);
            return;
          }
          return add(id, 'base', { via: [target], depth }) && next.push(id);
        };
        front.forEach(target => {
          const groups = new Set();
          M.EDGES.filter(e => e[1] === target).forEach(([from, , kind = '']) => {
            if (!kind.startsWith('any:')) return base(from, target);
            groups.add(kind.slice(4));
          });
          // Група: якщо хтось із неї вже в програмі, передумову виконано.
          groups.forEach(group => {
            const members = M.GROUPS[group].members;
            const have = members.filter(m => mods.has(m));
            if (have.length) return have.forEach(m => base(m, target));
            const ids = choose(group, drinks, pick);
            ids.forEach(id => {
              if (base(id, target) && ids.length === 1) mods.get(id).choice = group;
            });
          });
        });
        front = next;
      }

      // Порядок — як у «Майстрі», але кожен модуль після того, на що спирається.
      const order = [];
      const visit = id => {
        if (order.includes(id)) return;
        order.push(null);  // місце зайняте: цикл у матриці не зациклить обхід
        const at = order.length - 1;
        const before = M.EDGES.filter(e => e[1] === id && mods.has(e[0])).map(e => e[0]);
        order.splice(at, 1);
        before.sort((a, b) => place[a] - place[b]).forEach(visit);
        if (!order.includes(id)) order.push(id);
      };
      [...mods.keys()].sort((a, b) => place[a] - place[b]).forEach(visit);

      const modules = order.map(id => {
        const m = mods.get(id);
        const comp = byId[id];
        return {
          id, comp, role: m.role, via: uniq(m.via), choice: m.choice || null,
          options: m.choice ? M.GROUPS[m.choice].members.filter(x => x === id || !mods.has(x)) : [],
          level: person[m.role],
          weight: m.role === 'goal' ? 1 : m.role === 'drink' ? DRINK_WEIGHT : person.baseWeight,
        };
      });
      const subjects = uniq(modules.flatMap(m => m.comp.main));
      const formats = uniq(subjects.map(s => M.MODULES.find(x => x.n === M.SUBJECTS[s][0]).fmt));
      return { person, drinks, modules, held: uniq(held), subjects, formats, share: modules.length / total };
    }

    const coverOf = courseId => M.COMPS.filter(c => c.courses.includes(courseId)).map(c => c.id);

    // Наскільки готовий курс закриває програму, у відсотках.
    function score(course, prog) {
      const cover = new Set(coverOf(course.id));
      const focus = COURSE_FOCUS[course.id];
      const need = prog.modules;
      const hit = need.filter(m => cover.has(m.id));
      const sum = (list, value) => list.reduce((acc, m) => acc + value(m), 0);
      const got = sum(hit, m => m.weight * (m.role !== 'goal' || !focus || focus.includes(m.id) ? 1 : PASSING));
      const recall = need.length ? got / sum(need, m => m.weight) : 0;
      const extra = [...cover].filter(id => !need.some(m => m.id === id));
      let fit = recall * (1 - BREADTH.weight * (extra.length / total) ** BREADTH.power);
      const theme = COURSE_DRINKS[course.id];
      const ownDrink = prog.drinks.some(d => DRINK_COURSE[d] === course.id);
      const otherDrink = !!(theme && prog.drinks.length && !prog.drinks.some(d => theme.includes(d)));
      if (otherDrink) fit *= OTHER_DRINK;
      let percent = Math.round(fit * 100);
      const early = course.id === FLAGSHIP && !!prog.person.noBusiness;
      if (early) percent = Math.min(Math.round(fit * NOVICE_FLAGSHIP.factor * 100), NOVICE_FLAGSHIP.cap);
      return {
        id: course.id, course, percent, early, ownDrink, otherDrink,
        hit: hit.map(m => m.id),
        miss: need.filter(m => !cover.has(m.id)).map(m => m.id),
        extra,
      };
    }

    /* Результат: індивідуальний курс (завжди 100% і завжди перший) і готові
       курси від SHOW_FROM %. Курс про обраний напій (джин → «Майстерня
       джину») — завжди, зі своїм чесним відсотком: людина, що обрала джин,
       шукає саме його. Порядок: «Майстер» першим (крім новачка — див.
       NOVICE_FLAGSHIP), далі найкращі зверху. */
    // Великий курс — першим серед готових, але не новачкові.
    const lead = r => r.id === FLAGSHIP && !r.early ? 1 : 0;

    function match(answers) {
      const prog = programme(answers);
      const ready = prog.modules.length
        ? M.COURSES.map(c => score(c, prog)).filter(r => r.percent >= SHOW_FROM || r.ownDrink)
            .sort((a, b) => (lead(b) - lead(a)) || (b.percent - a.percent))
        : [];
      return { programme: prog, individual: { id: 'individual', percent: 100 }, ready };
    }

    return { programme, match, coverOf, byId, groupOf };
  }

  root.UDA_ENGINE = {
    create, fullPath, SHOW_FROM, FLAGSHIP, PERSON, DRINKS, STAGES, WORD_GROUPS, WORDS,
    PERSON_BY, DRINK_BY, STAGE_BY, WORD_BY,
  };
})(globalThis);
