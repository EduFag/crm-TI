from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View

from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.models import Batch, Chip
from chips.services import devolver_para_ti


class _ChipsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_CHIPS


class ReturnChipView(_ChipsMixin, View):
    """Devolve um chip ao estoque na TI (RF12)."""

    def post(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk, custody=Chip.CustodyChoices.WITH_PERSON)
        envelope_id = request.POST.get('envelope_id')
        tab = request.POST.get('tab', 'chips')

        if not envelope_id:
            messages.error(request, 'Selecione o envelope na TI.')
            return redirect(f'/chips/?tab={tab}')

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

        return redirect(f'/chips/?tab={tab}')
