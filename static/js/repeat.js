/* «+ ще один рядок» для форм платформи.

     <div data-repeat>
       <div data-repeat-rows> … рядки data-repeat-row … </div>
       <template data-repeat-template> порожній рядок </template>
       <button data-repeat-add>
     </div>

   Два різновиди рядків. Прості (випадний список з одним ім'ям на всіх) просто
   додаються й прибираються. Рядки формсету Django впізнаються за полем
   *-TOTAL_FORMS усередині: новий отримує наступний номер замість __prefix__,
   а прибраний ховається з позначкою DELETE — інакше збилися б номери решти.
   Кнопка «+» схована в розмітці й з'являється лише разом зі скриптом. */
(function () {
    function setUp(box) {
        var rows = box.querySelector('[data-repeat-rows]');
        var template = box.querySelector('[data-repeat-template]');
        var add = box.querySelector('[data-repeat-add]');
        var total = box.querySelector('input[name$="-TOTAL_FORMS"]');
        if (!rows || !template || !add) return;

        add.hidden = false;
        add.addEventListener('click', function () {
            var html = template.innerHTML;
            if (total) {
                html = html.replace(/__prefix__/g, total.value);
                total.value = parseInt(total.value, 10) + 1;
            }
            rows.insertAdjacentHTML('beforeend', html);
            var field = rows.lastElementChild.querySelector('select, input:not([type=hidden])');
            if (field) field.focus();
        });

        box.addEventListener('click', function (event) {
            var remove = event.target.closest('[data-repeat-remove]');
            if (!remove) return;
            var row = remove.closest('[data-repeat-row]');
            var drop = row.querySelector('input[name$="-DELETE"]');
            if (drop) {
                drop.checked = true;
                row.hidden = true;
            } else {
                row.remove();
            }
        });
    }

    document.querySelectorAll('[data-repeat]').forEach(setUp);
})();
