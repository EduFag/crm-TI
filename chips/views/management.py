from django.views.generic import CreateView, UpdateView

from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.htmx import ChipsModalMixin
from chips.models import Chip, Operator, Batch
from chips.audit import log_chip_atualizado, log_chip_criado, log_lote_criado, log_operadora_criada


class _ChipsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_CHIPS


class OperatorUpdateView(ChipsModalMixin, _ChipsMixin, UpdateView):
    model = Operator
    fields = ['name', 'status']
    chips_tab = 'operators'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def get_modal_title(self):
        return f'Editar Operadora — {self.object.name}'

    def get_modal_subtitle(self):
        return 'Atualize nome e status da operadora.'

    def form_valid(self, form):
        self.object = form.save()
        return self.htmx_redirect_response()


class OperatorCreateView(ChipsModalMixin, _ChipsMixin, CreateView):
    model = Operator
    fields = ['name', 'status']
    chips_tab = 'operators'
    modal_title = 'Nova Operadora'
    modal_subtitle = 'Cadastre uma operadora de telefonia.'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        log_operadora_criada(self.object, self.request.user)
        return self.htmx_redirect_response()


class BatchUpdateView(ChipsModalMixin, _ChipsMixin, UpdateView):
    model = Batch
    fields = ['identifier', 'tipo', 'nome', 'setor', 'status']
    chips_tab = 'envelopes'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def get_modal_title(self):
        return f'Editar — {self.object.label}'

    def get_modal_subtitle(self):
        return 'Atualize os dados do envelope ou lote.'

    def form_valid(self, form):
        self.object = form.save()
        return self.htmx_redirect_response()


class BatchCreateView(ChipsModalMixin, _ChipsMixin, CreateView):
    model = Batch
    fields = ['identifier', 'tipo', 'nome', 'setor', 'status']
    chips_tab = 'envelopes'
    modal_title = 'Novo envelope / lote'
    modal_subtitle = 'Envelopes físicos na TI: nome, setor e data de entrada automática.'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        log_lote_criado(self.object, self.request.user)
        return self.htmx_redirect_response()


class ChipCreateView(ChipsModalMixin, _ChipsMixin, CreateView):
    model = Chip
    fields = [
        'line_number', 'status', 'custody', 'technology', 'fixed_cost', 'iccid',
        'plan_type', 'operator', 'batch', 'activated_at',
    ]
    chips_tab = 'chips'
    modal_title = 'Novo Chip'
    modal_subtitle = 'Cadastre uma nova linha no inventário.'
    modal_submit_label = 'Salvar'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        log_chip_criado(self.object, self.request.user)
        return self.htmx_redirect_response()


class ChipUpdateView(ChipsModalMixin, _ChipsMixin, UpdateView):
    model = Chip
    fields = [
        'line_number', 'status', 'custody', 'technology', 'fixed_cost', 'iccid',
        'plan_type', 'operator', 'batch', 'activated_at',
    ]
    chips_tab = 'chips'
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
