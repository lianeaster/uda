import calendar
import datetime as dt

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView

from accounts.mixins import UserManagementRequiredMixin
from accounts.models import User

from .forms import CourseForm, ScheduleEntryForm, SubjectForm
from .models import Course, ScheduleEntry, Subject
from .services import build_month_grid, can_modify

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


class ScheduleView(LoginRequiredMixin, View):
    template_name = 'schedule/schedule.html'

    def get(self, request):
        user = request.user
        anchor = _parse_month(request)
        teachers = User.objects.filter(role=User.Role.TEACHER)

        viewed_teacher = None
        viewing_unassigned = False
        teacher_param = None
        can_add = False
        has_view = False

        if user.is_teacher:
            viewed_teacher = user
            teacher_param = str(user.pk)
            can_add = True
            has_view = True
        else:
            can_add = user.is_manager or user.is_super_admin
            requested = request.GET.get('teacher')
            if requested == 'unassigned':
                viewing_unassigned = True
                teacher_param = 'unassigned'
                has_view = True
            elif requested:
                viewed_teacher = teachers.filter(pk=requested).first()
                if viewed_teacher is not None:
                    teacher_param = str(viewed_teacher.pk)
                    has_view = True
            elif teachers.exists():
                viewed_teacher = teachers.first()
                teacher_param = str(viewed_teacher.pk)
                has_view = True

        weeks = []
        entries_json = {}
        if has_view:
            if viewing_unassigned:
                entries = ScheduleEntry.objects.filter(teacher__isnull=True).select_related('subject', 'course')
            else:
                # Include Academy-wide reservations with no teacher yet, so a
                # conflict with this teacher's booking is visible and flagged.
                entries = ScheduleEntry.objects.filter(
                    Q(teacher=viewed_teacher) | Q(teacher__isnull=True)
                ).select_related('subject', 'course', 'teacher')
            weeks = build_month_grid(entries, anchor, user)
            for week in weeks:
                for day in week:
                    if day['in_month'] and day['entries']:
                        entries_json[day['date'].isoformat()] = [
                            {
                                'id': e.pk,
                                'start': e.start_time.strftime('%H:%M'),
                                'end': e.end_time.strftime('%H:%M'),
                                'start_hour': e.start_time.hour,
                                'end_hour': e.end_time.hour,
                                'color': e.color,
                                'title': e.title,
                                'initials': e.teacher.initials if e.teacher_id else '',
                                'deletable': e.deletable,
                                'editable': e.editable,
                                'conflict': e.has_conflict,
                                'course_id': e.course_id,
                                'subject_id': e.subject_id,
                                'teacher_id': e.teacher_id,
                                'notes': e.notes,
                            }
                            for e in day['entries']
                        ]

        form = None
        if can_add and has_view:
            initial = None if user.is_teacher else {'teacher': viewed_teacher.pk if viewed_teacher else None}
            form = ScheduleEntryForm(actor=user, initial=initial)

        context = {
            'weeks': weeks,
            'entries_json': entries_json,
            'anchor': anchor,
            'month_label': f'{UK_MONTHS[anchor.month]} {anchor.year}',
            'weekday_labels': UK_WEEKDAYS,
            'prev_month': _shift_month(anchor, -1),
            'next_month': _shift_month(anchor, 1),
            'teachers': teachers,
            'viewed_teacher': viewed_teacher,
            'viewing_unassigned': viewing_unassigned,
            'teacher_param': teacher_param,
            'has_view': has_view,
            'can_add': can_add and has_view,
            'form': form,
        }
        return render(request, self.template_name, context)


class ScheduleEntryCreateView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        if not (user.is_teacher or user.is_manager or user.is_super_admin):
            messages.error(request, 'У вас немає прав додавати записи до розкладу.')
            return redirect('schedule:home')

        form = ScheduleEntryForm(request.POST, actor=user)
        month = request.POST.get('month')

        if form.is_valid():
            entry = form.save()
            teacher_param = str(entry.teacher_id) if entry.teacher_id else 'unassigned'
            messages.success(request, 'Запис додано до розкладу.')
        else:
            teacher_param = request.POST.get('teacher') or (str(user.pk) if user.is_teacher else 'unassigned')
            error_text = ' '.join(
                f'{errors[0]}' for errors in form.errors.values()
            ) or 'Перевірте поля форми.'
            messages.error(request, f'Не вдалося зберегти запис: {error_text}')

        params = {k: v for k, v in {'teacher': teacher_param, 'month': month}.items() if v}
        base_url = reverse('schedule:home')
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        return redirect(f'{base_url}?{query}' if query else base_url)


class ScheduleEntryDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = ScheduleEntry.objects.filter(pk=pk).first()
        user = request.user
        if entry is None:
            messages.info(request, 'Цей запис уже видалено.')
        elif not can_modify(entry, user):
            messages.error(request, 'У вас немає прав видалити цей запис.')
        else:
            entry.delete()
            messages.success(request, 'Запис видалено з розкладу.')
        base_url = reverse('schedule:home')
        params = {k: v for k, v in {'teacher': request.POST.get('teacher'), 'month': request.POST.get('month')}.items() if v}
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        return redirect(f'{base_url}?{query}' if query else base_url)


class ScheduleEntryUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = ScheduleEntry.objects.filter(pk=pk).first()
        user = request.user
        month = request.POST.get('month')

        if entry is None:
            messages.info(request, 'Цей запис уже видалено.')
        elif not can_modify(entry, user):
            messages.error(request, 'У вас немає прав редагувати цей запис.')
        else:
            form = ScheduleEntryForm(request.POST, actor=user, instance=entry)
            if form.is_valid():
                entry = form.save()
                messages.success(request, 'Запис оновлено.')
            else:
                error_text = ' '.join(
                    f'{errors[0]}' for errors in form.errors.values()
                ) or 'Перевірте поля форми.'
                messages.error(request, f'Не вдалося зберегти зміни: {error_text}')

        teacher_param = request.POST.get('teacher') or (str(entry.teacher_id) if entry and entry.teacher_id else 'unassigned')
        params = {k: v for k, v in {'teacher': teacher_param, 'month': month}.items() if v}
        base_url = reverse('schedule:home')
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        return redirect(f'{base_url}?{query}' if query else base_url)


class CourseListView(UserManagementRequiredMixin, ListView):
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


class SubjectListView(UserManagementRequiredMixin, ListView):
    model = Subject
    template_name = 'schedule/subject_list.html'
    context_object_name = 'subjects'

    def get_queryset(self):
        return Subject.objects.select_related('course').prefetch_related('teachers')


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
