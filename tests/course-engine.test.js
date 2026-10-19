/* Правила конструктора курсів (static/js/course-engine.js) на справжній
   матриці. Запуск: `node tests/course-engine.test.js`; з Django його ганяє
   core.tests.ConstructorEngineTests, якщо на машині є node. */
const assert = require('node:assert/strict');
const path = require('node:path');

const js = file => path.join(__dirname, '..', 'static', 'js', file);
require(js('competency-data.js'));
require(js('course-engine.js'));

const M = globalThis.UDA_MATRIX;
const E = globalThis.UDA_ENGINE;
const engine = E.create(M);

const ids = answers => engine.programme(answers).modules.map(m => m.id);
const ready = answers => engine.match(answers).ready;
const percent = (answers, course) => (ready(answers).find(r => r.id === course) || {}).percent;

const tests = {
  'довідники конструктора посилаються лише на те, що є в матриці'() {
    const comps = new Set(M.COMPS.map(c => c.id));
    const courses = new Set(M.COURSES.map(c => c.id));
    E.WORDS.forEach(w => w.comps.forEach(id => assert.ok(comps.has(id), `${w.name}: ${id}`)));
    E.STAGES.forEach(s => s.comps.filter(id => id !== '@raw')
      .forEach(id => assert.ok(comps.has(id), `${s.name}: ${id}`)));
    E.DRINKS.forEach(d => [...d.ctx, ...d.core, d.raw, d.cats].filter(Boolean)
      .forEach(id => assert.ok(comps.has(id), `${d.name}: ${id}`)));
    assert.ok(courses.has(E.FLAGSHIP));
    assert.equal(new Set(E.WORDS.map(w => w.id)).size, E.WORDS.length, 'слова не повторюються');
  },

  'індивідуальний курс завжди 100% і завжди перший'() {
    for (const level of E.PERSON.map(p => p.id)) {
      const result = engine.match({ level, drinks: ['gin'], stages: ['botan'] });
      assert.deepEqual(result.individual, { id: 'individual', percent: 100 });
    }
  },

  'курси, що підходять менше ніж на 70%, не показуються — крім курсу про напій'() {
    assert.equal(E.SHOW_FROM, 70);
    for (const level of E.PERSON.map(p => p.id)) {
      for (const word of E.WORDS) {
        ready({ level, words: [word.id] }).forEach(r =>
          assert.ok((r.percent >= 70 || r.ownDrink) && r.percent <= 100, `${word.name}: ${r.id} ${r.percent}`));
      }
    }
  },

  'готові курси: «Майстер» першим, далі від найкращого'() {
    const list = ready({ level: 'practitioner', words: ['ferment'] });
    assert.ok(list.length > 1);
    const rest = list.filter(r => r.id !== E.FLAGSHIP).map(r => r.percent);
    assert.deepEqual(rest, [...rest].sort((a, b) => b - a));
    // Віскі на весь шлях: «Майстер» перший, хоч і не єдиний.
    const whisky = ready({ level: 'practitioner', drinks: ['whisky'], stages: E.fullPath(['whisky']) });
    assert.equal(whisky[0].id, E.FLAGSHIP);
  },

  'курс про обраний напій є завжди — на будь-якому рівні й маршруті'() {
    for (const level of E.PERSON.map(p => p.id)) {
      for (const stages of [[], ['sensory'], ['raw'], ['lab'], E.fullPath(['gin'])]) {
        const gin = ready({ level, drinks: ['gin'], stages }).find(r => r.id === 'gin');
        assert.ok(gin && gin.ownDrink, `${level} ${stages.join('+') || 'лише напій'}`);
      }
    }
    const whole = ready({ level: 'pro', drinks: ['gin'], stages: E.fullPath(['gin']) });
    assert.ok(whole.every(r => r.ownDrink || r.percent >= 70));
  },

  'зерно — це насамперед курси про зернові дистиляти, а не «Майстер»'() {
    const list = ready({ level: 'practitioner', words: ['grain'] }).map(r => r.id);
    assert.deepEqual([...list].sort(), ['grain', 'whisky']);
  },

  'купаж тягне модулі рівно на крок назад по матриці'() {
    assert.deepEqual(ids({ level: 'practitioner', words: ['blend'] }).sort(),
      ['BOT', 'K12', 'K7', 'K8', 'K9']);
    // Для віскі ботанікали зайві: основа підлаштовується під напій.
    assert.deepEqual(ids({ level: 'practitioner', drinks: ['whisky'], stages: ['blend'] }).sort(),
      ['C2', 'K12', 'K7', 'K8', 'K9']);
  },

  'кожен модуль стоїть після того, на що спирається'() {
    const order = ids({ level: 'practitioner', drinks: ['whisky'], stages: E.fullPath(['whisky']) });
    M.EDGES.forEach(([from, to]) => {
      if (order.includes(from) && order.includes(to)) {
        assert.ok(order.indexOf(from) < order.indexOf(to), `${from} має бути перед ${to}`);
      }
    });
  },

  'новачкові підприємство саме не додається'() {
    const novice = engine.programme({ level: 'novice', words: ['gear'] });
    assert.ok(!novice.modules.some(m => m.comp.domain === 'biz'));
    assert.deepEqual(novice.held, ['K15']);
    // Тому, хто вже виробляє, той самий запит його додає.
    assert.ok(ids({ level: 'practitioner', words: ['gear'] }).includes('K15'));
  },

  'новачок може обрати підприємство сам'() {
    assert.deepEqual(ids({ level: 'novice', stages: ['biz'] }).sort(), ['K15', 'K16', 'K17', 'K18']);
    assert.ok(ids({ level: 'novice', words: ['gear'], extra: ['K15'] }).includes('K15'));
  },

  '«Майстер» не буває першим для новачка'() {
    const everything = { drinks: ['whisky'], stages: [...E.fullPath(['whisky']), 'biz'] };
    const novice = engine.match({ level: 'novice', ...everything });
    const master = novice.ready.find(r => r.id === E.FLAGSHIP);
    assert.ok(master.early);
    assert.ok(master.percent < novice.individual.percent);
    assert.ok(master.percent < percent({ level: 'practitioner', ...everything }, E.FLAGSHIP));
    // І на вузький запит його не видно зовсім — нікому.
    for (const level of E.PERSON.map(p => p.id)) {
      assert.equal(percent({ level, words: ['blend'] }, E.FLAGSHIP), undefined);
    }
  },

  'майстерня про тему обганяє ті, де тема — один із днів'() {
    assert.equal(ready({ level: 'practitioner', stages: ['aging'] })[0].id, 'aging');
    assert.equal(ready({ level: 'practitioner', stages: ['sensory'] })[0].id, 'sensory');
    assert.equal(ready({ level: 'practitioner', stages: ['ferm'] })[0].id, 'ferm');
    assert.equal(ready({ level: 'novice', drinks: ['gin'], stages: ['botan', 'blend'] })[0].id, 'gin');
  },

  'курс про інший напій поступається курсу про свій'() {
    const whisky = { level: 'practitioner', drinks: ['whisky'], stages: ['raw', 'ferm', 'dist'] };
    const vodka = { ...whisky, drinks: ['vodka'] };
    assert.equal(ready(whisky)[0].id, 'whisky');
    assert.equal(ready(vodka)[0].id, 'grain');
  },

  'сировина без напою — уся, з напоєм — його; вибір людини важить більше'() {
    assert.deepEqual(ids({ level: 'practitioner', stages: ['raw'] }), ['K2a', 'K2b', 'K2c', 'K3']);
    assert.deepEqual(ids({ level: 'practitioner', drinks: ['fruit'], stages: ['raw'] }), ['C1', 'K2b', 'K3']);
    const swapped = engine.programme({ level: 'practitioner', drinks: ['fruit'], stages: ['raw'], pick: { raw: 'K2c' } });
    assert.ok(swapped.modules.some(m => m.id === 'K2c' && m.choice === 'raw'));
    assert.ok(!swapped.modules.some(m => m.id === 'K2b'));
  },

  'джин і настоянки не зброджують: ні сировини, ні бродіння самі не додаються'() {
    for (const drink of ['gin', 'bitters']) {
      const everything = { level: 'practitioner', drinks: [drink], stages: E.fullPath([drink]) };
      const got = ids(everything);
      ['K2a', 'K2b', 'K2c', 'K4'].forEach(id => assert.ok(!got.includes(id), `${drink}: ${id} у програмі`));
      assert.ok(got.includes('K7') && got.includes('K3'), `${drink}: перегонка й вода лишаються`);
      assert.ok(!E.fullPath([drink]).includes('ferm'), `${drink}: «увесь шлях» без бродіння`);
      assert.deepEqual(ids({ level: 'practitioner', drinks: [drink], stages: ['raw'] }).filter(id => id !== 'C7' && id !== 'C8'), ['K3']);
    }
    // Хто сам обрав бродіння — отримує його; сировини під джин так і немає.
    const ferm = ids({ level: 'practitioner', drinks: ['gin'], stages: ['ferm'] });
    assert.ok(ferm.includes('K4') && !ferm.some(id => ['K2a', 'K2b', 'K2c'].includes(id)));
    // Джин разом із віскі: сировина — під віскі.
    assert.ok(ids({ level: 'practitioner', drinks: ['gin', 'whisky'], stages: ['raw'] }).includes('K2a'));
  },

  'прибраний модуль не повертається як основа'() {
    assert.ok(!ids({ level: 'practitioner', words: ['blend'], drop: ['K7'] }).includes('K7'));
  },

  'рівень людини задає цільовий рівень модулів'() {
    const level = person => engine.programme({ level: person, words: ['blend'] }).modules;
    assert.equal(level('novice').find(m => m.id === 'K9').level, 1);
    assert.equal(level('novice').find(m => m.id === 'K7').level, 0);
    assert.equal(level('pro').find(m => m.id === 'K9').level, 2);
  },
};

let failed = 0;
for (const [name, run] of Object.entries(tests)) {
  try {
    run();
    console.log('ok   ' + name);
  } catch (error) {
    failed += 1;
    console.error('FAIL ' + name + '\n     ' + String(error.message).split('\n').join('\n     '));
  }
}
if (failed) process.exit(1);
