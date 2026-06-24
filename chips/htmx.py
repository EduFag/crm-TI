"""Mixin HTMX específico do módulo chips (redirect com aba ativa)."""

from django.http import HttpResponse
from django.urls import reverse

from core.htmx import HtmxModalMixin


class ChipsModalMixin(HtmxModalMixin):
    """Redireciona para /chips/ preservando a aba ativa após salvar modal."""

    list_url_name = 'chips:dashboard'
    chips_tab = 'dashboard'

    def htmx_redirect_response(self, url_name=None):
        url = reverse(url_name or self.list_url_name)
        if self.chips_tab:
            url = f'{url}?tab={self.chips_tab}'
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
