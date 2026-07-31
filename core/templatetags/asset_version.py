"""Cache-bust de estáticos via ?v= (hash do commit / HELPDESK_FRONTEND_VERSION)."""
from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


def versao_assets() -> str:
    """Versão usada em ?v= — mesma fonte do helpdesk."""
    return getattr(settings, 'HELPDESK_FRONTEND_VERSION', '1') or '1'


def url_com_versao(path: str) -> str:
    """Monta URL de static com query de versão."""
    url = static(path)
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}v={versao_assets()}'


@register.simple_tag
def static_v(path):
    """URL de static com ?v= para invalidar cache do browser após deploy."""
    return url_com_versao(path)


@register.simple_tag
def asset_v():
    """Só o valor da versão (meta tags / debug)."""
    return versao_assets()
