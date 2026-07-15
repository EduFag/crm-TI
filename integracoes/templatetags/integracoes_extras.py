from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Acesso a dict[key] em templates."""
    if mapping is None:
        return ''
    try:
        return mapping.get(key, '')
    except AttributeError:
        return ''
