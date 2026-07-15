from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import escape
from django.utils.safestring import mark_safe

from helpdesk.mentions import MENTION_RE
from helpdesk.ticket_access import usuario_pode_contestar_chamado

register = template.Library()


def _versao_frontend() -> str:
    return getattr(settings, 'HELPDESK_FRONTEND_VERSION', '1') or '1'


@register.simple_tag
def helpdesk_static(path):
    """URL de static do helpdesk com ?v= para invalidar cache do browser."""
    url = static(path)
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}v={_versao_frontend()}'


@register.simple_tag
def helpdesk_v():
    """Só o valor da versão (útil em hx-get e meta tags)."""
    return _versao_frontend()


@register.simple_tag(takes_context=True)
def pode_contestar_chamado(context, ticket):
    """Indica se o usuário logado pode contestar o chamado."""
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    return usuario_pode_contestar_chamado(request.user, ticket)


@register.filter(name='highlight_mentions')
def highlight_mentions(text):
    """Destaca @username no texto do comentário (HTML seguro)."""
    if not text:
        return ''
    escaped = escape(text)

    def _repl(match):
        username = match.group(1)
        return (
            f'<span class="font-semibold text-sky-600 bg-sky-50 px-0.5 rounded">'
            f'@{escape(username)}</span>'
        )

    # reaplicamos no texto já escapado; padrão não contém HTML
    highlighted = MENTION_RE.sub(_repl, escaped)
    return mark_safe(highlighted.replace('\n', '<br>'))
