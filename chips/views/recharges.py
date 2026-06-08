from django.views.generic import CreateView
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from core.htmx import HtmxModalMixin
from chips.models import Recharge, Chip
from django.shortcuts import get_object_or_404

class RechargeCreateView(HtmxModalMixin, ModuloObrigatorioMixin, CreateView):
    """Registra uma recarga (RF14, RF15) via modal no dashboard."""
    modulo_obrigatorio = MODULO_CHIPS
    model = Recharge
    fields = ['chip', 'amount']
    list_url_name = 'chips:dashboard'
    modal_title = 'Nova Recarga'
    modal_subtitle = 'Registre o valor recarregado para a linha.'
    modal_submit_label = 'Registrar Recarga'
    form_layout = 'as_p'

    def get_initial(self):
        initial = super().get_initial()
        # Atalho de recarga pré-preenche o chip (RF15)
        chip_id = self.request.GET.get('chip_id')
        if chip_id:
            initial['chip'] = get_object_or_404(Chip, id=chip_id)
        return initial

    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        self.object = form.save()
        return self.htmx_redirect_response()
