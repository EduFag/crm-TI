from django.urls import reverse_lazy
from django.views.generic import CreateView
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.models import Recharge, Chip
from django.shortcuts import get_object_or_404

class RechargeCreateView(ModuloObrigatorioMixin, CreateView):
    """Registra uma recarga (RF14, RF15)"""
    modulo_obrigatorio = MODULO_CHIPS
    model = Recharge
    fields = ['chip', 'amount']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:dashboard')

    def get_initial(self):
        initial = super().get_initial()
        # Atalho de recarga pré-preenche o chip (RF15)
        chip_id = self.request.GET.get('chip_id')
        if chip_id:
            initial['chip'] = get_object_or_404(Chip, id=chip_id)
        return initial

    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        return super().form_valid(form)
