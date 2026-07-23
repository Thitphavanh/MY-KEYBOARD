from django import template

register = template.Library()


@register.filter
def kip(value):
    try:
        return "₭ " + "{:,}".format(round(float(value)))
    except (TypeError, ValueError):
        return "₭ 0"


@register.filter
def spec_label(value):
    return value.split(":", 1)[0].strip() if ":" in value else value


@register.filter
def spec_value(value):
    return value.split(":", 1)[1].strip() if ":" in value else ""


@register.filter
def get_item(mapping, key):
    return mapping.get(key)
