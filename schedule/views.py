import calendar
import datetime as dt
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, OuterRef, ProtectedError, Q, Subquery, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import UserManagementRequiredMixin
from accounts.models import User

from .forms import (
    CourseForm,
    EnrollmentForm,
    GroupForm,
    GroupSubjectForm,
    ModuleForm,
    NewStudentForm,
    ScheduleEntryForm,
    StudentInfoForm,
    SubjectForm,
    course_subject_formset,
)
from .models import (
    Course,
    CourseSubject,
    Enrollment,
    Group,
    GroupSubject,
    Module,
    ScheduleEntry,
    Subject,
)
from . import exchange, pricing
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
    """Read-only for everyone; only managers get the add/edit/delete controls."""

    model = Course
    template_name = 'schedule/course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        # Години — підзапитом: Sum поруч із Count по групах помножився б на їх кількість.
        hours = CourseSubject.objects.filter(course=OuterRef('pk')).values('course').annotate(
            total=Sum('hours')).values('total')
        return Course.objects.annotate(
            subject_count=Count('program', distinct=True),
            group_count=Count('groups', distinct=True),
            hours=Subquery(hours),
        )


def _commissions():
    """Відсотки комісії для підписів у таблицях вартості."""
    return {'base_commission': pricing.BASE_COMMISSION,
            'individual_commission': pricing.INDIVIDUAL_COMMISSION}


def _program_rows(links, with_money):
    """Рядки програми з вартістю (лише для тих, хто бачить гроші) і підсумок.

    Без грошей вартість навіть не рахується — у шаблон вона не потрапить.
    """
    links = list(links)
    hours = sum((link.hours for link in links if link.hours is not None), Decimal(0))
    if not with_money:
        return [(link, None) for link in links], hours, None
    rows, total = pricing.program_cost(links)
    return rows, hours, total


def _program_sections(course, with_money):
    """Програма курсу по модулях: [(модуль, рядки, годин, вартість)].

    Модулі — у своєму порядку, навіть порожні (щойно створений модуль має
    де бути видно). Предмет без модуля в програмі бути не повинен: форма
    цього не пропускає, а старі такі рядки перенесла міграція 0017. Якщо
    все ж трапиться — окремий розділ наприкінці, щоб рядок не зник з очей.
    """
    links = list(course.ordered_program)
    sections = []
    for module in course.modules.all():
        mine = [link for link in links if link.module_id == module.pk]
        sections.append((module, *_program_rows(mine, with_money)))
    loose = [link for link in links if link.module_id is None]
    if loose:
        sections.append((None, *_program_rows(loose, with_money)))
    return sections


class CourseDetailView(LoginRequiredMixin, DetailView):
    """Картка курсу: опис, програма по модулях з годинами й групи, що його проходять.

    Каталог курсів відкритий усім ролям, тож і картка теж. Групи — лише ті,
    що людині видно й на сторінці груп. Вартість — лише менеджеру й супер-адміну.
    """

    model = Course
    template_name = 'schedule/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        with_money = user.can_manage_users
        groups = self.object.groups.annotate(student_count=Count('enrollments', distinct=True))
        if not with_money:
            groups = groups.filter(pk__in=Group.objects.for_person(user))
        sections = _program_sections(self.object, with_money)
        context['sections'] = sections
        context['subject_count'] = sum(len(rows) for _, rows, _, _ in sections)
        context['hours'] = sum((hours for _, _, hours, _ in sections), Decimal(0))
        if with_money:
            total = sum((total for _, _, _, total in sections), pricing.Cost())
            euro = exchange.today_rate()
            context.update(
                total=total, euro=euro, **_commissions(),
                euro_is_today=bool(euro) and euro.date == timezone.localdate(),
                offers=pricing.course_offers(self.object, total, euro and euro.rate),
            )
        context['groups'] = groups
        return context


class CourseCreateView(UserManagementRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'schedule/course_form.html'

    def get_success_url(self):
        messages.success(self.request, f'Курс «{self.object.name}» додано.')
        return reverse('schedule:course_detail', args=[self.object.pk])


class CourseUpdateView(UserManagementRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'schedule/course_form.html'

    def get_success_url(self):
        messages.success(self.request, f'Курс «{self.object.name}» збережено.')
        return reverse('schedule:course_detail', args=[self.object.pk])


class CourseDeleteView(UserManagementRequiredMixin, View):
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        try:
            course.delete()
        except ProtectedError:
            messages.error(
                request,
                f'Курс «{course.name}» не можна видалити: за ним навчаються групи. '
                f'Спершу видаліть групи або переведіть їх на інший курс.',
            )
            return redirect('schedule:course_detail', pk=course.pk)
        messages.success(request, f'Курс «{course.name}» видалено. Його предмети лишилися в каталозі.')
        return redirect('schedule:course_list')


class ModuleDetailView(LoginRequiredMixin, DetailView):
    """Картка модуля: предмети з годинами; вартість — лише менеджеру й супер-адміну."""

    model = Module
    template_name = 'schedule/module_detail.html'
    context_object_name = 'module'

    def get_queryset(self):
        return Module.objects.select_related('course')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with_money = self.request.user.can_manage_users
        rows, hours, total = _program_rows(self.object.ordered_program, with_money)
        context.update(rows=rows, hours=hours, total=total)
        if with_money:
            context.update(_commissions())
            context['euro'] = exchange.today_rate()
        return context


class ModuleCreateView(UserManagementRequiredMixin, CreateView):
    model = Module
    form_class = ModuleForm
    template_name = 'schedule/module_form.html'

    def get_initial(self):
        return {'course': self.request.GET.get('course')}

    def get_success_url(self):
        messages.success(self.request, f'Модуль «{self.object.label}» додано.')
        return reverse('schedule:module_detail', args=[self.object.pk])


class ModuleUpdateView(UserManagementRequiredMixin, UpdateView):
    model = Module
    form_class = ModuleForm
    template_name = 'schedule/module_form.html'

    def get_success_url(self):
        messages.success(self.request, f'Модуль «{self.object.label}» збережено.')
        return reverse('schedule:module_detail', args=[self.object.pk])


class ModuleDeleteView(UserManagementRequiredMixin, View):
    def post(self, request, pk):
        module = get_object_or_404(Module, pk=pk)
        course, count = module.course, module.program.count()
        module.delete()
        messages.success(
            request,
            f'Модуль «{module.label}» видалено' + (
                f' разом із предметами програми ({count}). У каталозі предметів вони лишилися.'
                if count else '.'))
        return redirect('schedule:course_detail', pk=course.pk)


class SubjectListView(LoginRequiredMixin, ListView):
    """Read-only for everyone; only managers get the add/edit/delete controls.

    A teacher lands on their own subjects («Мої предмети») and can switch to
    the full catalogue — everybody sees every subject, the scope is only a
    filter, not a permission.
    """

    model = Subject
    template_name = 'schedule/subject_list.html'
    context_object_name = 'subjects'

    def all_subjects(self):
        return Subject.objects.prefetch_related('teachers', 'course_links__course')

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


class SubjectDetailView(LoginRequiredMixin, DetailView):
    """Картка предмета: хто може вести, у яких курсах і модулях, скільки годин.

    Ставки викладачів, вартість і групи — лише менеджеру й супер-адміну.
    """

    model = Subject
    template_name = 'schedule/subject_detail.html'
    context_object_name = 'subject'

    def get_queryset(self):
        return Subject.objects.prefetch_related('teachers')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with_money = self.request.user.can_manage_users
        links = self.object.course_links.select_related('course', 'module').prefetch_related(
            'teachers', 'subject__teachers')
        context['rows'], context['hours'], _ = _program_rows(links, with_money)
        if with_money:
            context['rate'] = pricing.subject_rate(self.object)
            context['teacher_rates'] = [
                (t, pricing.teacher_rate(t)) for t in self.object.teachers.all()]
            context.update(_commissions())
            context['taught_in'] = self.object.group_subjects.select_related(
                'group__course', 'teacher').order_by('-start_date')
        return context


class SubjectFormView(UserManagementRequiredMixin, View):
    """Додавання й редагування предмета: сам предмет, його викладачі й
    рядки «курс + номер у програмі» — одним збереженням."""

    template_name = 'schedule/subject_form.html'

    def get_subject(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Subject, pk=pk) if pk else None

    def get(self, request, pk=None):
        subject = self.get_subject()
        # Предмет додають у модуль — з картки модуля приходить ?module=.
        module = Module.objects.filter(pk=request.GET.get('module') or None).first()
        courses = course_subject_formset(subject, module=module)
        return self.render(SubjectForm(instance=subject), courses, subject)

    def post(self, request, pk=None):
        subject = self.get_subject()
        form = SubjectForm(request.POST, instance=subject)
        courses = course_subject_formset(subject or Subject(), request.POST)
        if form.is_valid() and courses.is_valid():
            with transaction.atomic():
                saved = form.save()
                courses.instance = saved
                courses.save()
            messages.success(
                request,
                f'Предмет «{saved.name}» {"збережено" if subject else "додано"}.',
            )
            return redirect('schedule:subject_list')
        return self.render(form, courses, subject)

    def render(self, form, courses, subject):
        context = {'form': form, 'courses': courses, 'object': subject}
        if subject is not None:
            # Хто реально веде предмет — у групах; там викладачі й різняться.
            context['taught_in'] = subject.group_subjects.select_related(
                'group__course', 'teacher').order_by('-start_date')
        return render(self.request, self.template_name, context)


class SubjectDeleteView(UserManagementRequiredMixin, View):
    def post(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk)
        try:
            subject.delete()
        except ProtectedError:
            messages.error(
                request,
                f'Предмет «{subject.name}» не можна видалити: його вже викладають у групах. '
                f'Спершу приберіть його з груп.',
            )
            return redirect('schedule:subject_list')
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
        # Номер і місце предмета — з програми курсу цієї групи: в іншому
        # курсі той самий предмет може стояти під іншим номером.
        program = CourseSubject.objects.filter(
            course_id=group.course_id, subject_id=OuterRef('subject_id'))
        context['group_subjects'] = (
            group.group_subjects.select_related('subject', 'teacher').annotate(
                code=Subquery(program.values('code')[:1]),
                position=Subquery(program.values('position')[:1]),
            ).order_by('position', 'start_date', 'subject__name')
        )
        context['enrollments'] = group.enrollments.select_related('student').all()
        if self.request.user.can_manage_users:
            context['subject_form'] = GroupSubjectForm(group=group)
            context['fillable'] = len(_fillable_subjects(group)[0])
        return context


class GroupCreateView(UserManagementRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'schedule/group_form.html'

    def get_initial(self):
        return {'course': self.request.GET.get('course')}

    def get_success_url(self):
        messages.success(self.request, f'Групу «{self.object.name}» створено.')
        return reverse('schedule:group_detail', args=[self.object.pk])


class GroupUpdateView(UserManagementRequiredMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = 'schedule/group_form.html'

    def get_success_url(self):
        messages.success(self.request, f'Групу «{self.object.name}» збережено.')
        return reverse('schedule:group_detail', args=[self.object.pk])


class GroupDeleteView(UserManagementRequiredMixin, View):
    """Разом із групою зникають її предмети, зарахування й розклад — без
    групи вони нічого не означають. Облікові записи людей лишаються."""

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        group.delete()
        messages.success(request, f'Групу «{group.name}» видалено.')
        return redirect('schedule:group_list')


def _fillable_subjects(group):
    """Предмети курсу, які можна додати в групу гуртом, і ті, що не можна.

    Гуртом береться лише однозначне: предмет, у якого в каталозі рівно один
    викладач. Де викладачів нема або кілька — вибір за людиною, тож такі
    предмети повертаються окремо, щоб про них сказати, а не тихо пропустити.
    """
    taken = set(group.group_subjects.values_list('subject_id', flat=True))
    ready, ambiguous = [], []
    # Предмет буває в кількох курсах з різними лекторами — беремо того, хто
    # веде в курсі цієї групи (`CourseSubject.lecturers`).
    links = group.course.program.exclude(subject_id__in=taken).select_related(
        'subject').prefetch_related('teachers', 'subject__teachers')
    for link in links:
        teachers = link.lecturers
        if len(teachers) == 1:
            ready.append((link.subject, teachers[0]))
        else:
            ambiguous.append(link.subject)
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
            names = ', '.join(s.name for s in ambiguous[:5])
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


def _safe_next(request, fallback):
    """Повернутися туди, звідки прийшли (зі сторінки групи чи зі списку студентів)."""
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(
            target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return fallback


class StudentFormMixin(UserManagementRequiredMixin):
    template_name = 'schedule/student_form.html'

    def back_url(self):
        return _safe_next(self.request, reverse('schedule:student_list'))


class StudentCreateView(StudentFormMixin, View):
    """Зарахувати до групи нового студента або того, хто вже є на платформі.

    Новому одразу створюється обліковий запис із роллю «студент». Хто вже
    навчався (або вчиться в іншій групі), обирається зі списку — другий
    обліковий запис тій самій людині не потрібен.
    """

    def get(self, request):
        initial = {'group': request.GET.get('group')}
        return self.render(EnrollmentForm(initial=initial, student_required=False),
                           NewStudentForm(prefix='new'), mode='new')

    def post(self, request):
        mode = 'existing' if request.POST.get('mode') == 'existing' else 'new'
        enrollment_form = EnrollmentForm(request.POST, student_required=mode == 'existing')
        new_form = NewStudentForm(request.POST, prefix='new')

        valid = enrollment_form.is_valid()
        if mode == 'new':
            valid = new_form.is_valid() and valid
        if not valid:
            return self.render(enrollment_form, new_form, mode)

        with transaction.atomic():
            enrollment = enrollment_form.save(commit=False)
            if mode == 'new':
                enrollment.student = new_form.save()
            enrollment.save()
        messages.success(
            request,
            f'{enrollment.student.display_name} — у групі «{enrollment.group.name}».',
        )
        return redirect(self.back_url())

    def render(self, enrollment_form, new_form, mode):
        return render(self.request, self.template_name, {
            'form': enrollment_form,
            'new_form': new_form,
            'mode': mode,
            'creating': True,
            'next': self.back_url(),
        })


class StudentUpdateView(StudentFormMixin, View):
    """Навчання в групі (група, дати) і ПІБ студента — на одній сторінці.

    ПІБ правиться лише тоді, коли актор має право редагувати цей обліковий
    запис: менеджер не чіпає, скажімо, колегу, що вчиться в Академії.
    """

    def get_enrollment(self, pk):
        return get_object_or_404(Enrollment.objects.select_related('student', 'group'), pk=pk)

    def info_form(self, student, data=None):
        if not self.request.user.can_edit_user(student):
            return None
        return StudentInfoForm(data, instance=student, prefix='info')

    def get(self, request, pk):
        enrollment = self.get_enrollment(pk)
        return self.render(enrollment, EnrollmentForm(instance=enrollment),
                           self.info_form(enrollment.student))

    def post(self, request, pk):
        enrollment = self.get_enrollment(pk)
        form = EnrollmentForm(request.POST, instance=enrollment)
        info = self.info_form(enrollment.student, request.POST)
        if form.is_valid() and (info is None or info.is_valid()):
            with transaction.atomic():
                form.save()
                if info is not None:
                    info.save()
            messages.success(request, f'Дані студента {enrollment.student.display_name} збережено.')
            return redirect(self.back_url())
        return self.render(enrollment, form, info)

    def render(self, enrollment, form, info):
        return render(self.request, self.template_name, {
            'form': form,
            'info_form': info,
            'enrollment': enrollment,
            'creating': False,
            'next': self.back_url(),
        })


class StudentDeleteView(UserManagementRequiredMixin, View):
    """Прибирає рядок навчання в групі. Обліковий запис лишається —
    його видаляють у «Користувачах», якщо людина зовсім іде з платформи."""

    def post(self, request, pk):
        enrollment = get_object_or_404(Enrollment.objects.select_related('student', 'group'), pk=pk)
        enrollment.delete()
        messages.success(
            request,
            f'{enrollment.student.display_name} більше не в групі «{enrollment.group.name}».',
        )
        return redirect(_safe_next(request, reverse('schedule:student_list')))
