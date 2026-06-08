from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.models import Chip, Operator, Batch


class _ChipsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_CHIPS


# ----------------- OPERATOR (RF06) -----------------
class OperatorListView(_ChipsMixin, ListView):
    model = Operator
    template_name = 'chips/operator_list.html'
    context_object_name = 'operators'

class OperatorCreateView(_ChipsMixin, CreateView):
    model = Operator
    fields = ['name', 'status']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:operator_list')

# ----------------- BATCH (RF06) -----------------
class BatchListView(_ChipsMixin, ListView):
    model = Batch
    template_name = 'chips/batch_list.html'
    context_object_name = 'batches'

class BatchCreateView(_ChipsMixin, CreateView):
    model = Batch
    fields = ['identifier', 'status']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:batch_list')

# ----------------- CHIP (RF05, RF07) -----------------
class ChipListView(_ChipsMixin, ListView):
    model = Chip
    template_name = 'chips/chip_list.html'
    context_object_name = 'chips'
    
    def get_queryset(self):
        return Chip.objects.select_related('operator', 'batch').all().order_by('-created_at')

class ChipCreateView(_ChipsMixin, CreateView):
    model = Chip
    fields = ['line_number', 'status', 'technology', 'fixed_cost', 'iccid', 'plan_type', 'operator', 'batch']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:chip_list')

class ChipUpdateView(_ChipsMixin, UpdateView):
    model = Chip
    fields = ['line_number', 'status', 'technology', 'fixed_cost', 'iccid', 'plan_type', 'operator', 'batch']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:chip_list')
