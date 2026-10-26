from django import template

register = template.Library()


@register.filter
def startswith(value, prefix):
    return str(value or "").startswith(str(prefix))
