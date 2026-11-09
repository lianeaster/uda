/* Анімації сайту Центру.
 *
 * Усе працює лише з класом `motion` на <html> (його ставить рядок у
 * <head>, якщо людина не просила в системі менше руху). Без нього сторінка
 * одразу показує кінцевий стан: цифри, логотип, план — нічого не ховається.
 *
 *  [data-play="<селектор>"]  сцена: коли потрапляє в поле зору, отримує
 *                            .is-playing, а її елементам (за селектором)
 *                            — --i, порядковий номер для затримки в CSS.
 *  [data-stagger]            картки з data-reveal всередині з'являються
 *                            по черзі (затримку ставимо до reveal.js).
 *  [data-count]              число рахує від нуля, коли його видно.
 *  [data-morph]              пункти списку змінюють один одного по колу.
 *  [data-emblem]             клік програє складання логотипа ще раз.
 *  [data-parallax]           сцена ледь іде за курсором (--px, --py від -.5
 *                            до .5); лише з мишею.
 *  [data-cycle]              пункти по черзі отримують .is-on, поки сцена
 *                            грає (.is-playing від data-play).
 *  [data-progress]           смужка прокрутки сторінки — працює й без руху.
 *  [data-compare]            «сировина → продукт»: повзунок відкриває одне
 *                            фото з-під іншого (--pos), кнопки міняють пару.
 *                            Працює й без руху; рух додає лише «підказку».
 *  [data-story]              етапи з фото: фото змінюється разом з етапом,
 *                            до якого догорнули. Теж працює й без руху.
 *  .u-card, .u-news-card     світлова пляма йде за курсором (--mx, --my).
 */
(function () {
  var motion = document.documentElement.classList.contains('motion');
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };

  // --- порядкові номери для сцен --------------------------------------------
  each(document.querySelectorAll('[data-play]'), function (scene) {
    each(scene.querySelectorAll(scene.getAttribute('data-play') || ':scope > *'), function (el, i) {
      el.style.setProperty('--i', i);
    });
  });

  // --- черга карток ---------------------------------------------------------
  // Затримку знімаємо після появи, інакше вона гальмувала б і hover.
  each(document.querySelectorAll('[data-stagger]'), function (group) {
    each(group.querySelectorAll('[data-reveal]'), function (el, i) {
      el.style.transitionDelay = (i * 90) + 'ms';
      el.addEventListener('transitionend', function clear() {
        el.style.transitionDelay = '';
        el.removeEventListener('transitionend', clear);
      });
    });
  });

  // --- план: де працюють із напрямом ----------------------------------------
  // Не анімація, а навігація, тож працює і з «менше руху». Приміщення без
  // data-uses (побутові, допоміжні) фільтр не чіпає.
  each(document.querySelectorAll('[data-plan]'), function (plan) {
    var filter = plan.querySelector('[data-plan-filter]');
    var status = plan.querySelector('[data-plan-status]');
    var list = plan.nextElementSibling;
    var rooms = Array.prototype.slice.call(plan.querySelectorAll('[data-uses]'))
      .concat(list ? Array.prototype.slice.call(list.querySelectorAll('[data-uses]')) : []);
    var total = plan.querySelectorAll('svg [data-uses]').length;
    if (!filter) return;
    filter.hidden = false;

    filter.addEventListener('click', function (event) {
      var chip = event.target.closest('button');
      if (!chip) return;
      var slug = chip.getAttribute('data-direction');
      each(filter.querySelectorAll('button'), function (b) {
        b.setAttribute('aria-pressed', b === chip ? 'true' : 'false');
      });
      var used = 0;
      rooms.forEach(function (room) {
        var on = !slug || room.getAttribute('data-uses').split(' ').indexOf(slug) !== -1;
        room.classList.toggle('is-dim', !on);
        room.classList.toggle('is-lit', !!slug && on);
        if (on && room.closest('svg')) used++;
      });
      var name = chip.getAttribute('data-name');
      status.textContent = !slug ? ''
        : used === total ? 'Напрям «' + name + '» — в усіх ' + total + ' приміщеннях.'
        : 'Напрям «' + name + '» — у ' + used + ' з ' + total + ' приміщень, решта — для інших напрямів.';
    });
  });

  // --- смужка прокрутки ------------------------------------------------------
  // Не анімація, а підказка, де ти на сторінці, тож працює і з «менше руху».
  var bar = document.querySelector('[data-progress]');
  if (bar) {
    var queued = false;
    var update = function () {
      var root = document.documentElement;
      var max = root.scrollHeight - root.clientHeight;
      bar.style.transform = 'scaleX(' + (max > 0 ? Math.min(window.scrollY / max, 1) : 0) + ')';
      queued = false;
    };
    window.addEventListener('scroll', function () {
      if (!queued) { queued = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  // --- сировина → продукт -----------------------------------------------------
  // Повзунок — звичайний range, тож миша, палець і стрілки працюють самі;
  // скрипт лише переносить його значення в --pos і перемикає пари.
  each(document.querySelectorAll('[data-compare]'), function (box) {
    var range = box.querySelector('[data-compare-range]');
    var tabs = document.querySelector('[data-compare-tabs]');
    var touched = false;
    var set = function (value) { box.style.setProperty('--pos', value + '%'); };
    range.addEventListener('input', function () { touched = true; set(range.value); });
    if (tabs) {
      tabs.hidden = false;
      tabs.addEventListener('click', function (event) {
        var chip = event.target.closest('button');
        if (!chip) return;
        each(tabs.querySelectorAll('button'), function (b) {
          b.setAttribute('aria-pressed', b === chip ? 'true' : 'false');
        });
        each(box.querySelectorAll('.u-compare-pair'), function (pair) {
          pair.classList.toggle('is-on', pair.getAttribute('data-pair') === chip.getAttribute('data-pair'));
        });
      });
    }
    // Підказка: коли блок уперше видно, повзунок сам ходить туди й назад.
    if (!motion || !('IntersectionObserver' in window)) return;
    var hint = function () {
      var start = null, duration = 2400;
      var step = function (now) {
        if (touched) return;
        if (start === null) start = now;
        var t = Math.min((now - start) / duration, 1);
        var value = 50 + 32 * Math.sin(t * Math.PI * 2) * (1 - t * 0.35);
        range.value = Math.round(value);
        set(value.toFixed(1));
        if (t < 1) requestAnimationFrame(step); else { range.value = 50; set(50); }
      };
      requestAnimationFrame(step);
    };
    var seen = new IntersectionObserver(function (entries) {
      if (!entries[0].isIntersecting) return;
      seen.disconnect();
      setTimeout(hint, 500);
    }, { threshold: 0.5 });
    seen.observe(box);
  });

  // --- етапи з фото ---------------------------------------------------------
  // Активний етап — той, до якого догорнули: його верх уже вище середини екрана.
  each(document.querySelectorAll('[data-story]'), function (story) {
    var steps = Array.prototype.slice.call(story.querySelectorAll('[data-story-step]'));
    var images = story.querySelectorAll('.u-story-img');
    var no = story.querySelector('[data-story-no]');
    var progress = story.querySelector('[data-story-bar]');
    if (steps.length < 2) return;
    var current = -1;
    var show = function (i) {
      if (i === current) return;
      current = i;
      steps.forEach(function (s, k) { s.classList.toggle('is-active', k === i); });
      each(images, function (img, k) { img.classList.toggle('is-on', k === i); });
      if (no) no.textContent = (i < 9 ? '0' : '') + (i + 1);
      if (progress) progress.style.transform = 'scaleX(' + ((i + 1) / steps.length) + ')';
    };
    // Останній етап, чий верх уже вище за середину екрана.
    var pick = function () {
      var middle = window.innerHeight / 2, active = 0;
      steps.forEach(function (s, k) { if (s.getBoundingClientRect().top < middle) active = k; });
      show(active);
      queued = false;
    };
    var queued = false;
    window.addEventListener('scroll', function () {
      if (!queued) { queued = true; requestAnimationFrame(pick); }
    }, { passive: true });
    window.addEventListener('resize', pick);
    pick();
  });

  if (!motion) return;

  // --- колаж героя йде за курсором, картки ловлять світло --------------------
  if (matchMedia('(pointer: fine)').matches) {
    each(document.querySelectorAll('[data-parallax]'), function (scene) {
      var area = scene.closest('section') || scene;
      area.addEventListener('pointermove', function (event) {
        var box = area.getBoundingClientRect();
        scene.style.setProperty('--px', ((event.clientX - box.left) / box.width - 0.5).toFixed(3));
        scene.style.setProperty('--py', ((event.clientY - box.top) / box.height - 0.5).toFixed(3));
      });
      area.addEventListener('pointerleave', function () {
        scene.style.setProperty('--px', 0);
        scene.style.setProperty('--py', 0);
      });
    });

    document.addEventListener('pointermove', function (event) {
      var card = event.target.closest && event.target.closest('.u-card, .u-news-card');
      if (!card) return;
      var box = card.getBoundingClientRect();
      card.style.setProperty('--mx', (event.clientX - box.left) + 'px');
      card.style.setProperty('--my', (event.clientY - box.top) + 'px');
    }, { passive: true });
  }

  // --- пункти підсвічуються по черзі ----------------------------------------
  each(document.querySelectorAll('[data-cycle]'), function (list) {
    var items = list.children, i = -1;
    if (!items.length) return;
    setInterval(function () {
      if (document.hidden || !list.classList.contains('is-playing')) return;
      if (items[i]) items[i].classList.remove('is-on');
      i = (i + 1) % items.length;
      items[i].classList.add('is-on');
    }, 2200);
  });

  // --- лічильники -----------------------------------------------------------
  function countUp(el) {
    var target = parseInt(el.getAttribute('data-target'), 10);
    var start = null, duration = 1400;
    function step(now) {
      if (start === null) start = now;
      var t = Math.min((now - start) / duration, 1);
      el.textContent = Math.round(target * (1 - Math.pow(1 - t, 3)));
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  each(document.querySelectorAll('[data-count]'), function (el) {
    el.setAttribute('data-target', el.textContent.trim());
    el.textContent = '0';
  });

  // --- запуск сцен при появі ------------------------------------------------
  var targets = document.querySelectorAll('[data-play], [data-count]');
  function play(el) {
    if (el.hasAttribute('data-count')) countUp(el);
    else el.classList.add('is-playing');
  }
  if (!('IntersectionObserver' in window)) {
    each(targets, play);
  } else {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        play(entry.target);
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.2 });
    each(targets, function (el) { observer.observe(el); });
  }

  // --- рядок перетворень у героя: «сировина → продукт» по черзі ---------------
  each(document.querySelectorAll('[data-morph]'), function (list) {
    var items = list.children, i = 0;
    if (items.length < 2) return;
    setInterval(function () {
      if (document.hidden) return;
      var prev = items[i];
      i = (i + 1) % items.length;
      prev.classList.remove('is-in');
      prev.classList.add('is-out');
      items[i].classList.remove('is-out');
      items[i].classList.add('is-in');
      setTimeout(function () { prev.classList.remove('is-out'); }, 650);
    }, 2600);
  });

  // --- логотип: ще раз по кліку ---------------------------------------------
  each(document.querySelectorAll('[data-emblem]'), function (emblem) {
    emblem.addEventListener('click', function () {
      emblem.classList.remove('is-playing');
      void emblem.offsetWidth;  // скинути анімації, щоб вони пішли з нуля
      emblem.classList.add('is-playing');
    });
  });
})();
