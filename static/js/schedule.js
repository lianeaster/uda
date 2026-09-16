(function () {
    var dataEl = document.getElementById('schedule-entries-data');
    if (!dataEl) return;

    var entriesByDay = JSON.parse(dataEl.textContent);
    var modal = document.getElementById('day-modal');
    var modalTitle = document.getElementById('day-modal-title');
    var modalBookings = document.getElementById('day-modal-bookings');
    var modalClose = document.getElementById('day-modal-close');
    var addForm = document.getElementById('day-modal-form');
    var dateField = document.getElementById('id_date');
    var notesField = document.getElementById('id_notes');
    var startHourField = document.getElementById('id_start_hour');
    var endHourField = document.getElementById('id_end_hour');
    var subjectSelect = document.getElementById('id_group_subject');
    var submitBtn = document.getElementById('day-modal-submit');
    var cancelEditBtn = document.getElementById('day-modal-cancel-edit');
    var addUrl = addForm ? addForm.getAttribute('data-add-url') : null;
    var addLabel = submitBtn ? submitBtn.textContent.trim() : '';
    var editUrlTemplate = addForm ? addForm.getAttribute('data-edit-url-template') : null;

    // Дії над окремим записом — приховані форми, JS лише підставляє id.
    var actionForms = {
        remove: document.getElementById('delete-entry-form'),
        accept: document.getElementById('accept-entry-form'),
        reject: document.getElementById('reject-entry-form')
    };

    var monthNames = ['січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
        'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня'];

    function formatDate(iso) {
        var parts = iso.split('-');
        var day = parseInt(parts[2], 10);
        var month = parseInt(parts[1], 10) - 1;
        return day + ' ' + monthNames[month] + ' ' + parts[0];
    }

    function submitAction(name, entryId) {
        var form = actionForms[name];
        if (!form) return;
        form.action = form.getAttribute('data-url-template').replace('/0/', '/' + entryId + '/');
        form.hidden = false;
        form.submit();
    }

    function startEdit(entry) {
        if (!addForm || !editUrlTemplate) return;
        addForm.action = editUrlTemplate.replace('/0/', '/' + entry.id + '/');
        if (subjectSelect) {
            subjectSelect.value = entry.group_subject_id ? String(entry.group_subject_id) : '';
        }
        if (startHourField) startHourField.value = String(entry.start_hour);
        if (endHourField) endHourField.value = String(entry.end_hour);
        if (notesField) notesField.value = entry.notes || '';
        if (submitBtn) submitBtn.textContent = 'Зберегти зміни';
        if (cancelEditBtn) cancelEditBtn.hidden = false;
    }

    function resetToAddMode() {
        if (!addForm || !addUrl) return;
        addForm.action = addUrl;
        addForm.reset();
        if (submitBtn) submitBtn.textContent = addLabel;
        if (cancelEditBtn) cancelEditBtn.hidden = true;
    }

    function actionButton(label, className, onClick) {
        var button = document.createElement('button');
        button.type = 'button';
        button.className = className;
        button.textContent = label;
        button.addEventListener('click', onClick);
        return button;
    }

    function renderBookings(iso) {
        var entries = entriesByDay[iso] || [];
        modalBookings.innerHTML = '';
        if (entries.length === 0) {
            var empty = document.createElement('p');
            empty.className = 'muted';
            empty.textContent = 'На цей день ще немає записів.';
            modalBookings.appendChild(empty);
            return;
        }
        entries.forEach(function (entry) {
            var row = document.createElement('div');
            row.className = 'booking-row color-' + entry.color;

            var info = document.createElement('span');
            info.className = 'booking-info';
            var badge = entry.is_proposal
                ? ' <span class="status-badge">' + escapeHtml(entry.status_label) + '</span>'
                : '';
            info.innerHTML = '<strong>' + entry.start + '–' + entry.end + '</strong> ' +
                escapeHtml(entry.title) +
                (entry.initials ? ' <span class="entry-initials">' + escapeHtml(entry.initials) + '</span>' : '') +
                badge;
            if (entry.is_proposal) {
                info.title = 'Запропонував(ла): ' + entry.proposed_by;
            }
            row.appendChild(info);

            var actions = document.createElement('span');
            actions.className = 'booking-actions';

            if (entry.reviewable) {
                actions.appendChild(actionButton('Прийняти', 'link-button', function () {
                    submitAction('accept', entry.id);
                }));
                actions.appendChild(actionButton('Відхилити', 'link-button danger-link', function () {
                    if (confirm('Відхилити пропозицію?')) submitAction('reject', entry.id);
                }));
            }

            if (entry.editable && editUrlTemplate) {
                actions.appendChild(actionButton('Редагувати', 'link-button', function () {
                    startEdit(entry);
                }));
            }

            if (entry.deletable && actionForms.remove) {
                actions.appendChild(actionButton('Видалити', 'link-button danger-link', function () {
                    if (confirm('Видалити запис?')) submitAction('remove', entry.id);
                }));
            }

            row.appendChild(actions);
            modalBookings.appendChild(row);
        });
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function openModal(iso) {
        resetToAddMode();
        modalTitle.textContent = formatDate(iso);
        renderBookings(iso);
        if (dateField) dateField.value = iso;
        modal.hidden = false;
        document.body.classList.add('modal-open');
    }

    function closeModal() {
        modal.hidden = true;
        document.body.classList.remove('modal-open');
    }

    document.querySelectorAll('.day-cell[data-date]').forEach(function (cell) {
        cell.addEventListener('click', function () {
            openModal(cell.getAttribute('data-date'));
        });
        cell.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openModal(cell.getAttribute('data-date'));
            }
        });
    });

    if (modalClose) modalClose.addEventListener('click', closeModal);
    if (modal) {
        modal.addEventListener('click', function (event) {
            if (event.target === modal) closeModal();
        });
    }
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && modal && !modal.hidden) closeModal();
    });

    if (cancelEditBtn) cancelEditBtn.addEventListener('click', resetToAddMode);
})();
