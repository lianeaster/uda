// Стос фото лектора: картки лежать одна на одній (data-pos, 0 — зверху).
// Кожні кілька секунд верхня відлітає вбік і ховається під стос, наверх
// виходить наступна. Клік по стосу — наступне фото, крапка — будь-яке.
// Без скрипта видно верхню картку, решта лежить під нею.
(function () {
  var stacks = Array.prototype.slice.call(document.querySelectorAll('[data-stack]'));
  if (!stacks.length) return;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var STEP = 5000;
  var FLY = reduce ? 0 : 380;   // скільки картка «летить» убік, перш ніж лягти під низ

  stacks.forEach(function (stack) {
    var cards = Array.prototype.slice.call(stack.querySelectorAll('[data-pos]'));
    var dots = Array.prototype.slice.call(stack.querySelectorAll('[data-go]'));
    var count = cards.length;
    if (count < 2) return;

    // order[i] — номер картки на позиції i; order[0] — верхня.
    var order = cards.map(function (_, i) { return i; });
    var busy = false;

    function paint() {
      order.forEach(function (card, pos) { cards[card].setAttribute('data-pos', pos); });
      dots.forEach(function (dot, i) { dot.setAttribute('aria-current', i === order[0] ? 'true' : 'false'); });
    }

    // Підняти картку `card` наверх: ті, що були над нею, по черзі йдуть під низ.
    function show(card) {
      if (busy || card === order[0]) return;
      busy = true;
      var top = cards[order[0]];
      top.classList.add('is-flying');
      setTimeout(function () {
        while (order[0] !== card) order.push(order.shift());
        paint();
        top.classList.remove('is-flying');
        busy = false;
      }, FLY);
    }

    function next() { show(order[1]); }

    var timer = null;
    function start() { if (!reduce && !timer) timer = setInterval(next, STEP); }
    function stop() { clearInterval(timer); timer = null; }

    stack.querySelector('[data-stack-cards]').addEventListener('click', function () { stop(); next(); start(); });
    dots.forEach(function (dot) {
      dot.addEventListener('click', function () { stop(); show(parseInt(dot.getAttribute('data-go'), 10)); start(); });
    });
    // Поки людина роздивляється фото чи ходить клавіатурою — не гортаємо.
    stack.addEventListener('mouseenter', stop);
    stack.addEventListener('mouseleave', start);
    stack.addEventListener('focusin', stop);
    stack.addEventListener('focusout', start);
    document.addEventListener('visibilitychange', function () { document.hidden ? stop() : start(); });

    stack.classList.add('is-live');
    start();
  });
})();
