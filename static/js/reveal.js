(function () {
    var els = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]'));
    if (!els.length) return;

    // Anything already in view on load is revealed immediately — only
    // elements further down the page animate in as they are scrolled to.
    if (!('IntersectionObserver' in window)) {
        els.forEach(function (el) { el.classList.add('is-revealed'); });
        return;
    }

    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-revealed');
                observer.unobserve(entry.target);
            }
        });
    }, { rootMargin: '0px 0px -8% 0px' });

    els.forEach(function (el) {
        if (el.getBoundingClientRect().top < window.innerHeight * 0.92) {
            el.classList.add('is-revealed');
        } else {
            observer.observe(el);
        }
    });
})();
