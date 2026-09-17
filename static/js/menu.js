(function () {
    // Сендвіч-меню в шапці: панель ховається атрибутом hidden, тож без
    // скрипта вона просто лишається закритою, а не висить розгорнутою.
    var menus = Array.prototype.slice.call(document.querySelectorAll('[data-menu]'));
    if (!menus.length) return;

    menus.forEach(function (menu) {
        var toggle = menu.querySelector('[data-menu-toggle]');
        var panel = menu.querySelector('[data-menu-panel]');
        if (!toggle || !panel) return;

        function setOpen(open) {
            panel.hidden = !open;
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            menu.classList.toggle('is-open', open);
        }

        toggle.addEventListener('click', function () {
            setOpen(panel.hidden);
        });

        // Клік поза меню закриває його — інакше панель лишалася б висіти
        // над сторінкою, по якій людина вже клікає.
        document.addEventListener('click', function (event) {
            if (!panel.hidden && !menu.contains(event.target)) setOpen(false);
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !panel.hidden) {
                setOpen(false);
                toggle.focus();
            }
        });
    });
})();
