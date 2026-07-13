# core/templatetags/jalali.py
from django import template
import jdatetime

register = template.Library()

@register.filter
def to_jalali(value, fmt="%Y/%m/%d - %H:%M"):
    if not value:
        return "-"
    try:
        return jdatetime.datetime.fromgregorian(datetime=value).strftime(fmt)
    except Exception:
        return value
