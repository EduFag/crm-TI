from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View

from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.forms import AssignmentForm
from chips.models import Chip
from chips.services import devolver_para_ti, entregar_chip, transferir_chip


class _ChipsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_CHIPS


class AssignmentView(_ChipsMixin, TemplateView):
    """Tela de atribuição — entrega ou transferência (RF08, RF09, RF10)."""
    template_name = 'chips/assignment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_chips'] = Chip.objects.filter(
            status=Chip.StatusChoices.AVAILABLE,
            custody=Chip.CustodyChoices.WITH_TI,
        ).select_related('operator')
        context['in_use_chips'] = Chip.objects.filter(
            custody=Chip.CustodyChoices.WITH_PERSON,
        ).select_related('operator')
        context['form'] = AssignmentForm()
        return context

    def post(self, request, *args, **kwargs):
        form = AssignmentForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Corrija os erros do formulário.')
            return redirect('chips:assignment')

        chip = get_object_or_404(Chip, id=form.cleaned_data['chip_id'])
        nome = form.cleaned_data['employee_name']
        usuario = form.cleaned_data.get('employee_user')

        try:
            if chip.custody == Chip.CustodyChoices.WITH_PERSON:
                transferir_chip(chip, novo_nome=nome, novo_user=usuario, actor=request.user)
                messages.success(request, f'Chip {chip.line_number} transferido para {nome}.')
            else:
                entregar_chip(chip, employee_name=nome, employee_user=usuario, actor=request.user)
                messages.success(request, f'Chip {chip.line_number} entregue para {nome}.')
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))

        return redirect('chips:dashboard')


class ReturnChipView(_ChipsMixin, View):
    """Devolve um chip ao estoque na TI (RF12)."""

    def post(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk, custody=Chip.CustodyChoices.WITH_PERSON)
        envelope_id = request.POST.get('envelope_id')
        if not envelope_id:
            messages.error(request, 'Selecione o envelope na TI.')
            return redirect('chips:chip_list')

        from chips.models import Batch
        envelope = get_object_or_404(
            Batch,
            pk=envelope_id,
            tipo=Batch.TipoChoices.ENVELOPE,
        )

        try:
            devolver_para_ti(chip, envelope=envelope, actor=request.user)
            messages.success(request, f'Chip {chip.line_number} retornado ao envelope {envelope.label}.')
        except ValidationError as exc:
            messages.error(request, str(exc))

        return redirect(request.POST.get('next') or 'chips:dashboard')
