// Жива вітрина полиці випускників: картки стоять на місці, а по одній
// перевертаються й показують наступну пляшку. Нове фото спершу вантажиться на
// звороті, і лише тоді картка обертається — порожнього боку не видно.
// На екрані ніколи немає двох однакових фото.
(function () {
  var vitrine = document.querySelector('[data-vitrine]');
  var data = document.getElementById('vitrine-photos');
  if (!vitrine || !data) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var photos = JSON.parse(data.textContent);
  var cards = Array.prototype.slice.call(vitrine.querySelectorAll('.vitrine-card'));
  if (photos.length <= cards.length) return;

  var STEP = 2600;
  var FLIP = 900;                     // як transition у .vitrine-flip
  var shown = cards.map(function (_, i) { return i; });   // індекс фото на кожній картці
  var next = cards.length;            // наступне фото в черзі
  var last = -1;                      // щойно перевернута картка — її не чіпаємо двічі поспіль
  var busy = false;

  function pickCard() {
    var i;
    do { i = Math.floor(Math.random() * cards.length); } while (i === last && cards.length > 1);
    return i;
  }

  function pickPhoto() {
    // Далі по черзі, пропускаючи те, що вже на вітрині.
    for (var tries = 0; tries < photos.length; tries++) {
      var p = next;
      next = (next + 1) % photos.length;
      if (shown.indexOf(p) === -1) return p;
    }
    return -1;
  }

  function turn() {
    if (busy) return;
    var i = pickCard();
    var p = pickPhoto();
    if (p === -1) return;
    var card = cards[i];
    var photo = photos[p];
    var flipped = card.classList.contains('is-flipped');
    // Видимий бік — лицьовий, якщо картку ще не перевертали; новий кладемо на інший.
    var hidden = card.querySelectorAll('.vitrine-face img')[flipped ? 0 : 1];
    busy = true;
    hidden.onload = function () {
      hidden.onload = null;
      hidden.alt = photo.brand;
      hidden.parentNode.removeAttribute('aria-hidden');
      var visible = card.querySelectorAll('.vitrine-face img')[flipped ? 1 : 0];
      visible.alt = '';
      visible.parentNode.setAttribute('aria-hidden', 'true');
      card.classList.toggle('is-flipped');
      card.href = photo.url;
      setTimeout(function () {
        card.querySelector('.grad-photo-name').textContent = photo.brand;
        busy = false;
      }, FLIP / 2);
      shown[i] = p;
      last = i;
    };
    hidden.onerror = function () { busy = false; };
    hidden.src = photo.image;
  }

  var timer = null;
  var visibleOnScreen = false;
  var hovered = false;
  function sync() {
    var run = visibleOnScreen && !hovered && !document.hidden;
    if (run && !timer) timer = setInterval(turn, STEP);
    if (!run && timer) { clearInterval(timer); timer = null; }
  }

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      visibleOnScreen = entries[0].isIntersecting;
      sync();
    }).observe(vitrine);
  } else {
    visibleOnScreen = true;
  }
  // Поки людина роздивляється пляшку чи ходить клавіатурою — вітрина стоїть.
  vitrine.addEventListener('mouseenter', function () { hovered = true; sync(); });
  vitrine.addEventListener('mouseleave', function () { hovered = false; sync(); });
  vitrine.addEventListener('focusin', function () { hovered = true; sync(); });
  vitrine.addEventListener('focusout', function () { hovered = false; sync(); });
  document.addEventListener('visibilitychange', sync);
  sync();
})();
