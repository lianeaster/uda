/* Сортування й фільтрація для кожної таблиці платформи.

   Розмітка керує поведінкою, скрипт один на всі:

     <table data-table>
       <th>ПІБ</th>                    звичайна колонка: сортується, фільтрується
       <th data-sort="false">          не сортувати (колонка дій)
       <th data-filter="none">         не фільтрувати
       <th data-filter="period">       фільтр «з … по …»; комірки несуть
       <td data-start="2026-03-05"     межі періоду (кінця може не бути —
           data-end="">                тоді період ще триває)
       <td data-sort="2026-03-05">     чим сортувати, якщо текст для цього не годиться
                                       (дати, ролі за старшинством, періоди)

   Тип фільтра обирається сам: мало різних значень — випадний список, багато —
   поле для пошуку. Таблиці тут не посторінкові, тож клієнт бачить усі рядки;
   якщо якась колись виросте, їй знадобиться посторінковість, а разом із нею й
   фільтрація на сервері. */
(function () {
    var SELECT_LIMIT = 12;

    var NUMBER = /^-?\d+(?:[.,]\d+)?$/;

    /* Текст комірки з шаблону приходить із переносами й відступами розмітки.
       Без згортання пробілів у випадному фільтрі опинилося б
       «МД-1\n        викладаю», а сортування порівнювало б ці ж пробіли. */
    function text(node) {
        return (node && node.textContent || '').replace(/\s+/g, ' ').trim();
    }

    function cellValue(cell) {
        if (!cell) return '';
        var explicit = cell.getAttribute('data-sort');
        return explicit !== null ? explicit.trim() : text(cell);
    }

    function compare(a, b) {
        // Тільки справжнє число, інакше «2026-03-05» прочиталося б як 2026
        // і всі дати одного року стали б рівними.
        if (NUMBER.test(a) && NUMBER.test(b)) {
            return parseFloat(a.replace(',', '.')) - parseFloat(b.replace(',', '.'));
        }
        return a.localeCompare(b, 'uk');
    }

    function setUp(table) {
        var head = table.tHead;
        var body = table.tBodies[0];
        if (!head || !body) return;

        var headers = Array.prototype.slice.call(head.rows[0].cells);
        var dataRows = Array.prototype.slice.call(body.rows).filter(function (row) {
            // Рядок-заглушка «ще немає записів» не бере участі ні в чому.
            return !row.hasAttribute('data-empty') && row.cells.length === headers.length;
        });
        if (dataRows.length === 0) return;

        var emptyRow = buildEmptyRow(headers.length);
        body.appendChild(emptyRow);

        var filters = buildFilterRow(table, head, headers, dataRows, applyFilters);
        headers.forEach(function (th, index) {
            if (th.getAttribute('data-sort') === 'false' || !th.textContent.trim()) return;
            th.classList.add('is-sortable');
            th.tabIndex = 0;
            th.setAttribute('role', 'button');
            th.addEventListener('click', function () { sortBy(index, th); });
            th.addEventListener('keydown', function (event) {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    sortBy(index, th);
                }
            });
        });

        function sortBy(index, th) {
            var ascending = th.getAttribute('aria-sort') !== 'ascending';
            headers.forEach(function (other) {
                other.removeAttribute('aria-sort');
                other.classList.remove('is-sorted');
            });
            th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
            th.classList.add('is-sorted');

            dataRows.sort(function (rowA, rowB) {
                var result = compare(cellValue(rowA.cells[index]), cellValue(rowB.cells[index]));
                return ascending ? result : -result;
            });
            dataRows.forEach(function (row) { body.insertBefore(row, emptyRow); });
        }

        function applyFilters() {
            var visible = 0;
            dataRows.forEach(function (row) {
                var matches = filters.every(function (filter) {
                    return filter.matches(row);
                });
                row.hidden = !matches;
                if (matches) visible += 1;
            });
            emptyRow.hidden = visible > 0;
        }
    }

    function buildEmptyRow(columnCount) {
        var row = document.createElement('tr');
        row.setAttribute('data-empty', '');
        var cell = document.createElement('td');
        cell.colSpan = columnCount;
        cell.className = 'muted';
        cell.textContent = 'Нічого не знайдено за цим фільтром.';
        row.appendChild(cell);
        row.hidden = true;
        return row;
    }

    function buildFilterRow(table, head, headers, dataRows, onChange) {
        var row = head.insertRow(-1);
        row.className = 'filter-row';
        var filters = [];

        headers.forEach(function (th, index) {
            var cell = row.insertCell(-1);
            var kind = th.getAttribute('data-filter');
            if (kind === 'none' || !th.textContent.trim()) return;

            if (kind === 'period') {
                var period = periodControl(th.textContent.trim());
                cell.appendChild(period.element);
                period.element.addEventListener('input', onChange);
                filters.push({
                    matches: function (dataRow) { return period.matches(dataRow.cells[index]); }
                });
                return;
            }

            var values = dataRows.map(function (dataRow) {
                return text(dataRow.cells[index]);
            });
            var distinct = values.filter(function (value, position) {
                return value !== '' && values.indexOf(value) === position;
            }).sort(function (a, b) { return a.localeCompare(b, 'uk'); });

            var control = distinct.length && distinct.length <= SELECT_LIMIT
                ? selectControl(distinct, th.textContent.trim())
                : textControl(th.textContent.trim());
            cell.appendChild(control.element);
            control.element.addEventListener(control.event, onChange);
            filters.push({
                matches: function (dataRow) {
                    return control.matches(text(dataRow.cells[index]));
                }
            });
        });
        return filters;
    }

    function selectControl(values, label) {
        var select = document.createElement('select');
        select.setAttribute('aria-label', label);
        select.appendChild(new Option('усі', ''));
        values.forEach(function (value) { select.appendChild(new Option(value, value)); });
        return {
            element: select,
            event: 'change',
            matches: function (text) { return !select.value || text === select.value; }
        };
    }

    function textControl(label) {
        var input = document.createElement('input');
        input.type = 'search';
        input.placeholder = 'пошук';
        input.setAttribute('aria-label', label);
        return {
            element: input,
            event: 'input',
            matches: function (text) {
                var needle = input.value.trim().toLowerCase();
                return !needle || text.toLowerCase().indexOf(needle) !== -1;
            }
        };
    }

    /* Період рядка підходить, якщо перетинається з обраним: «з» — ще не
       закінчився до цієї дати, «по» — уже почався до неї. Обидві межі разом —
       тривав хоч день у цьому проміжку. ISO-дати порівнюються як рядки. */
    function periodControl(label) {
        var box = document.createElement('div');
        box.className = 'period-filter';
        var from = dateInput('з', label + ': з');
        var to = dateInput('по', label + ': по');
        box.appendChild(from.label);
        box.appendChild(to.label);
        return {
            element: box,
            matches: function (cell) {
                var start = cell.getAttribute('data-start') || '';
                var end = cell.getAttribute('data-end') || '';
                if (from.input.value && end && end < from.input.value) return false;
                if (to.input.value && start && start > to.input.value) return false;
                return true;
            }
        };
    }

    function dateInput(caption, label) {
        var wrap = document.createElement('label');
        var input = document.createElement('input');
        input.type = 'date';
        input.setAttribute('aria-label', label);
        var text = document.createElement('span');
        text.textContent = caption;
        wrap.appendChild(text);
        wrap.appendChild(input);
        return { label: wrap, input: input };
    }

    document.querySelectorAll('table[data-table]').forEach(setUp);
})();
