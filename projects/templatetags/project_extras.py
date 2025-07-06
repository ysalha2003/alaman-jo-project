from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split a string by the given separator."""
    if value:
        return value.split(arg)
    return []

@register.filter
def trim(value):
    """Remove leading and trailing whitespace."""
    if value:
        return value.strip()
    return value

@register.filter
def slice_list(value, arg):
    """Slice a list using Python slice notation."""
    try:
        start, end = arg.split(':')
        start = int(start) if start else None
        end = int(end) if end else None
        return value[start:end]
    except (ValueError, TypeError):
        return value
