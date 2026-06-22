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
                employee_name=cleaned.get('employee_name') or '',
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
        chip = get_object_or_404(Chip, pk=pk, status=Chip.StatusChoices.IN_USE)
        form = TransferForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'errors': form.errors}, status=400)

        try:
            if chip.status == Chip.StatusChoices.AVAILABLE:
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
            row = devolver_para_ti(chip, actor=request.user)
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
        has_envelopes = Batch.objects.exists()
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


class ChipToggleEmailView(ModuloObrigatorioMixin, View):
    """POST /chips/api/grid/<pk>/toggle-email/ — Alterna email_vinculado para SIM."""
    modulo_obrigatorio = MODULO_CHIPS

    def post(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk)
        chip.email_vinculado = True
        chip.save(update_fields=['email_vinculado'])
        # Retorna HttpResponse 200 OK e via javascript poderíamos atualizar, 
        # mas como estamos no HTMX, vamos retornar o HTML da célula (td) se necessário,
        # ou recarregar a tabela.
        # Wait, the frontend logic will use HTMX to swap the TD.
        # Let's return just the HTML for the SIM span.
        html = '<span class="px-2.5 py-1 rounded text-xs font-bold bg-slate-100 text-slate-700">SIM</span>'
        from django.http import HttpResponse
        return HttpResponse(html)


class ChipObservationModalView(ModuloObrigatorioMixin, View):
    """GET /chips/api/grid/<pk>/observation/ — Modal com a observação."""
    modulo_obrigatorio = MODULO_CHIPS
    
    def get(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk)
        from django.http import HttpResponse
        html = f"""
<div class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40" onclick="document.getElementById('modal-container').innerHTML = ''"></div>
<div class="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
    <div class="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md pointer-events-auto" onclick="event.stopPropagation()">
        <div class="px-6 py-5 border-b border-slate-100 bg-slate-50 rounded-t-xl flex items-center justify-between">
            <div>
                <h3 class="text-lg font-bold text-slate-900">Observação da Linha</h3>
                <p class="text-xs text-slate-500 mt-0.5">{chip.line_number}</p>
            </div>
            <button type="button" onclick="document.getElementById('modal-container').innerHTML = ''" class="text-slate-400 hover:text-slate-600 bg-white p-1 rounded-md shadow-sm border border-slate-200">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
        </div>
        <div class="p-6">
            <p class="text-sm text-slate-700 whitespace-pre-wrap">{chip.observacao}</p>
            <button type="button" onclick="document.getElementById('modal-container').innerHTML = ''" class="mt-6 w-full py-2.5 border border-slate-300 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-50">Fechar</button>
        </div>
    </div>
</div>
        """
        return HttpResponse(html)
