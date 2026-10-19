/* Конструктор курсів — сторінка /academy/constructor/.

   Гра з трьох кроків («хто ви», «що в пляшці», «маршрут») або вибір за
   ключовими словами; далі — «перегонка» й результат: індивідуальна програма
   та готові курси з відсотком. Підбір рахує static/js/course-engine.js на
   матриці компетенцій, цей файл лише малює й слухає. */
(() => {
  const app = document.getElementById('cc-app');
  if (!app) return;

  const M = window.UDA_MATRIX, E = window.UDA_ENGINE;
  const engine = E.create(M);
  const catalog = Object.fromEntries(
    JSON.parse(document.getElementById('cc-catalog').textContent).map(c => [c.id, c]));
  // Ціни з платформи (schedule.pricing.public_prices): предмет «Майстра» за id
  // з матриці → години й ціна для студента, курс НБУ, ціни готових курсів.
  // Немає — конструктор працює, як раніше, без цін.
  const prices = JSON.parse(document.getElementById('cc-prices')?.textContent || 'null');
  const intro = document.getElementById('cc-intro');
  const enroll = document.getElementById('zapys');
  const form = document.getElementById('cc-form');
  const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const blank = () => ({
    mode: 'quest', step: 0, level: null, drinks: [], stages: [], words: [],
    extra: [], drop: [], pick: {}, course: 'individual', query: '',
  });
  let state = blank();

  // --- утиліти -------------------------------------------------------------
  const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
  const icon = id => `<svg class="ic" aria-hidden="true"><use href="#${id}"></use></svg>`;
  const plural = (n, forms) => {
    const a = n % 10, b = n % 100;
    return forms[a === 1 && b !== 11 ? 0 : a >= 2 && a <= 4 && (b < 12 || b > 14) ? 1 : 2];
  };
  const count = (n, forms) => `${n} ${plural(n, forms)}`;
  const toggle = (list, id) => list.includes(id) ? list.filter(x => x !== id) : [...list, id];
  // --- ціни ----------------------------------------------------------------
  const num = n => Math.round(n).toLocaleString('uk-UA');
  const inEur = n => prices && prices.rate ? Math.round(n / prices.rate) : null;
  const hoursText = h => `${String(Math.round(h * 10) / 10).replace('.', ',')} год`;
  // Гривні, під ними дрібно — євро за курсом НБУ.
  const money = n => `<span class="cc-money"><b>${num(n)}&nbsp;₴</b>${inEur(n) !== null ? `<small>≈&nbsp;${num(inEur(n))}&nbsp;€</small>` : ''}</span>`;
  // Ціна набору модулів. Кожен предмет — один раз; модуль без жодного
  // предмета з ціною (напр. ботанічні спирти — поза «Майстром») — у `unpriced`.
  function priceOf(comps) {
    if (!prices) return null;
    const seen = new Set(), unpriced = [];
    let uah = 0, hours = 0;
    comps.forEach(c => {
      const own = c.main.filter(s => prices.subjects[s]);
      if (!own.length) { unpriced.push(c); return; }
      own.filter(s => !seen.has(s)).forEach(s => {
        seen.add(s);
        uah += prices.subjects[s].uah;
        hours += prices.subjects[s].hours;
      });
    });
    return { uah, hours, unpriced };
  }

  // Програти CSS-анімацію класу ще раз, навіть якщо клас уже стоїть.
  const replay = (el, cls) => { el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls); };
  // Крапля падає в пляшку, а над нею спливає, що саме долили.
  function pour(name) {
    const art = app.querySelector('.cc-bottle-art');
    if (!art || calm) return;
    const add = (tag, cls, text) => {
      const el = document.createElement(tag);
      el.className = cls;
      if (text) el.textContent = text;
      el.addEventListener('animationend', () => el.remove());
      art.appendChild(el);
    };
    add('i', 'cc-pour');
    if (name) add('span', 'cc-plus', '+ ' + name);
    replay(art, 'is-splash');
  }
  // Число добігає від одного значення до іншого.
  function run(el, from, to, ms = 1000) {
    const started = performance.now();
    const tick = now => {
      const t = Math.min((now - started) / ms, 1);
      el.textContent = Math.round(from + (to - from) * (1 - Math.pow(1 - t, 3)));
      if (t < 1 && el.isConnected) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  const answers = () => ({
    level: state.level, extra: state.extra, drop: state.drop, pick: state.pick,
    ...(state.mode === 'words' ? { words: state.words } : { drinks: state.drinks, stages: state.stages }),
  });
  const ready = () => !!state.level && (state.mode === 'words' ? state.words : state.stages).length > 0;

  // Відповіді одним рядком — для посилання на результат і для форми:
  // після помилки сервер повертає сторінку, і результат треба показати знову.
  const KEYS = { d: 'drinks', s: 'stages', w: 'words', x: 'extra', r: 'drop' };
  const VALID = {
    drinks: E.DRINK_BY, stages: E.STAGE_BY, words: E.WORD_BY, extra: engine.byId, drop: engine.byId,
  };
  function pack() {
    const q = new URLSearchParams({ m: state.mode === 'words' ? 'w' : 'q', l: state.level });
    Object.entries(KEYS).forEach(([key, field]) => { if (state[field].length) q.set(key, state[field].join('.')); });
    const picks = Object.entries(state.pick).map(p => p.join('-'));
    if (picks.length) q.set('p', picks.join('.'));
    return q.toString();
  }
  function unpack(text) {
    const q = new URLSearchParams(text);
    const next = blank();
    next.mode = q.get('m') === 'w' ? 'words' : 'quest';
    next.level = E.PERSON_BY[q.get('l')] ? q.get('l') : null;
    Object.entries(KEYS).forEach(([key, field]) => {
      next[field] = (q.get(key) || '').split('.').filter(id => VALID[field][id]);
    });
    (q.get('p') || '').split('.').forEach(pair => {
      const [group, id] = pair.split('-');
      if (M.GROUPS[group] && M.GROUPS[group].members.includes(id)) next.pick[group] = id;
    });
    return next;
  }

  // --- пляшка --------------------------------------------------------------
  // Наповнюється з кожною відповіддю; колір рідини — за напоєм.
  const GLASS = 'M62 8h36v14h-4v62c0 22 34 30 34 66v196a14 14 0 0 1-14 14H46a14 14 0 0 1-14-14V150c0-36 34-44 34-66V22h-4z';
  const bottle = () => `
    <div class="cc-bottle">
      <div class="cc-bottle-art">
      <svg viewBox="0 0 160 368" aria-hidden="true">
        <defs><clipPath id="cc-glass"><path d="${GLASS}"/></clipPath></defs>
        <g clip-path="url(#cc-glass)">
          <rect class="cc-glass-back" width="160" height="368"/>
          <g class="cc-liquid">
            <path class="cc-wave" d="M-160 0q20-7 40 0t40 0 40 0 40 0 40 0 40 0 40 0 40 0V400H-160z"/>
          </g>
          <circle class="cc-bubble" cx="58" cy="330" r="3"/>
          <circle class="cc-bubble" cx="86" cy="340" r="2"/>
          <circle class="cc-bubble" cx="106" cy="325" r="2.5"/>
        </g>
        <path class="cc-glass" d="${GLASS}"/>
        <path class="cc-shine" d="M45 170v140"/>
        <rect class="cc-cork" x="64" y="-8" width="32" height="26" rx="4"/>
      </svg>
      </div>
      <div class="cc-label"></div>
    </div>`;

  const DOMAIN_ADJ = {
    base: 'Обачний', raw: 'Бродильний', dist: 'Перегінний', craft: 'Купажний',
    cats: 'Допитливий', quality: 'Лабораторний', biz: 'Підприємливий',
  };
  const COMP_ADJ = { K8: 'Бочковий', BOT: 'Ботанічний', K12: 'Сенсорний', K2a: 'Зерновий', K2b: 'Плодовий', K2c: 'Медовий' };
  // Ім'я профілю: «Солодовий шукач», «Купажний майстер».
  function persona(prog) {
    const drink = E.DRINK_BY[prog.drinks[0]];
    const goal = prog.modules.find(m => m.role === 'goal');
    const adj = drink ? drink.adj : goal ? COMP_ADJ[goal.id] || DOMAIN_ADJ[goal.comp.domain] : 'Майбутній';
    return `${adj} ${prog.person.rank.toLowerCase()}`;
  }

  function fill() {
    const picked = state.mode === 'words' ? state.words.length / 4 : state.stages.length / 6;
    return (state.level ? 0.22 : 0.05) + (state.drinks.length ? 0.18 : 0) + Math.min(picked, 1) * 0.42;
  }
  function syncBottle(full) {
    const el = app.querySelector('.cc-bottle');
    if (!el) return;
    const prog = state.level ? engine.programme(answers()) : null;
    const drink = E.DRINK_BY[(prog ? prog.drinks : state.drinks)[0]];
    el.style.setProperty('--fill', full ? 1 : fill());
    el.style.setProperty('--liq', drink ? drink.tone : 'var(--accent-300)');
    const lines = [];
    if (prog && prog.drinks.length) lines.push(prog.drinks.map(d => E.DRINK_BY[d].name).join(' · '));
    const n = prog ? prog.modules.length : 0;
    if (n) lines.push(count(n, ['модуль', 'модулі', 'модулів']));
    setLabel(el, prog ? persona(prog) : 'Ваш профіль', lines);
  }
  // Етикетка «підстрибує», коли на ній щось змінилось.
  function setLabel(el, name, lines) {
    const label = el.querySelector('.cc-label');
    const sign = [name, ...lines].join('|');
    if (label.dataset.sign === sign) return;
    const fresh = label.dataset.sign === undefined;
    label.dataset.sign = sign;
    label.innerHTML = `<span class="cc-label-kicker">Рецепт курсу</span><strong>${esc(name)}</strong>` +
      lines.map(l => `<span>${esc(l)}</span>`).join('');
    if (!fresh) replay(label, 'is-changed');
  }

  // На старті пляшка сама показує, що вийде: наливається різним і міняє ім'я.
  const DEMO = [
    ['whisky', 'Солодовий практик', 0.62], ['gin', 'Ботанічний шукач', 0.4],
    ['fruit', 'Плодовий майстер', 0.8], ['honey', 'Медовий шукач', 0.52],
  ];
  let demoTimer = 0;
  function demo() {
    clearInterval(demoTimer);
    if (calm) return;
    let i = 0;
    demoTimer = setInterval(() => {
      const el = app.querySelector('.cc-start .cc-bottle');
      if (!el) return clearInterval(demoTimer);
      const [drink, name, level] = DEMO[i++ % DEMO.length];
      el.style.setProperty('--fill', level);
      el.style.setProperty('--liq', E.DRINK_BY[drink].tone);
      setLabel(el, name, [E.DRINK_BY[drink].name]);
      pour();
    }, 2300);
  }

  // --- екрани --------------------------------------------------------------
  function show(html, { top = true } = {}) {
    app.innerHTML = html;
    if (intro) intro.hidden = state.screen !== 'intro';
    // На головній гра стартує карткою в героя, а далі займає всю його ширину.
    app.closest('.cc').classList.toggle('is-playing', state.screen !== 'intro');
    enroll.hidden = true;
    const head = app.querySelector('h2');
    if (head && state.screen !== 'intro') {
      head.tabIndex = -1;
      head.focus({ preventScroll: true });
    }
    if (top && state.screen !== 'intro') {
      const y = app.getBoundingClientRect().top;
      if (y < 0 || y > window.innerHeight * 0.4) {
        window.scrollTo({ top: window.scrollY + y - 110, behavior: calm ? 'auto' : 'smooth' });
      }
    }
  }

  function renderIntro() {
    state.screen = 'intro';
    show(`
      <div class="cc-start">
        <div class="cc-start-body">
          ${app.dataset.title ? `<span class="tag">Конструктор курсів</span><p class="cc-start-title">${esc(app.dataset.title)}</p>` : ''}
          <ol class="cc-how">
            <li style="--i:0"><b>1</b><span>Скажіть, хто ви біля куба</span></li>
            <li style="--i:1"><b>2</b><span>Налийте в пляшку свій напій</span></li>
            <li style="--i:2"><b>3</b><span>Прокладіть маршрут від сировини до полиці</span></li>
          </ol>
          <div class="cc-start-actions">
            <button type="button" class="btn btn-primary btn-lg cc-go" data-act="start"><i class="cc-go-drop"></i>Почати перегонку!<span class="cc-go-arrow" aria-hidden="true">→</span></button>
            <button type="button" class="btn btn-outline" data-act="words">Знаю, що шукаю — обрати за словами</button>
          </div>
          <p class="cc-fine">Хвилина часу, без реєстрації. Результат — програма під вас і готові курси, які підходять на ${E.SHOW_FROM}% і більше.</p>
        </div>
        <div class="cc-start-art">${bottle()}</div>
      </div>`);
    syncBottle();
    demo();
  }

  const LEVEL_ICON = { novice: 'ic-cap', practitioner: 'ic-still', pro: 'ic-diploma' };
  const STEPS = [
    { name: 'Засип', title: 'Хто ви біля куба?',
      hint: 'Від рівня залежить, з чого почнеться програма і наскільки глибоко вона піде.' },
    { name: 'Напій', title: 'Що наллємо в пляшку?',
      hint: 'Можна кілька. Ще не вирішили — тисніть «Далі», підберемо без прив\'язки до напою.' },
    { name: 'Маршрут', title: 'Що хочете прокачати?',
      hint: 'Позначте станції на шляху від сировини до полиці. Основу, без якої вони не працюють, додамо самі.' },
  ];

  function stepBody() {
    if (state.step === 0) {
      return `<div class="cc-levels">${E.PERSON.map((p, i) => `
        <button type="button" class="cc-level" style="--i:${i}" data-act="level" data-id="${p.id}" aria-pressed="${state.level === p.id}">
          <span class="icon-badge">${icon(LEVEL_ICON[p.id])}</span>
          <span class="cc-level-n">Рівень ${i + 1}</span>
          <strong>${esc(p.name)}</strong>
          <span>${esc(p.text)}</span>
        </button>`).join('')}</div>`;
    }
    if (state.step === 1) {
      return `<div class="cc-drinks">${E.DRINKS.map((d, i) => `
        <button type="button" class="cc-drink" style="--i:${i}" data-act="drink" data-id="${d.id}" aria-pressed="${state.drinks.includes(d.id)}">
          <i style="--liq:${d.tone}"></i>${esc(d.name)}
        </button>`).join('')}</div>`;
    }
    return `<div class="cc-route">${E.STAGES.map((s, i) => `
        <button type="button" class="cc-stage" style="--i:${i}" data-act="stage" data-id="${s.id}" aria-pressed="${state.stages.includes(s.id)}">
          <span class="cc-stage-n">${String(i + 1).padStart(2, '0')}</span>
          <span class="cc-stage-ic">${icon(s.icon)}</span>
          <strong>${esc(s.name)}</strong>
          <span>${esc(s.text)}</span>
        </button>`).join('')}</div>
      <button type="button" class="cc-link" data-act="all"></button>`;
  }
  const isFullPath = () => E.fullPath(state.drinks).every(id => state.stages.includes(id));

  function renderQuest() {
    state.screen = 'quest';
    state.mode = 'quest';
    const step = STEPS[state.step];
    const last = state.step === STEPS.length - 1;
    show(`
      <div class="cc-quest">
        <div class="cc-main">
          <ol class="cc-steps" aria-label="Кроки">${[...STEPS, { name: 'Розлив' }].map((s, i) =>
            `<li class="${i < state.step ? 'is-done' : i === state.step ? 'is-now' : ''}"${i === state.step ? ' aria-current="step"' : ''}><b>${i + 1}</b>${s.name}</li>`).join('')}</ol>
          <span class="cc-kicker">Крок ${state.step + 1} / ${STEPS.length}</span>
          <h2>${step.title}</h2>
          <p class="cc-hint">${step.hint}</p>
          <div id="cc-step" class="is-entering">${stepBody()}</div>
          <div class="cc-nav">
            <button type="button" class="btn btn-ghost" data-act="back">← Назад</button>
            <button type="button" class="btn btn-primary${last ? ' cc-go' : ''}" data-act="next">${last ? 'Перегнати в курс!<span class="cc-go-arrow" aria-hidden="true">→</span>' : 'Далі →'}</button>
          </div>
        </div>
        <aside class="cc-side" aria-hidden="true">${bottle()}</aside>
      </div>`);
    syncQuest();
  }

  // Після кліку нічого не перемальовується — лише перемикаються стани: і
  // картки не блимають, і рідина в пляшці піднімається плавно.
  function syncQuest() {
    const picked = { level: [state.level], drink: state.drinks, stage: state.stages };
    app.querySelectorAll('#cc-step [data-id]').forEach(b =>
      b.setAttribute('aria-pressed', String(picked[b.dataset.act].includes(b.dataset.id))));
    const all = app.querySelector('[data-act="all"]');
    if (all) all.textContent = isFullPath() ? 'Зняти все' : 'Позначити весь шлях — від сировини до пляшки';
    const next = app.querySelector('[data-act="next"]');
    const off = state.step === 0 ? !state.level : state.step === 2 ? !state.stages.length : false;
    if (next.disabled && !off && !calm) replay(next, 'is-ready');
    next.disabled = off;
    syncBottle();
  }

  function renderWords() {
    state.screen = 'words';
    state.mode = 'words';
    show(`
      <div class="cc-quest">
        <div class="cc-main">
          <span class="cc-kicker">Вибір за словами</span>
          <h2>Що хочете вивчити?</h2>
          <p class="cc-hint">Позначте кілька слів — за ними стоять модулі програми Академії. Основу, на яку вони спираються, додамо самі.</p>
          <div class="cc-seg" role="group" aria-label="Ваш рівень">
            <span class="cc-seg-label">Ваш рівень:</span>
            ${E.PERSON.map(p => `<button type="button" data-act="level" data-id="${p.id}" aria-pressed="${state.level === p.id}" title="${esc(p.text)}">${esc(p.name)}</button>`).join('')}
          </div>
          <label class="visually-hidden" for="cc-search">Пошук слова</label>
          <input type="search" id="cc-search" placeholder="Пошук: бочка, дріжджі, ліцензія…" value="${esc(state.query)}" autocomplete="off">
          <div id="cc-step" class="is-entering"></div>
          <div class="cc-nav">
            <button type="button" class="btn btn-ghost" data-act="home">← До гри</button>
            <button type="button" class="btn btn-primary cc-go" data-act="distil"></button>
          </div>
        </div>
        <aside class="cc-side" aria-hidden="true">${bottle()}</aside>
      </div>`);
    syncWords(true);
  }

  // Список слів перемальовується лише від пошуку; клік по слову — ні.
  function syncWords(redraw) {
    const list = app.querySelector('#cc-step');
    if (redraw) {
      const q = state.query.trim().toLowerCase();
      let i = 0;
      const groups = E.WORD_GROUPS.map(g => ({
        name: g.name,
        words: E.WORDS.filter(w => w.group === g.name && (!q || w.name.includes(q) || state.words.includes(w.id))),
      })).filter(g => g.words.length);
      list.innerHTML = groups.length
        ? groups.map(g => `<div class="cc-words"><h3>${esc(g.name)}</h3><div>${g.words.map(w =>
            `<button type="button" class="cc-word" style="--i:${i++}" data-act="word" data-id="${w.id}">${esc(w.name)}</button>`).join('')}</div></div>`).join('')
        : `<p class="cc-hint">Такого слова в нас немає. Спробуйте інше або <button type="button" class="cc-link" data-act="start">пройдіть гру з трьох кроків</button>.</p>`;
    }
    list.querySelectorAll('.cc-word').forEach(b => b.setAttribute('aria-pressed', String(state.words.includes(b.dataset.id))));
    app.querySelectorAll('.cc-seg [data-id]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.id === state.level)));
    const go = app.querySelector('[data-act="distil"]');
    const off = !ready();
    if (go.disabled && !off && !calm) replay(go, 'is-ready');
    go.disabled = off;
    go.innerHTML = !state.level ? 'Оберіть рівень' : !state.words.length ? 'Оберіть хоча б одне слово'
      : 'Перегнати в курс!<span class="cc-go-arrow" aria-hidden="true">→</span>';
    syncBottle();
  }

  // «Перегонка»: спершу краплі доливають пляшку до краю, потім вони
  // вщухають, пляшку закорковують — і лише тоді результат.
  const STILL = ['Нагріваємо куб…', 'Відсікаємо голови й хвости…', 'Збираємо серце програми…'];
  const STILL_MS = { line: 800, seal: 2400, end: 3300 };
  function renderStill() {
    if (calm) return renderResult(true);
    state.screen = 'still';
    show(`
      <div class="cc-still" role="status">
        <div class="cc-still-art">
          <div class="cc-drops"><i></i><i></i><i></i></div>
          ${bottle()}
        </div>
        <p class="cc-still-text">${STILL[0]}</p>
        <div class="cc-still-bar" style="--ms:${STILL_MS.end}ms"><i></i></div>
      </div>`);
    syncBottle();
    requestAnimationFrame(() => requestAnimationFrame(() => syncBottle(true)));
    const root = app.querySelector('.cc-still');
    const text = root.querySelector('.cc-still-text');
    const later = (ms, step) => setTimeout(() => { if (root.isConnected) step(); }, ms);
    const say = line => { text.textContent = line; replay(text, 'is-changed'); };
    STILL.slice(1).forEach((line, i) => later(STILL_MS.line * (i + 1), () => say(line)));
    later(STILL_MS.seal, () => { root.classList.add('is-sealed'); say('Закорковуємо!'); });
    later(STILL_MS.end, () => renderResult(true));
  }

  // --- результат -----------------------------------------------------------
  // from — з якого значення кільце добігає до свого відсотка (див. settle).
  const ring = (percent, from = percent) => `
    <div class="cc-ring" style="--p:${from}" data-from="${from}" data-to="${percent}" role="img" aria-label="Підходить на ${percent}%">
      <svg viewBox="0 0 64 64" aria-hidden="true"><circle class="cc-ring-track" cx="32" cy="32" r="28"/><circle class="cc-ring-value" cx="32" cy="32" r="28" pathLength="100"/></svg>
      <span><b>${from}</b>%</span>
    </div>`;
  const meter = level => `<span class="cc-meter">${[0, 1, 2].map(i => `<i class="${i <= level ? 'on' : ''}"></i>`).join('')}</span>`;
  const KIND = { program: 'Сертифікаційна програма · 60 днів', workshop: 'Курс Академії', masterclass: 'Майстер-клас · 1 день' };
  const ROLE = { goal: 'Ваша ціль', drink: 'Про ваш напій' };
  const title = id => engine.byId[id].title;
  const card = course => catalog[course.id] || { kind: 'workshop', title: course.name, text: '', image: '' };

  function moduleItem(m, i, isNew) {
    const c = m.comp;
    const topics = c.main.map(s => M.SUBJECTS[s][2]);
    const role = ROLE[m.role] || `Основа для: ${m.via.map(title).join(', ')}`;
    const options = m.options.length > 1 ? `
      <div class="cc-options" role="group" aria-label="Одна на вибір">
        <span>Одна на вибір:</span>
        ${m.options.map(id => `<button type="button" data-act="pick" data-group="${m.choice}" data-id="${id}" aria-pressed="${id === m.id}">${esc(title(id))}</button>`).join('')}
      </div>` : '';
    return `
      <li class="cc-mod cc-mod--${m.role}${isNew ? ' is-new' : ''}" style="--i:${i}">
        <span class="cc-mod-n">${i + 1}</span>
        <div class="cc-mod-body">
          <span class="cc-role">${esc(role)}</span>
          <h4>${esc(c.title)}</h4>
          ${moduleHours(c)}
          <p class="cc-out">${meter(m.level)}<b>Рівень «${M.LEVELS[m.level]}».</b> ${esc(c.levels[m.level])}</p>
          <p class="cc-topics">${topics.length ? 'Теми: ' + esc(topics.join(' · ')) : esc(c.can.join('. '))}</p>
          ${options}
        </div>
        <button type="button" class="cc-x" data-act="drop" data-id="${m.id}" aria-label="Прибрати модуль «${esc(c.title)}»" title="Прибрати модуль">×</button>
      </li>`;
  }

  // Ціни окремого модуля не показуємо — лише години: інакше з'являється
  // спокуса прибрати частину програми через ціну. Ціна — одна, за всю програму.
  function moduleHours(c) {
    const p = priceOf([c]);
    return p && !p.unpriced.length ? `<p class="cc-mod-hours">${hoursText(p.hours)}</p>` : '';
  }

  function ownPrice(prog) {
    const p = priceOf(prog.modules.map(m => m.comp));
    if (!p || !p.uah) return '';
    const rate = prices.rate ? ` за курсом НБУ на ${prices.rateDate}` : '';
    const excursion = prices.excursion ? ` Екскурсія на дистилерію — окремо, ${num(prices.excursion)}&nbsp;₴.` : '';
    const unpriced = p.unpriced.length
      ? ` ${p.unpriced.map(c => `«${esc(c.title)}»`).join(', ')} у цю суму не ${p.unpriced.length > 1 ? 'входять' : 'входить'} — вартість назве менеджер.` : '';
    return `
      <div class="cc-price">
        <span class="cc-price-label">Вартість програми</span>
        ${money(p.uah)}
        <p class="cc-price-note">${hoursText(p.hours)} занять із викладачами Академії${rate}.${excursion}${unpriced}</p>
      </div>`;
  }

  function readyPrice(id) {
    const p = prices && prices.courses[id];
    if (!p) return '';
    const uah = p.uah !== null ? ` (≈&nbsp;${num(p.uah)}&nbsp;₴)` : '';
    const early = p.earlyBird ? `, Early Bird — ${num(p.earlyBird.uah)}&nbsp;₴` : '';
    return `<p class="cc-ready-price">Ціна: <b>${num(p.eur)}&nbsp;€</b> з людини${uah}${early}.</p>`;
  }

  function ownCard(prog, from, isNew) {
    const inProg = new Set(prog.modules.map(m => m.id));
    // Власний проєкт — випускна робота «Майстра», в індивідуальний курс не йде.
    const spare = M.COMPS.filter(c => !inProg.has(c.id) && c.id !== 'K19');
    const addable = Object.entries(M.DOMAINS).map(([key, d]) => ({ d, comps: spare.filter(c => c.domain === key) })).filter(g => g.comps.length);
    const held = prog.held.filter(id => !inProg.has(id));
    return `
      <article class="cc-card cc-card--own" style="--i:0" data-course="individual">
        <span class="cc-stamp" aria-hidden="true">Найкращий збіг</span>
        <div class="cc-card-head">
          ${ring(100, from)}
          <div class="cc-card-text">
            <span class="tag tag-dark">Індивідуальний курс</span>
            <h3>Програма, складена під вас</h3>
            <p>Заняття з викладачами Академії за вашим графіком. Програму можна правити просто тут: прибирайте те, що вже знаєте, і додавайте своє.</p>
            <ul class="cc-facts">
              <li><b>${prog.modules.length}</b> ${plural(prog.modules.length, ['модуль', 'модулі', 'модулів'])}</li>
              <li><b>${prog.subjects.length}</b> ${plural(prog.subjects.length, ['тема', 'теми', 'тем'])}</li>
              <li><b>${Math.round(prog.share * 100)}%</b> повної програми Академії</li>
            </ul>
            ${ownPrice(prog)}
          </div>
          <button type="button" class="btn btn-primary" data-act="enroll" data-id="individual">Записатись</button>
        </div>
        <div class="cc-prog">
          <ol class="cc-mods">${prog.modules.map((m, i) => moduleItem(m, i, isNew(m.id))).join('')}</ol>
          ${held.length ? `<p class="cc-note">Для старту ми не додавали ${held.length > 1 ? 'модулі' : 'модуль'} про підприємство — ${held.map(id => `«${esc(title(id))}»`).join(', ')}: до цього варто дійти з базою.
            <button type="button" class="cc-link" data-act="add" data-id="${held[0]}">Додати все одно</button></p>` : ''}
          ${addable.length ? `<details class="cc-add">
            <summary>+ Додати модуль</summary>
            ${addable.map(g => `<div class="cc-words"><h3>${esc(g.d.name)}</h3><div>${g.comps.map(c =>
              `<button type="button" class="cc-word" data-act="add" data-id="${c.id}">${esc(c.title)}</button>`).join('')}</div></div>`).join('')}
          </details>` : ''}
        </div>
      </article>`;
  }

  function readyCard(r, prog, i, from, isNew) {
    const c = card(r.course);
    const goals = prog.modules.filter(m => m.role === 'goal');
    const goalsHit = goals.filter(m => r.hit.includes(m.id)).length;
    const why = (goals.length ? `${goalsHit} з ${count(goals.length, ['вашої цілі', 'ваших цілей', 'ваших цілей'])} і ` : '') +
      `${r.hit.length} з ${count(prog.modules.length, ['модуля', 'модулів', 'модулів'])} програми`;
    const line = (id, mark, cls) => `<li class="${cls}"><span>${mark}</span>${esc(title(id))}</li>`;
    const notes = [];
    if (r.early) notes.push('Для старту зарано: це повний цикл на 60 днів. Радимо почати з меншого й повернутись до «Майстра» з базою.');
    if (r.otherDrink) notes.push('Курс про інший напій, але основа у вас спільна.');
    if (r.ownDrink && r.percent < E.SHOW_FROM) notes.push('Курс саме про ваш напій, тож показуємо його, хоч решту програми він закриває лише частково.');
    return `
      <article class="cc-card${isNew ? ' is-new' : ''}" style="--i:${i + 1}" data-course="${r.id}">
        <div class="cc-card-head">
          ${ring(r.percent, from)}
          <div class="cc-card-text">
            <span class="tag tag-accent">${KIND[c.kind]}</span>${r.ownDrink ? ' <span class="tag tag-dark">Про ваш напій</span>' : ''}
            <h3>${esc(c.title)}</h3>
            <p>${esc(c.text)}</p>
            <p class="cc-why">Закриває ${why}.</p>
            ${readyPrice(r.id)}
            ${notes.map(n => `<p class="cc-note">${n}</p>`).join('')}
          </div>
          <button type="button" class="btn btn-outline" data-act="enroll" data-id="${r.id}">Записатись</button>
        </div>
        <details class="cc-inside"${i === 0 ? ' open' : ''}>
          <summary>Що в курсі з вашої програми</summary>
          <div class="cc-cover">
            <div><h4>Є в курсі</h4><ul>${r.hit.map(id => line(id, '✓', 'hit')).join('')}</ul></div>
            ${r.miss.length ? `<div><h4>Немає в курсі</h4><ul>${r.miss.map(id => line(id, '–', 'miss')).join('')}</ul></div>` : ''}
            ${r.extra.length ? `<div><h4>Понад вашу програму</h4><ul>${r.extra.map(id => line(id, '+', 'extra')).join('')}</ul></div>` : ''}
          </div>
          <a class="cc-link" href="${app.dataset.coursesUrl}">Усі курси Академії →</a>
        </details>
      </article>`;
  }

  let lastResult = null;
  // Що було на екрані до правки — щоб показати, що саме змінилось.
  let seen = null;

  function renderResult(first) {
    state.screen = 'result';
    const result = lastResult = engine.match(answers());
    const prog = result.programme;
    const picked = state.mode === 'words'
      ? state.words.map(id => E.WORD_BY[id].name)
      : [...state.drinks.map(id => E.DRINK_BY[id].name), ...state.stages.map(id => E.STAGE_BY[id].name)];
    const n = result.ready.length;
    // Скільки курсів пройшли поріг — курс про напій показується й нижче нього.
    const strong = result.ready.filter(r => r.percent >= E.SHOW_FROM).length;
    const themed = result.ready.some(r => r.percent < E.SHOW_FROM);
    const keep = first ? null : window.scrollY;
    const before = first ? null : seen;
    // Кільця: уперше — з нуля, після правки — з того, що було; нове — з нуля.
    const from = (id, percent) => calm ? percent : first ? 0 : !before ? percent : before.percents[id] || 0;
    const newModule = id => !!before && !before.modules.has(id);
    seen = {
      modules: new Set(prog.modules.map(m => m.id)),
      percents: Object.fromEntries([['individual', 100], ...result.ready.map(r => [r.id, r.percent])]),
    };

    show(`
      <div class="cc-result${first && !calm ? ' is-first' : ''}">
        <header class="cc-result-head">
          <span class="cc-kicker">Розлито · ваш профіль</span>
          <h2><span>${esc(persona(prog))}</span></h2>
          <p class="cc-hint">${strong
            ? `Ми склали програму під ваші відповіді й знайшли ${count(strong, ['готовий курс, який підходить', 'готові курси, які підходять', 'готових курсів, які підходять'])} вам на ${E.SHOW_FROM}% і більше.`
            : `Ми склали програму під ваші відповіді. Готового курсу, який підходив би вам на ${E.SHOW_FROM}% і більше, зараз немає — тож найкращий шлях індивідуальний.`}${themed ? ' Курс про ваш напій показуємо завжди.' : ''}</p>
          <div class="cc-recap">
            <span class="cc-chip cc-chip--level">${esc(prog.person.name)}</span>
            ${picked.map((name, i) => `<span class="cc-chip" style="--i:${i + 1}">${esc(name)}</span>`).join('')}
          </div>
          <div class="cc-tools">
            <button type="button" class="cc-link" data-act="edit">Змінити відповіді</button>
            <button type="button" class="cc-link" data-act="reset">Почати заново</button>
            ${navigator.clipboard ? '<button type="button" class="cc-link" data-act="share">Скопіювати посилання на результат</button>' : ''}
          </div>
        </header>
        <div class="cc-cards">
          ${prog.modules.length ? ownCard(prog, from('individual', 100), newModule) : '<p class="cc-note">У програмі не лишилось жодного модуля. <button type="button" class="cc-link" data-act="undo">Повернути прибране</button></p>'}
          ${n ? `<h3 class="cc-cards-title">Готові курси Академії</h3>` : ''}
          ${result.ready.map((r, i) => readyCard(r, prog, i, from(r.id, r.percent), !!before && !(r.id in before.percents))).join('')}
        </div>
        <p class="visually-hidden" role="status">${first ? '' : `Програму оновлено: ${count(prog.modules.length, ['модуль', 'модулі', 'модулів'])}.`}</p>
      </div>`, { top: first });

    // Правки в програмі не мають смикати сторінку.
    if (keep !== null) window.scrollTo(0, keep);
    settle(first ? 700 : 0);
    if (first && !calm) burst();
    syncEnroll(result);
    history.replaceState(null, '', '#' + pack());
  }

  // Кільця й числа добігають до своїх відсотків.
  function settle(delay) {
    app.querySelectorAll('.cc-ring').forEach(el => {
      const from = Number(el.dataset.from), to = Number(el.dataset.to);
      if (from === to) return;
      setTimeout(() => {
        el.style.setProperty('--p', to);
        run(el.querySelector('b'), from, to);
      }, delay + 30);
    });
  }

  // Бризки з-під імені профілю: мить, заради якої грали.
  function burst() {
    const name = app.querySelector('.cc-result-head h2 span');
    const box = document.createElement('div');
    box.className = 'cc-burst';
    box.style.left = Math.min(name.offsetWidth / 2, 260) + 'px';
    const tones = ['var(--copper)', 'var(--contrast)', 'var(--accent-300)', 'var(--contrast-light)'];
    for (let i = 0; i < 22; i++) {
      const angle = Math.PI * (1 + (i + Math.random()) / 22), far = 90 + Math.random() * 150;
      const drop = document.createElement('i');
      drop.style.cssText = `--dx:${Math.round(Math.cos(angle) * far * 1.6)}px;--dy:${Math.round(Math.sin(angle) * far)}px;` +
        `--c:${tones[i % tones.length]};animation-delay:${250 + Math.round(Math.random() * 180)}ms`;
      box.appendChild(drop);
    }
    name.parentNode.appendChild(box);
    setTimeout(() => box.remove(), 2200);
  }

  // --- запис ---------------------------------------------------------------
  const courseName = (id, result) => id === 'individual'
    ? 'Індивідуальний курс'
    : card(result.ready.find(r => r.id === id).course).title;

  function syncEnroll(result) {
    const options = ['individual', ...result.ready.map(r => r.id)];
    if (!options.includes(state.course)) state.course = 'individual';
    const select = document.getElementById('cc-course');
    select.innerHTML = options.map(id => {
      const percent = id === 'individual' ? 100 : result.ready.find(r => r.id === id).percent;
      return `<option value="${id}"${id === state.course ? ' selected' : ''}>${esc(courseName(id, result))} — ${percent}%</option>`;
    }).join('');
    enroll.hidden = !result.programme.modules.length;
    app.querySelectorAll('.cc-card').forEach(el => el.classList.toggle('is-chosen', el.dataset.course === state.course));
  }

  // Що менеджер побачить у заявці: вибір людини і те, що їй підібрали.
  function fillForm() {
    const result = lastResult, prog = result.programme;
    const percent = state.course === 'individual' ? 100 : result.ready.find(r => r.id === state.course).percent;
    const lines = [
      `Обрано: ${courseName(state.course, result)} (${percent}%)`,
      `Рівень: ${prog.person.name}`,
    ];
    if (state.mode === 'words') lines.push(`Слова: ${state.words.map(id => E.WORD_BY[id].name).join(', ')}`);
    else {
      lines.push(`Напій: ${state.drinks.map(id => E.DRINK_BY[id].name).join(', ') || 'не визначено'}`);
      lines.push(`Маршрут: ${state.stages.map(id => E.STAGE_BY[id].name).join(', ')}`);
    }
    lines.push('', 'Індивідуальна програма:');
    prog.modules.forEach((m, i) => lines.push(
      `${i + 1}. ${m.comp.title} — ${m.role === 'goal' ? 'ціль' : m.role === 'drink' ? 'про напій' : 'основа'}, рівень «${M.LEVELS[m.level]}»`));
    const p = priceOf(prog.modules.map(m => m.comp));
    if (p && p.uah) {
      const euros = inEur(p.uah) !== null ? ` (≈ ${num(inEur(p.uah))} €)` : '';
      lines.push(`Вартість індивідуальної програми: ${num(p.uah)} ₴${euros}, ${hoursText(p.hours)}` +
        (p.unpriced.length ? `; без ціни: ${p.unpriced.map(c => c.title).join(', ')}` : ''));
    }
    if (state.extra.length) lines.push(`Додано вручну: ${state.extra.map(title).join(', ')}`);
    if (state.drop.length) lines.push(`Прибрано вручну: ${state.drop.map(title).join(', ')}`);
    if (result.ready.length) {
      lines.push('', 'Готові курси, що підійшли:');
      result.ready.forEach(r => lines.push(`- ${card(r.course).title} — ${r.percent}%`));
    }
    form.elements.interest.value = `Конструктор: ${courseName(state.course, result)} — ${percent}%`.slice(0, 300);
    form.elements.details.value = lines.join('\n');
    form.elements.state.value = pack();
  }

  // --- події ---------------------------------------------------------------
  const ACTIONS = {
    start() { state = { ...blank(), step: 0 }; renderQuest(); },
    words() { state = blank(); renderWords(); },
    home() { state = blank(); seen = null; history.replaceState(null, '', location.pathname); renderIntro(); },
    reset() { ACTIONS.home(); },
    back() { if (state.step === 0) return ACTIONS.home(); state.step -= 1; renderQuest(); },
    next() { if (state.step === STEPS.length - 1) return renderStill(); state.step += 1; renderQuest(); },
    distil() { renderStill(); },
    level(id) {
      state.level = id;
      pour(E.PERSON_BY[id].name);
      if (state.screen === 'words') return syncWords();
      syncQuest();
      // Один вибір на кроці — одразу далі, без зайвого кліку.
      setTimeout(() => { if (state.screen === 'quest' && state.step === 0 && state.level === id) ACTIONS.next(); }, calm ? 0 : 380);
    },
    drink(id) {
      state.drinks = toggle(state.drinks, id);
      if (state.drinks.includes(id)) pour(E.DRINK_BY[id].name);
      syncQuest();
    },
    stage(id) {
      state.stages = toggle(state.stages, id);
      if (state.stages.includes(id)) pour(E.STAGE_BY[id].name);
      syncQuest();
    },
    all() {
      const full = isFullPath();
      state.stages = full ? [] : [...new Set([...state.stages, ...E.fullPath(state.drinks)])];
      if (!full) pour('Увесь шлях');
      syncQuest();
    },
    word(id) {
      state.words = toggle(state.words, id);
      if (state.words.includes(id)) pour(E.WORD_BY[id].name);
      syncWords();
    },
    // Правки в готовій програмі.
    drop(id) { state.drop = [...state.drop, id]; state.extra = state.extra.filter(x => x !== id); renderResult(); },
    add(id) { state.extra = [...state.extra, id]; state.drop = state.drop.filter(x => x !== id); renderResult(); },
    pick(id, el) { state.pick = { ...state.pick, [el.dataset.group]: id }; state.drop = state.drop.filter(x => x !== id); renderResult(); },
    undo() { state.drop = []; renderResult(); },
    edit() {
      Object.assign(state, { extra: [], drop: [], pick: {} });
      seen = null;
      if (state.mode === 'words') return renderWords();
      state.step = 0;
      renderQuest();
    },
    share(id, el) {
      navigator.clipboard.writeText(location.href).then(() => {
        el.textContent = 'Посилання скопійовано';
      }, () => {});
    },
    enroll(id) {
      state.course = id;
      syncEnroll(lastResult);
      enroll.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
      form.elements.name.focus({ preventScroll: true });
    },
  };

  app.addEventListener('click', event => {
    const el = event.target.closest('[data-act]');
    if (!el || el.disabled || !ACTIONS[el.dataset.act]) return;
    // Вступна анімація кроку вже своє відіграла — далі картки живуть самі.
    const entering = app.querySelector('#cc-step.is-entering');
    if (entering) entering.classList.remove('is-entering');
    ACTIONS[el.dataset.act](el.dataset.id, el);
    if (el.isConnected && el.getAttribute('aria-pressed') === 'true') replay(el, 'is-pop');
  });
  app.addEventListener('input', event => {
    if (event.target.id !== 'cc-search') return;
    state.query = event.target.value;
    // Пошук перемальовує список — без вступної анімації, інакше він блимає.
    app.querySelector('#cc-step').classList.remove('is-entering');
    syncWords(true);
  });
  document.getElementById('cc-course').addEventListener('change', event => {
    state.course = event.target.value;
    syncEnroll(lastResult);
  });
  form.addEventListener('submit', fillForm);

  // --- старт ---------------------------------------------------------------
  // Результат відновлюється з форми (сервер повернув її з помилками) або з
  // посилання, яким поділилися.
  const saved = form.elements.state.value || location.hash.slice(1);
  const restored = saved ? unpack(saved) : null;
  if (restored && (state = restored, ready())) {
    renderResult();
    if (form.querySelector('.errorlist')) enroll.scrollIntoView({ block: 'start' });
  } else {
    state = blank();
    renderIntro();
  }
})();
