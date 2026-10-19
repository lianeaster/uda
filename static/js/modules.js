/* Модулі програми на картці курсу: кожен згортається сам (<details>), а
   кнопки «Згорнути всі» / «Розгорнути всі» — усі разом. */
(function () {
    document.querySelectorAll('[data-modules-toggle]').forEach(function (button) {
        button.addEventListener('click', function () {
            var open = button.getAttribute('data-modules-toggle') === 'open';
            document.querySelectorAll('details.module-block').forEach(function (block) {
                block.open = open;
            });
        });
    });
})();
