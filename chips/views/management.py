from django.views.generic import CreateView, UpdateView, FormView

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
    fields = ['nome']
    chips_tab = 'envelopes'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def get_modal_title(self):
        return f'Editar — {self.object.label}'

    def get_modal_subtitle(self):
        return 'Atualize os dados do envelope.'

    def form_valid(self, form):
        self.object = form.save()
        return self.htmx_redirect_response()


class BatchCreateView(ChipsModalMixin, _ChipsMixin, CreateView):
    model = Batch
    fields = ['nome']
    chips_tab = 'envelopes'
    modal_title = 'Novo envelope'
    modal_subtitle = 'Envelopes físicos na TI: nome e data de criação automática.'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'

    def form_valid(self, form):
        self.object = form.save()
        log_lote_criado(self.object, self.request.user)
        return self.htmx_redirect_response()


class ChipCreateView(ChipsModalMixin, _ChipsMixin, CreateView):
    model = Chip
    fields = [
        'line_number', 'operator', 'status', 'technology', 'iccid',
        'batch', 'activated_at',
    ]
    chips_tab = 'chips'
    modal_title = 'Novo Chip'
    modal_subtitle = 'Cadastre uma nova linha no inventário.'
    modal_submit_label = 'Salvar'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        from django import forms
        if 'activated_at' in form.fields:
            form.fields['activated_at'].widget = forms.DateInput(attrs={'type': 'date'})
        if 'line_number' in form.fields:
            form.fields['line_number'].widget.attrs.update({
                'data-mask': '(00) 00000-0000',
                'placeholder': '(11) 98888-7777',
            })
        return form

    def form_valid(self, form):
        self.object = form.save()
        log_chip_criado(self.object, self.request.user)
        return self.htmx_redirect_response()


class ChipUpdateView(ChipsModalMixin, _ChipsMixin, UpdateView):
    model = Chip
    fields = [
        'line_number', 'operator', 'status', 'technology', 'iccid',
        'batch', 'activated_at',
    ]
    chips_tab = 'chips'
    modal_submit_label = 'Salvar'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        from django import forms
        if 'activated_at' in form.fields:
            form.fields['activated_at'].widget = forms.DateInput(attrs={'type': 'date'})
        if 'line_number' in form.fields:
            form.fields['line_number'].widget.attrs.update({
                'data-mask': '(00) 00000-0000',
                'placeholder': '(11) 98888-7777',
            })
        return form

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


class ChipGeneralTransferView(ChipsModalMixin, _ChipsMixin, FormView):
    from django.views.generic import FormView
    from chips.forms import GeneralTransferForm
    form_class = GeneralTransferForm
    template_name = 'chips/_general_transfer_modal.html'
    chips_tab = 'chips'
    modal_title = 'Transferência de Linha (Atribuição)'
    modal_subtitle = 'Entregar um chip disponível na TI para um funcionário.'
    modal_submit_label = 'Confirmar Transferência'
    modal_max_width = 'max-w-lg'

    def get_template_names(self):
        return [self.template_name]

    def form_valid(self, form):
        chip = form.cleaned_data['chip']
        nome = form.cleaned_data['employee_name']
        usuario = form.cleaned_data.get('employee_user')

        from chips.services import entregar_chip
        from django.core.exceptions import ValidationError
        try:
            entregar_chip(
                chip,
                employee_name=nome,
                employee_user=usuario,
                actor=self.request.user,
            )
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        return self.htmx_redirect_response()


from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

@require_POST
def batch_delete_view(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    nome_str = batch.nome or f"#{batch.id}"
    batch.delete()
    messages.success(request, f'Envelope "{nome_str}" excluído com sucesso.')
    return redirect('/chips/?tab=envelopes')
