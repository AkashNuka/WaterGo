from django import template
import math

register = template.Library()

@register.filter
def abs_value(value):
    """Return the absolute value of a number."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value