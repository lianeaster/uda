from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from accounts.models import User
from schedule.models import Course, Enrollment, Group, ScheduleEntry, Subject


class DashboardView(LoginRequiredMixin, View):
    """The tiles are the role's whole map of the platform.

    A manager or super-admin gets every tile. A teacher gets the same minus
    «Викладачі», and their «Групи» / «Студенти» counts are scoped to the
    groups where they actually teach — the catalogue (courses, subjects) is
    the same for everyone.
    """

    template_name = 'dashboard/home.html'

    def get(self, request):
        user = request.user
        context = {}

        if user.is_student and not (user.can_manage_users or user.is_teacher):
            # Група — єдиний шлях студента до своїх предметів і викладачів.
            own = Group.objects.for_person(user)
            context.update({
                'student_tiles': True,
                'group_total': own.count(),
                'group_active': own.active().count(),
            })

        if user.can_manage_users or user.is_teacher:
            groups = Group.objects.all() if user.can_manage_users else Group.objects.for_person(user)
            enrollments = (
                Enrollment.objects.all() if user.can_manage_users
                else Enrollment.objects.for_teacher(user)
            )
            context.update({
                'show_tiles': True,
                # Хто лише викладає — бачить свої групи/студентів/предмети.
                # Хто ще й керує, для того керування головне: тайли рахують усе,
                # а звузити до свого можна вже на самій сторінці.
                'own_scope': user.is_teacher and not user.can_manage_users,
                'group_total': groups.count(),
                'group_active': groups.active().count(),
                'student_count': enrollments.active().values('student_id').distinct().count(),
                'course_count': Course.objects.count(),
                # Каталог предметів однаковий для всіх, але викладачеві на
                # тайлі цікаві свої — саме на них веде посилання.
                'subject_count': (
                    Subject.objects.count() if user.can_manage_users
                    else user.subjects.count()
                ),
                'subject_total': Subject.objects.count(),
            })
            # Доля пропозицій: менеджмент бачить, що чекає на його розгляд,
            # викладач — скільки його слотів ще без відповіді. Новина про
            # вже ухвалене рішення показується авторові, доки він її не відкрив.
            proposals = ScheduleEntry.objects.proposals()
            mine = proposals.by_author(user)
            context.update({
                'proposals_pending': (
                    proposals.awaiting_review().count() if user.can_manage_users
                    else mine.awaiting_review().count()
                ),
                'proposals_news': mine.unseen_decisions().count(),
            })
            if user.can_manage_users:
                context['teacher_count'] = User.objects.with_role(User.Role.TEACHER).count()

        return render(request, self.template_name, context)
