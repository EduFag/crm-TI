"""Mixin HTMX do discador (redirect preservando aba)."""

from django.http import HttpResponse
from django.urls import reverse

from core.htmx import HtmxModalMixin


class DiscadorModalMixin(HtmxModalMixin):
    """Redireciona para JoyTec preservando a aba ativa após salvar modal."""

    list_url_name = 'discador:joytec'
    discador_tab = 'acessos'

    def htmx_redirect_response(self, url_name=None):
        url = reverse(url_name or self.list_url_name)
        if self.discador_tab:
            url = f'{url}?tab={self.discador_tab}'
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
