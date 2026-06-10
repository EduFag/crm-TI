import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.forms import ChipGridCreateForm, ReturnToTiForm, TransferForm
from chips.models import Batch, Chip, Operator
from chips.queries import chip_para_grid_dict, chips_operacionais
from chips.services import (
    atualizar_chip_grid,
    criar_chip_operacional,
    devolver_para_ti,
    transferir_chip,
    entregar_chip,
)


class _JsonChipsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_CHIPS


class ChipGridDataView(_JsonChipsMixin, View):
    """GET /chips/api/grid/ — dados para Tabulator."""

    def get(self, request):
        chips = chips_operacionais().order_by('line_number')
        data = [chip_para_grid_dict(c) for c in chips]
        operators = list(
            Operator.objects.filter(status=Operator.StatusChoices.ACTIVE)
            .values('id', 'name')
        )
        envelopes = [
            {'id': b.id, 'label': b.label}
            for b in Batch.objects.all().order_by('id')
        ]
        return JsonResponse({
            'data': data,
            'last_page': 1,
            'operators': operators,
            'envelopes': envelopes,
        })


class ChipGridCreateView(_JsonChipsMixin, View):
    """POST /chips/api/grid/ — nova linha no grid."""

    def post(self, request):
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido.'}, status=400)

        form = ChipGridCreateForm(payload)
        if not form.is_valid():
            return JsonResponse({'errors': form.errors}, status=400)

        cleaned = form.cleaned_data
        try:
            row = criar_chip_operacional(
                line_number=cleaned['line_number'],
                operator=cleaned['operator'],
                custody=cleaned['custody'],
                employee_name=cleaned.get('employee_name', ''),
                employee_user=cleaned.get('employee_user'),
                activated_at=cleaned.get('activated_at'),
                batch=cleaned.get('batch'),
                actor=request.user,
            )
        except ValidationError as exc:
            return JsonResponse({'error': exc.messages[0] if exc.messages else str(exc)}, status=400)

        return JsonResponse({'data': row}, status=201)


class ChipGridUpdateView(_JsonChipsMixin, View):
    """PATCH /chips/api/grid/<pk>/ — edição inline."""

    def patch(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk)
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido.'}, status=400)

        try:
            row = atualizar_chip_grid(chip, dados=payload, actor=request.user)
        except ValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, 'messages') and exc.messages else str(exc)
            return JsonResponse({'error': msg}, status=400)

        return JsonResponse({'data': row})


class ChipTransferView(_JsonChipsMixin, View):
    """POST /chips/api/grid/<pk>/transfer/ — transferência de posse."""

    def post(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk)
        form = TransferForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'errors': form.errors}, status=400)

        try:
            if chip.custody == Chip.CustodyChoices.WITH_TI:
                row = entregar_chip(
                    chip,
                    employee_name=form.cleaned_data['employee_name'],
                    employee_user=form.cleaned_data.get('employee_user'),
                    actor=request.user,
                )
            else:
                row = transferir_chip(
                    chip,
                    novo_nome=form.cleaned_data['employee_name'],
                    novo_user=form.cleaned_data.get('employee_user'),
                    actor=request.user,
                )
        except ValidationError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse({'data': row, 'success': True})


class ChipReturnView(_JsonChipsMixin, View):
    """POST /chips/api/grid/<pk>/return/ — devolve chip para TI."""

    def post(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk)
        form = ReturnToTiForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'errors': form.errors}, status=400)

        try:
            row = devolver_para_ti(chip, envelope=form.cleaned_data['envelope'], actor=request.user)
        except ValidationError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        return JsonResponse({'data': row, 'success': True})


class ChipGridCreateModalView(ModuloObrigatorioMixin, View):
    """GET modal HTMX para cadastrar nova linha no grid."""

    modulo_obrigatorio = MODULO_CHIPS
    template_name = 'chips/_grid_create_modal.html'

    def get(self, request):
        form = ChipGridCreateForm()
        has_operators = Operator.objects.filter(
            status=Operator.StatusChoices.ACTIVE,
        ).exists()
        has_envelopes = Batch.objects.filter(
            tipo=Batch.TipoChoices.ENVELOPE,
            status=Batch.StatusChoices.OPEN,
        ).exists()
        return render(request, self.template_name, {
            'form': form,
            'has_operators': has_operators,
            'has_envelopes': has_envelopes,
        })


class ChipTransferModalView(ModuloObrigatorioMixin, View):
    """GET modal HTMX de transferência."""

    modulo_obrigatorio = MODULO_CHIPS
    template_name = 'chips/_transfer_modal.html'

    def get(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk)
        form = TransferForm()
        return render(request, self.template_name, {'chip': chip, 'form': form})
