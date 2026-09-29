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

  // --- план: де працює академія --------------------------------------------
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
      var slug = chip.getAttribute('data-academy');
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
        : used === total ? name + ' працює в усіх ' + total + ' приміщеннях.'
        : name + ' працює в ' + used + ' з ' + total + ' приміщень, решта — для інших академій.';
    });
  });

  if (!motion) return;

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
