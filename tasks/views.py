import datetime as dt
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from accounting.payroll import sync_payday_tasks
from schedule.services import month_weeks
from schedule.views import UK_MONTHS, UK_WEEKDAYS

from .forms import TaskForm
from .models import Task

DONE_SHOWN = 15   # скільки останніх виконаних видно під списком


def _month(request):
    try:
        return dt.date.fromisoformat(request.GET.get('month', '')).replace(day=1)
    except ValueError:
        return dt.date.today().replace(day=1)


def _shift_month(anchor, delta):
    month = anchor.month - 1 + delta
    return dt.date(anchor.year + month // 12, month % 12 + 1, 1)


def _back(request):
    target = request.POST.get('next')
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}):
        return redirect(target)
    return redirect('tasks:list')


class TaskListView(LoginRequiredMixin, View):
    """«Мої задачі» — особистий календар, окремо від розкладу занять.

    Тут свої задачі людини, а в того, хто керує, — ще й спільні задачі
    керування, серед них нагадування про виплати викладачам.
    """

    template_name = 'tasks/task_list.html'

    def get(self, request, form=None):
        user = request.user
        if user.can_manage_users:
            sync_payday_tasks()
        today = dt.date.today()
        anchor = _month(request)
        tasks = Task.objects.for_user(user).select_related('assignee', 'done_by')

        weeks = month_weeks(anchor)
        by_day = defaultdict(list)
        for task in tasks.filter(due_date__range=(weeks[0][0], weeks[-1][-1])):
            by_day[task.due_date].append(task)

        open_tasks = list(tasks.open())
        return render(request, self.template_name, {
            'weeks': [[{
                'date': day,
                'in_month': day.month == anchor.month,
                'is_today': day == today,
                'tasks': by_day.get(day, []),
            } for day in week] for week in weeks],
            'month_label': f'{UK_MONTHS[anchor.month]} {anchor.year}',
            'weekday_labels': UK_WEEKDAYS,
            'prev_month': _shift_month(anchor, -1),
            'next_month': _shift_month(anchor, 1),
            'overdue': [t for t in open_tasks if t.due_date < today],
            'upcoming': [t for t in open_tasks if t.due_date >= today],
            'done': tasks.done().order_by('-done_at')[:DONE_SHOWN],
            'form': form or TaskForm(actor=user, initial={'due_date': today}),
        })


class TaskCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = TaskForm(request.POST, actor=request.user)
        if not form.is_valid():
            return TaskListView().get(request, form=form)
        form.save()
        messages.success(request, 'Задачу додано.')
        return _back(request)


class TaskDoneView(LoginRequiredMixin, View):
    """Позначити виконаною — або повернути, якщо поспішили."""

    def post(self, request, pk):
        task = Task.objects.for_user(request.user).filter(pk=pk).first()
        if task is None:
            messages.error(request, 'Цієї задачі немає або вона не ваша.')
            return _back(request)
        if request.POST.get('done') == '1':
            task.done_at, task.done_by = timezone.now(), request.user
        else:
            task.done_at = task.done_by = None
        task.save(update_fields=['done_at', 'done_by'])
        return _back(request)


class TaskDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = Task.objects.for_user(request.user).filter(pk=pk).first()
        if task is None or not task.can_delete(request.user):
            messages.error(request, 'Цю задачу видалити не можна — її можна лише виконати.')
        else:
            task.delete()
            messages.success(request, 'Задачу видалено.')
        return _back(request)
