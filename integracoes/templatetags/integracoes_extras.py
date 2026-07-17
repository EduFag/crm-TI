from django import template

from integracoes.markdown_safe import markdown_leve_safe

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


@register.filter(name='markdown_leve')
def markdown_leve_filter(value):
    """Renderiza Markdown leve (negrito, listas, etc.) de forma segura."""
    return markdown_leve_safe(value or '')
