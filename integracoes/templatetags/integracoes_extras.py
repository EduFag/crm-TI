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


@register.filter
def contains(seq, item):
    """True se item está na sequência (checklist de modelos)."""
    if not seq:
        return False
    try:
        return item in seq
    except TypeError:
        return False
