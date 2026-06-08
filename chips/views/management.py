from django.views.generic import ListView, CreateView, UpdateView
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from core.htmx import HtmxModalMixin
from chips.models import Chip, Operator, Batch


class _ChipsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_CHIPS


# ----------------- OPERATOR (RF06) -----------------
class OperatorListView(_ChipsMixin, ListView):
    model = Operator
    template_name = 'chips/operator_list.html'
    context_object_name = 'operators'

class OperatorCreateView(HtmxModalMixin, _ChipsMixin, CreateView):
    model = Operator
    fields = ['name', 'status']
    list_url_name = 'chips:operator_list'
    modal_title = 'Nova Operadora'
    modal_subtitle = 'Cadastre uma operadora de telefonia.'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        return self.htmx_redirect_response()

# ----------------- BATCH (RF06) -----------------
class BatchListView(_ChipsMixin, ListView):
    model = Batch
    template_name = 'chips/batch_list.html'
    context_object_name = 'batches'

class BatchCreateView(HtmxModalMixin, _ChipsMixin, CreateView):
    model = Batch
    fields = ['identifier', 'status']
    list_url_name = 'chips:batch_list'
    modal_title = 'Novo Lote'
    modal_subtitle = 'Registre um lote ou envelope de recebimento.'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        return self.htmx_redirect_response()

# ----------------- CHIP (RF05, RF07) -----------------
class ChipListView(_ChipsMixin, ListView):
    model = Chip
    template_name = 'chips/chip_list.html'
    context_object_name = 'chips'
    
    def get_queryset(self):
        return Chip.objects.select_related('operator', 'batch').all().order_by('-created_at')

class ChipCreateView(HtmxModalMixin, _ChipsMixin, CreateView):
    model = Chip
    fields = ['line_number', 'status', 'technology', 'fixed_cost', 'iccid', 'plan_type', 'operator', 'batch']
    list_url_name = 'chips:chip_list'
    modal_title = 'Novo Chip'
    modal_subtitle = 'Cadastre uma nova linha no inventário.'
    modal_submit_label = 'Salvar'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        return self.htmx_redirect_response()

class ChipUpdateView(HtmxModalMixin, _ChipsMixin, UpdateView):
    model = Chip
    fields = ['line_number', 'status', 'technology', 'fixed_cost', 'iccid', 'plan_type', 'operator', 'batch']
    list_url_name = 'chips:chip_list'
    modal_submit_label = 'Salvar'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'

    def get_modal_title(self):
        return f'Editar Chip — {self.object.line_number}'

    def get_modal_subtitle(self):
        return 'Atualize os dados da linha.'

    def form_valid(self, form):
        self.object = form.save()
        return self.htmx_redirect_response()
