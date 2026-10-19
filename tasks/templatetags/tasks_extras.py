from django import template

register = template.Library()


@register.filter
def can_delete(task, user):
    return task.can_delete(user)
