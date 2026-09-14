/* Легкий вбудований YouTube: до кліку на сторінці лише локальний постер,
   плеєр підвантажується на вимогу. */
(function () {
    document.addEventListener('click', function (event) {
        var button = event.target.closest('.video-play');
        if (!button) return;

        var card = button.closest('[data-video]');
        if (!card) return;

        var frame = document.createElement('iframe');
        frame.src = 'https://www.youtube-nocookie.com/embed/'
            + encodeURIComponent(card.dataset.video) + '?autoplay=1&rel=0';
        frame.title = button.getAttribute('aria-label') || 'Відео';
        frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
        frame.allowFullscreen = true;
        frame.referrerPolicy = 'strict-origin-when-cross-origin';
        button.replaceWith(frame);
    });
})();
