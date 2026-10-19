import datetime as dt

from django.shortcuts import render
from django.views import View

from accounts.mixins import UserManagementRequiredMixin

from . import payroll

UK_MONTHS_GENITIVE = [
    '', 'січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
    'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня',
]


def _requested_payday(request):
    """День виплати з адреси; будь-яку дату зводимо до її дня виплати."""
    raw = request.GET.get('payday')
    if raw:
        try:
            return payroll.payday_for(dt.date.fromisoformat(raw))
        except ValueError:
            pass
    return payroll.next_payday()


class PayrollView(UserManagementRequiredMixin, View):
    """Відомість виплат викладачам на 15-те чи 30-те — з розкладу, наживо.

    Лише для керування: тут ставки й суми, а їх бачать менеджер і
    супер-адмін (див. `schedule.pricing`).
    """

    template_name = 'accounting/payroll.html'

    def get(self, request):
        payroll.sync_payday_tasks()
        payday = _requested_payday(request)
        report = payroll.statement(payday)
        return render(request, self.template_name, {
            'report': report,
            'period_label': (
                f'{report.start.day}–{report.end.day} '
                f'{UK_MONTHS_GENITIVE[report.end.month]} {report.end.year}'
            ),
            'previous': payroll.previous_payday(payday),
            'following': payroll.following_payday(payday),
            'is_next': payday == payroll.next_payday(),
        })
