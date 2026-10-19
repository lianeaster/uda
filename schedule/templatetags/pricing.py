"""Гроші й години в таблицях вартості: «13 200», «1,5»."""

from django import template

register = template.Library()


@register.filter
def uah(amount):
    """Ціле число з вузьким нерозривним пробілом між тисячами, як пишуть гроші."""
    if amount is None or amount == '':
        return '—'
    return f'{int(amount):,}'.replace(',', ' ')


@register.filter
def hours(value):
    """3.0 → «3», 1.5 → «1,5»; порожньо — прочерк."""
    if value is None or value == '':
        return '—'
    text = f'{value:f}'.rstrip('0').rstrip('.') if '.' in f'{value:f}' else f'{value}'
    return text.replace('.', ',')
