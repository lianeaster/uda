import calendar
import datetime as dt

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from accounts.mixins import UserManagementRequiredMixin
from accounts.models import User

from .forms import CourseForm, GroupSubjectForm, ScheduleEntryForm, SubjectForm
from .models import Course, Enrollment, Group, GroupSubject, ScheduleEntry, Subject
from .services import build_month_grid, can_modify, can_review

UK_MONTHS = [
    '', 'Січень', 'Лютий', 'Березень', 'Квітень', 'Травень', 'Червень',
    'Липень', 'Серпень', 'Вересень', 'Жовтень', 'Листопад', 'Грудень',
]
UK_WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']


def _parse_month(request):
    raw = request.GET.get('month')
    if raw:
        try:
            return dt.date.fromisoformat(raw).replace(day=1)
        except ValueError:
            pass
    return dt.date.today().replace(day=1)


def _shift_month(anchor, delta):
    year = anchor.year + (anchor.month - 1 + delta) // 12
    month = (anchor.month - 1 + delta) % 12 + 1
    return dt.date(year, month, 1)


class OwnScopeMixin(LoginRequiredMixin):
    """Who a page is allowed to show, and whose side it opens on.

    Access is the widest role: a manager or super-admin may see everything,
    everyone else only their own. But roles are a set, so the same person can
    manage *and* teach — for them the page opens on the full picture (managing
    is the day job) with a «Мої» switch to narrow it down to where they teach.
    """

    def manages_and_teaches(self):
        user = self.request.user
        return user.can_manage_users and user.is_teacher

    def showing_own(self):
        if not self.request.user.can_manage_users:
            return True
        return self.manages_and_teaches() and self.request.GET.get('who') == 'mine'

    def own_scope_context(self):
        return {
            'showing_own': self.showing_own(),
            'can_switch_who': self.manages_and_teaches(),
            'who': 'mine' if self.showing_own() else 'all',
        }


class GroupScopedMixin(OwnScopeMixin):
    """The same queryset backs both the list and the detail page, so a teacher
    cannot reach another group by guessing its URL."""

    def scoped_groups(self):
        groups = Group.objects.select_related('course')
        if not self.showing_own():
            return groups
        # Не «викладач АБО студент», а обидва разом — ролі додаються.
        return groups.for_person(self.request.user)


class ScheduleView(GroupScopedMixin, View):
    """A group's month. The group is the axis, because that is what management
    books: a group is exactly one course running between two dates."""

    template_name = 'schedule/schedule.html'

    def get(self, request):
        user = request.user
        anchor = _parse_month(request)
        groups = self.scoped_groups().order_by('-start_date', 'name')

        requested = request.GET.get('group')
        viewed_group = None
        if requested:
            viewed_group = groups.filter(pk=requested).first()
        if viewed_group is None:
            viewed_group = groups.first()

        has_view = viewed_group is not None
        weeks, entries_json, form = [], {}, None
        can_add = False

        if has_view:
            can_add = user.can_manage_users or (
                user.is_teacher
                and viewed_group.group_subjects.filter(teacher=user).exists()
            )
            entries = viewed_group.schedule_entries.select_related(
                'group__course', 'group_subject__subject',
                'group_subject__teacher', 'created_by',
            )
            weeks = build_month_grid(entries, anchor, user)
            for week in weeks:
                for day in week:
                    if day['in_month'] and day['entries']:
                        entries_json[day['date'].isoformat()] = [
                            self._entry_payload(entry) for entry in day['entries']
                        ]
            if can_add:
                form = ScheduleEntryForm(actor=user, group=viewed_group)

        return render(request, self.template_name, {
            'weeks': weeks,
            'entries_json': entries_json,
            'anchor': anchor,
            'month_label': f'{UK_MONTHS[anchor.month]} {anchor.year}',
            'weekday_labels': UK_WEEKDAYS,
            'prev_month': _shift_month(anchor, -1),
            'next_month': _shift_month(anchor, 1),
            'groups': groups,
            'viewed_group': viewed_group,
            'group_param': str(viewed_group.pk) if has_view else '',
            'has_view': has_view,
            'can_add': can_add,
            'proposing': can_add and user.teaches_only,
            'form': form,
        })

    @staticmethod
    def _entry_payload(entry):
        teacher = entry.teacher
        return {
            'id': entry.pk,
            'start': entry.start_time.strftime('%H:%M'),
            'end': entry.end_time.strftime('%H:%M'),
            'start_hour': entry.start_time.hour,
            'end_hour': entry.end_time.hour,
            'color': entry.color,
            'title': entry.title,
            'initials': teacher.initials if teacher else '',
            'teacher': teacher.get_full_name() if teacher else '',
            'deletable': entry.deletable,
            'editable': entry.editable,
            'reviewable': entry.reviewable,
            'status': entry.status,
            'status_label': entry.get_status_display(),
            'is_proposal': entry.is_proposal,
            'proposed_by': entry.created_by.get_full_name() or entry.created_by.username,
            'group_subject_id': entry.group_subject_id,
            'notes': entry.notes,
        }


def _back_to_schedule(request, group_id):
    params = {'group': group_id, 'month': request.POST.get('month')}
    query = '&'.join(f'{k}={v}' for k, v in params.items() if v)
    base_url = reverse('schedule:home')
    return redirect(f'{base_url}?{query}' if query else base_url)


class ScheduleEntryCreateView(GroupScopedMixin, View):
    def post(self, request):
        user = request.user
        group = self.scoped_groups().filter(pk=request.POST.get('group')).first()

        if group is None:
            messages.error(request, 'Групу не знайдено або вона вам недоступна.')
            return redirect('schedule:home')
        may_add = user.can_manage_users or (
            user.is_teacher and group.group_subjects.filter(teacher=user).exists()
        )
        if not may_add:
            messages.error(request, 'У вас немає прав додавати записи до цього розкладу.')
            return _back_to_schedule(request, group.pk)

        form = ScheduleEntryForm(request.POST, actor=user, group=group)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Пропозицію надіслано на розгляд.' if user.teaches_only
                else 'Запис додано до розкладу.',
            )
        else:
            error_text = ' '.join(f'{errors[0]}' for errors in form.errors.values())
            messages.error(request, f'Не вдалося зберегти запис: {error_text or "Перевірте поля форми."}')
        return _back_to_schedule(request, group.pk)


class ScheduleEntryUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = ScheduleEntry.objects.filter(pk=pk).select_related('group').first()
        if entry is None:
            messages.info(request, 'Цей запис уже видалено.')
            return redirect('schedule:home')

        if not can_modify(entry, request.user):
            messages.error(request, 'У вас немає прав редагувати цей запис.')
        else:
            form = ScheduleEntryForm(request.POST, actor=request.user, instance=entry)
            if form.is_valid():
                form.save()
                messages.success(request, 'Запис оновлено.')
            else:
                error_text = ' '.join(f'{errors[0]}' for errors in form.errors.values())
                messages.error(request, f'Не вдалося зберегти зміни: {error_text or "Перевірте поля форми."}')
        return _back_to_schedule(request, entry.group_id)


class ScheduleEntryDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = ScheduleEntry.objects.filter(pk=pk).first()
        if entry is None:
            messages.info(request, 'Цей запис уже видалено.')
            return redirect('schedule:home')

        group_id = entry.group_id
        if not can_modify(entry, request.user):
            messages.error(request, 'У вас немає прав видалити цей запис.')
        else:
            entry.delete()
            messages.success(request, 'Запис видалено з розкладу.')
        return _back_to_schedule(request, group_id)


class ScheduleEntryReviewView(LoginRequiredMixin, View):
    """Management accepts or rejects a teacher's proposal — once.

    An accepted proposal becomes part of the schedule and is drawn like any
    other booking; `source` still records that a teacher suggested it.
    """

    decision = None

    def post(self, request, pk):
        entry = ScheduleEntry.objects.filter(pk=pk).select_related('group').first()
        if entry is None:
            messages.info(request, 'Цієї пропозиції вже немає.')
            return redirect('schedule:home')

        if not can_review(entry, request.user):
            messages.error(request, 'Цю пропозицію не можна розглянути.')
        else:
            entry.status = self.decision
            entry.reviewed_by = request.user
            entry.reviewed_at = timezone.now()
            entry.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            messages.success(
                request,
                'Пропозицію прийнято — слот у розкладі.'
                if self.decision == ScheduleEntry.Status.ACCEPTED
                else 'Пропозицію відхилено.',
            )
        return _back_to_schedule(request, entry.group_id)


class CourseListView(LoginRequiredMixin, ListView):
    """Read-only for everyone; only managers get the add/delete controls."""

    model = Course
    template_name = 'schedule/course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.prefetch_related('subjects')


class CourseCreateView(UserManagementRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'schedule/course_form.html'

    def get_success_url(self):
        messages.success(self.request, f'Курс «{self.object.name}» додано.')
        return reverse('schedule:course_list')


class CourseDeleteView(UserManagementRequiredMixin, View):
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        course.delete()
        messages.success(request, f'Курс «{course.name}» видалено.')
        return redirect('schedule:course_list')


class SubjectListView(LoginRequiredMixin, ListView):
    """Read-only for everyone; only managers get the add/delete controls.

    A teacher lands on their own subjects («Мої предмети») and can switch to
    the full catalogue — everybody sees every subject, the scope is only a
    filter, not a permission.
    """

    model = Subject
    template_name = 'schedule/subject_list.html'
    context_object_name = 'subjects'

    def all_subjects(self):
        return Subject.objects.select_related('course').prefetch_related('teachers')

    def get_queryset(self):
        subjects = self.all_subjects()
        if self.request.user.is_teacher and self.scope() == 'mine':
            subjects = subjects.filter(teachers=self.request.user)
        return subjects

    def scope(self):
        """Викладач відкриває свої предмети; той, хто ще й керує, — увесь каталог."""
        requested = self.request.GET.get('scope')
        if requested in ('mine', 'all'):
            return requested
        return 'all' if self.request.user.can_manage_users else 'mine'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['is_teacher'] = user.is_teacher
        if user.is_teacher:
            context['scope'] = self.scope()
            context['mine_count'] = self.all_subjects().filter(teachers=user).count()
            context['total_count'] = self.all_subjects().count()
        return context


class SubjectCreateView(UserManagementRequiredMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'schedule/subject_form.html'

    def get_success_url(self):
        messages.success(self.request, f'Предмет «{self.object.name}» додано.')
        return reverse('schedule:subject_list')


class SubjectDeleteView(UserManagementRequiredMixin, View):
    def post(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk)
        subject.delete()
        messages.success(request, f'Предмет «{subject.name}» видалено.')
        return redirect('schedule:subject_list')


class ProposalListView(LoginRequiredMixin, ListView):
    """Доля пропозицій: що чекає на розгляд і що вже вирішено.

    Викладач бачить свої, менеджмент — усі. Відкривши сторінку, автор дізнався
    про рішення, тож саме тут вони позначаються переглянутими — і зникають із
    лічильника новин у кабінеті.
    """

    template_name = 'schedule/proposal_list.html'
    context_object_name = 'proposals'

    def scoped(self):
        proposals = ScheduleEntry.objects.proposals().select_related(
            'group__course', 'group_subject__subject', 'created_by', 'reviewed_by')
        if self.request.user.can_manage_users:
            return proposals
        return proposals.by_author(self.request.user)

    def get_queryset(self):
        return self.scoped().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Вибірку форсуємо до позначення: інакше рядки прочитались би вже
        # переглянутими й підсвітка «нове» не показалася б жодного разу.
        proposals = list(context['proposals'])
        context['proposals'] = proposals
        self._mark_own_decisions_seen(proposals)

        mine = self.scoped().by_author(self.request.user)
        context['own_pending'] = mine.awaiting_review().count()
        context['reviewing'] = self.request.user.can_manage_users
        context['pending_total'] = self.scoped().awaiting_review().count()
        return context

    def _mark_own_decisions_seen(self, proposals):
        user = self.request.user
        fresh = [p.pk for p in proposals
                 if p.created_by_id == user.pk and p.decision_is_news]
        if fresh:
            ScheduleEntry.objects.filter(pk__in=fresh).update(
                author_seen_at=timezone.now())


class GroupListView(GroupScopedMixin, ListView):
    template_name = 'schedule/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        groups = self.scoped_groups().annotate_my_part(self.request.user).annotate(
            subject_count=Count('group_subjects', distinct=True),
            teacher_count=Count('group_subjects__teacher', distinct=True),
            student_count=Count('enrollments', distinct=True),
        )
        if self.request.GET.get('scope') != 'all':
            groups = groups.active()
        return groups

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scope = 'all' if self.request.GET.get('scope') == 'all' else 'active'
        context['scope'] = scope
        context['total_count'] = self.scoped_groups().count()
        context['active_count'] = self.scoped_groups().active().count()
        context['own_only'] = self.showing_own()
        context.update(self.own_scope_context())
        return context


class GroupDetailView(GroupScopedMixin, DetailView):
    template_name = 'schedule/group_detail.html'
    context_object_name = 'group'

    def get_queryset(self):
        return self.scoped_groups().annotate_my_part(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object
        context['group_subjects'] = (
            group.group_subjects.select_related('subject', 'teacher').all()
        )
        context['enrollments'] = group.enrollments.select_related('student').all()
        if self.request.user.can_manage_users:
            context['subject_form'] = GroupSubjectForm(group=group)
            context['fillable'] = len(_fillable_subjects(group)[0])
        return context


def _fillable_subjects(group):
    """Предмети курсу, які можна додати в групу гуртом, і ті, що не можна.

    Гуртом береться лише однозначне: предмет, у якого в каталозі рівно один
    викладач. Де викладачів нема або кілька — вибір за людиною, тож такі
    предмети повертаються окремо, щоб про них сказати, а не тихо пропустити.
    """
    taken = set(group.group_subjects.values_list('subject_id', flat=True))
    ready, ambiguous = [], []
    subjects = group.course.subjects.exclude(pk__in=taken).prefetch_related('teachers')
    for subject in subjects:
        teachers = list(subject.teachers.all())
        if len(teachers) == 1:
            ready.append((subject, teachers[0]))
        else:
            ambiguous.append(subject)
    return ready, ambiguous


class GroupSubjectCreateView(UserManagementRequiredMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        form = GroupSubjectForm(request.POST, group=group)
        if form.is_valid():
            link = form.save()
            messages.success(request, f'Предмет «{link.subject.name}» додано до групи.')
        else:
            error_text = ' '.join(f'{errors[0]}' for errors in form.errors.values())
            messages.error(request, f'Не вдалося додати предмет: {error_text or "Перевірте поля форми."}')
        return redirect('schedule:group_detail', pk=group.pk)


class GroupSubjectDeleteView(UserManagementRequiredMixin, View):
    def post(self, request, pk):
        link = get_object_or_404(GroupSubject, pk=pk)
        group_id, name = link.group_id, link.subject.name
        link.delete()
        messages.success(request, f'Предмет «{name}» прибрано з групи.')
        return redirect('schedule:group_detail', pk=group_id)


class GroupSubjectsFillView(UserManagementRequiredMixin, View):
    """Переносить у групу всі предмети курсу, де викладач однозначний.

    Програма курсу вже містить 40+ предметів із закріпленими викладачами —
    додавати їх по одному в кожну нову групу було б непрактично.
    """

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        ready, ambiguous = _fillable_subjects(group)

        GroupSubject.objects.bulk_create([
            GroupSubject(group=group, subject=subject, teacher=teacher,
                         start_date=group.start_date, end_date=group.end_date)
            for subject, teacher in ready
        ])

        if ready:
            messages.success(request, f'Додано предметів: {len(ready)}.')
        else:
            messages.info(request, 'Нема чого додавати — усі предмети курсу вже в групі.')
        if ambiguous:
            names = ', '.join(s.label for s in ambiguous[:5])
            tail = f' та ще {len(ambiguous) - 5}' if len(ambiguous) > 5 else ''
            messages.warning(
                request,
                f'Не додано {len(ambiguous)} — викладач не один або не призначений: {names}{tail}. '
                f'Їх додайте вручну.',
            )
        return redirect('schedule:group_detail', pk=group.pk)


class StudentListView(OwnScopeMixin, ListView):
    """Students seen through enrollments, so every row carries its dates.

    A teacher only ever sees the students of the groups they teach in — the
    roster is derived from their own `GroupSubject` rows, never from the
    student accounts directly.
    """

    template_name = 'schedule/student_list.html'
    context_object_name = 'enrollments'

    def get_queryset(self):
        user = self.request.user
        enrollments = Enrollment.objects.select_related('student', 'group', 'group__course')
        if self.showing_own():
            if not user.is_teacher:
                return enrollments.none()
            enrollments = enrollments.for_teacher(user)
        if self.request.GET.get('scope') != 'all':
            enrollments = enrollments.active()
        return enrollments.order_by('student__last_name', 'student__first_name', 'group__name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['scope'] = 'all' if self.request.GET.get('scope') == 'all' else 'active'
        context['student_count'] = self.get_queryset().values('student_id').distinct().count()
        context['own_only'] = self.showing_own()
        context.update(self.own_scope_context())
        return context
