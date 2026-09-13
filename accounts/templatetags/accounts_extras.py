from django import template

register = template.Library()


@register.filter
def can_edit(actor, target):
    return actor.is_authenticated and actor.can_edit_user(target)
