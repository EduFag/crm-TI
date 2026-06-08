from django.shortcuts import get_object_or_404
from django.views.generic import CreateView

from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.htmx import ChipsModalMixin
from chips.models import Recharge, Chip
from chips.audit import log_recarga


class RechargeCreateView(ChipsModalMixin, ModuloObrigatorioMixin, CreateView):
    """Registra uma recarga (RF14, RF15) via modal no dashboard."""
    modulo_obrigatorio = MODULO_CHIPS
    model = Recharge
    fields = ['chip', 'amount']
    chips_tab = 'dashboard'
    modal_title = 'Nova Recarga'
    modal_subtitle = 'Registre o valor recarregado para a linha.'
    modal_submit_label = 'Registrar Recarga'
    form_layout = 'as_p'

    def get_initial(self):
        initial = super().get_initial()
        chip_id = self.request.GET.get('chip_id')
        if chip_id:
            initial['chip'] = get_object_or_404(Chip, id=chip_id)
        return initial

    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        self.object = form.save()
        log_recarga(self.object, self.request.user)
        return self.htmx_redirect_response()
