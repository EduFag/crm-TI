"""Utilitários HTMX para formulários em modal flutuante."""

from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


class HtmxModalMixin:
    """
    Exibe formulários create/update como modal via HTMX na listagem.
    GET sem HX-Request redireciona para list_url_name.
    POST válido responde com HX-Redirect para recarregar a tabela.
    """

    modal_template_name = 'core/_htmx_form_modal.html'
    list_url_name = None
    modal_title = 'Formulário'
    modal_subtitle = ''
    modal_submit_label = 'Salvar'
    modal_max_width = 'max-w-lg'
    form_layout = 'fields'

    def is_htmx(self):
        return bool(self.request.headers.get('HX-Request'))

    def get(self, request, *args, **kwargs):
        if not self.is_htmx():
            return redirect(self.list_url_name)
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        return [self.modal_template_name]

    def get_modal_title(self):
        return self.modal_title

    def get_modal_subtitle(self):
        return self.modal_subtitle

    def get_modal_submit_label(self):
        return self.modal_submit_label

    def get_form_action(self):
        return self.request.get_full_path()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'modal_title': self.get_modal_title(),
            'modal_subtitle': self.get_modal_subtitle(),
            'modal_submit_label': self.get_modal_submit_label(),
            'modal_max_width': self.modal_max_width,
            'form_layout': self.form_layout,
            'form_action': self.get_form_action(),
        })
        return context

    def htmx_redirect_response(self, url_name=None):
        url = reverse(url_name or self.list_url_name)
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response

    def form_invalid(self, form):
        # Retorna 200 para o HTMX trocar o HTML do modal (4xx gera erro no console e não faz swap)
        return self.render_to_response(self.get_context_data(form=form))
