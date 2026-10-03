from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def money(value):
    """Localized thousands separators, with a real minus sign."""
    if value is None:
        return ''
    text = intcomma(abs(int(value)))
    return f'−{text}' if value < 0 else text


@register.filter
def signed_money(value):
    """Like money, but always shows the sign: +1,200 / −800."""
    if value is None:
        return ''
    text = intcomma(abs(int(value)))
    return f'−{text}' if value < 0 else f'+{text}'
