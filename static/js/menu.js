(function () {
    // Сендвіч головного меню на вузькому екрані. Кнопка [data-nav-toggle]
    // називає своє меню в aria-controls; відкрите меню отримує .is-open, а
    // чи ховати закрите — вирішує CSS за шириною екрана й класом `js`.
    var toggles = Array.prototype.slice.call(document.querySelectorAll('[data-nav-toggle]'));

    toggles.forEach(function (toggle) {
        var nav = document.getElementById(toggle.getAttribute('aria-controls'));
        if (!nav) return;

        function isOpen() { return nav.classList.contains('is-open'); }
        function setOpen(open) {
            nav.classList.toggle('is-open', open);
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        }

        toggle.addEventListener('click', function () {
            setOpen(!isOpen());
        });

        // Пункт меню часто веде на якір тієї ж сторінки — меню має згорнутись,
        // а не лишитись висіти над секцією, куди людина щойно перейшла.
        nav.addEventListener('click', function (event) {
            if (event.target.closest('a')) setOpen(false);
        });

        document.addEventListener('click', function (event) {
            if (isOpen() && !nav.contains(event.target) && !toggle.contains(event.target)) setOpen(false);
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && isOpen()) {
                setOpen(false);
                toggle.focus();
            }
        });
    });
})();

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
