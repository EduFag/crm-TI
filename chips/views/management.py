from django.views.generic import ListView, CreateView, UpdateView
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from core.htmx import HtmxModalMixin
from chips.models import Chip, Operator, Batch
from chips.audit import log_chip_atualizado, log_chip_criado, log_lote_criado, log_operadora_criada


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
        log_operadora_criada(self.object, self.request.user)
        return self.htmx_redirect_response()

# ----------------- BATCH (RF06) -----------------
class BatchListView(_ChipsMixin, ListView):
    model = Batch
    template_name = 'chips/batch_list.html'
    context_object_name = 'batches'

class BatchCreateView(HtmxModalMixin, _ChipsMixin, CreateView):
    model = Batch
    fields = ['identifier', 'tipo', 'nome', 'setor', 'status']
    list_url_name = 'chips:batch_list'
    modal_title = 'Novo envelope / lote'
    modal_subtitle = 'Envelopes físicos na TI: nome, setor e data de entrada automática.'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        log_lote_criado(self.object, self.request.user)
        return self.htmx_redirect_response()

# ----------------- CHIP (RF05, RF07) -----------------
class ChipListView(_ChipsMixin, ListView):
    model = Chip
    template_name = 'chips/chip_list.html'
    context_object_name = 'chips'

    def get_queryset(self):
        return Chip.objects.select_related('operator', 'batch').all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['envelopes'] = Batch.objects.filter(
            tipo=Batch.TipoChoices.ENVELOPE,
            status=Batch.StatusChoices.OPEN,
        ).order_by('identifier')
        return context

class ChipCreateView(HtmxModalMixin, _ChipsMixin, CreateView):
    model = Chip
    fields = [
        'line_number', 'status', 'custody', 'technology', 'fixed_cost', 'iccid',
        'plan_type', 'operator', 'batch', 'activated_at',
    ]
    list_url_name = 'chips:chip_list'
    modal_title = 'Novo Chip'
    modal_subtitle = 'Cadastre uma nova linha no inventário.'
    modal_submit_label = 'Salvar'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        log_chip_criado(self.object, self.request.user)
        return self.htmx_redirect_response()


class ChipUpdateView(HtmxModalMixin, _ChipsMixin, UpdateView):
    model = Chip
    fields = [
        'line_number', 'status', 'custody', 'technology', 'fixed_cost', 'iccid',
        'plan_type', 'operator', 'batch', 'activated_at',
    ]
    list_url_name = 'chips:chip_list'
    modal_submit_label = 'Salvar'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'

    def get_modal_title(self):
        return f'Editar Chip — {self.object.line_number}'

    def get_modal_subtitle(self):
        return 'Atualize os dados da linha.'

    def form_valid(self, form):
        antes = Chip.objects.get(pk=self.object.pk)
        self.object = form.save()
        if (
            self.object.status == Chip.StatusChoices.BLOCKED
            and antes.status != Chip.StatusChoices.BLOCKED
        ):
            from chips.services import registrar_bloqueio
            registrar_bloqueio(self.object, self.request.user)
        elif (
            antes.status == Chip.StatusChoices.BLOCKED
            and self.object.status != Chip.StatusChoices.BLOCKED
        ):
            self.object.last_blocked_at = None
            self.object.save(update_fields=['last_blocked_at'])
        log_chip_atualizado(self.object, self.request.user, antes)
        return self.htmx_redirect_response()
