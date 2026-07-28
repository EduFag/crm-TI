from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View

from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.forms import ReturnToTiForm
from chips.models import Chip
from chips.services import devolver_para_ti


class _ChipsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_CHIPS


class ReturnChipView(_ChipsMixin, View):
    """Devolve um chip ao estoque na TI (RF12)."""

    def post(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk, usage_status=Chip.UsageChoices.IN_USE)
        tab = request.POST.get('tab', 'chips')
        form = ReturnToTiForm(request.POST)

        if not form.is_valid():
            messages.error(request, 'Selecione um envelope válido para a devolução.')
            return redirect(f'/chips/?tab={tab}')

        try:
            devolver_para_ti(
                chip,
                actor=request.user,
                batch=form.cleaned_data.get('envelope'),
            )
            messages.success(request, f'Chip {chip.line_number} retornado para TI.')
        except ValidationError as exc:
            messages.error(request, str(exc))

        return redirect(f'/chips/?tab={tab}')
