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
    var teacherField = document.getElementById('id_teacher');
    var startHourField = document.getElementById('id_start_hour');
    var endHourField = document.getElementById('id_end_hour');
    var courseSelect = document.getElementById('id_course');
    var subjectSelect = document.getElementById('id_subject');
    var submitBtn = document.getElementById('day-modal-submit');
    var cancelEditBtn = document.getElementById('day-modal-cancel-edit');
    var addUrl = addForm ? addForm.getAttribute('data-add-url') : null;
    var editUrlTemplate = addForm ? addForm.getAttribute('data-edit-url-template') : null;
    var deleteForm = document.getElementById('delete-entry-form');
    var deleteUrlTemplate = deleteForm ? deleteForm.getAttribute('data-url-template') : null;

    var monthNames = ['січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
        'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня'];

    function formatDate(iso) {
        var parts = iso.split('-');
        var day = parseInt(parts[2], 10);
        var month = parseInt(parts[1], 10) - 1;
        return day + ' ' + monthNames[month] + ' ' + parts[0];
    }

    function filterSubjectsByCourse() {
        if (!courseSelect || !subjectSelect) return;
        var courseId = courseSelect.value;
        Array.prototype.forEach.call(subjectSelect.options, function (opt) {
            if (!opt.value) return;
            opt.hidden = !!courseId && opt.getAttribute('data-course') !== courseId;
        });
    }

    function startEdit(entry) {
        if (!addForm || !editUrlTemplate) return;
        addForm.action = editUrlTemplate.replace('/0/', '/' + entry.id + '/');
        if (courseSelect) {
            courseSelect.value = entry.course_id ? String(entry.course_id) : '';
            filterSubjectsByCourse();
        }
        if (subjectSelect) subjectSelect.value = entry.subject_id ? String(entry.subject_id) : '';
        if (teacherField) teacherField.value = entry.teacher_id ? String(entry.teacher_id) : '';
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
        filterSubjectsByCourse();
        if (submitBtn) submitBtn.textContent = 'Забронювати час';
        if (cancelEditBtn) cancelEditBtn.hidden = true;
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
            info.innerHTML = '<strong>' + entry.start + '–' + entry.end + '</strong> ' +
                escapeHtml(entry.title) +
                (entry.initials ? ' <span class="entry-initials">' + escapeHtml(entry.initials) + '</span>' : '') +
                (entry.conflict ? ' <span class="conflict-badge">перетин</span>' : '');
            row.appendChild(info);

            var actions = document.createElement('span');
            actions.className = 'booking-actions';

            if (entry.editable && editUrlTemplate) {
                var edit = document.createElement('button');
                edit.type = 'button';
                edit.className = 'link-button';
                edit.textContent = 'Редагувати';
                edit.addEventListener('click', function () {
                    startEdit(entry);
                });
                actions.appendChild(edit);
            }

            if (entry.deletable && deleteUrlTemplate) {
                var del = document.createElement('button');
                del.type = 'button';
                del.className = 'link-button danger-link';
                del.textContent = 'Видалити';
                del.addEventListener('click', function () {
                    if (!confirm('Видалити запис?')) return;
                    deleteForm.action = deleteUrlTemplate.replace('/0/', '/' + entry.id + '/');
                    deleteForm.hidden = false;
                    deleteForm.submit();
                });
                actions.appendChild(del);
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
    if (courseSelect && subjectSelect) {
        courseSelect.addEventListener('change', function () {
            filterSubjectsByCourse();
            var selected = subjectSelect.options[subjectSelect.selectedIndex];
            if (selected && selected.hidden) subjectSelect.value = '';
        });
    }
})();
