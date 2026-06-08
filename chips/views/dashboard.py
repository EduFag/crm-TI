from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView, View

from core.audit import logs_do_modulo
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.forms import AssignmentForm
from chips.models import Batch, Chip, ChipMovement, Operator, Recharge
from chips.period import periodo_mes_anterior, periodo_padrao, resolver_periodo
from chips.queries import chips_com_anotacoes_operacionais
from chips.services import devolver_para_ti, entregar_chip, transferir_chip

ABAS_VALIDAS = ('dashboard', 'assignment', 'inventory', 'operators', 'envelopes')


class ChipsView(ModuloObrigatorioMixin, TemplateView):
    """Página única do módulo chips com abas."""
    modulo_obrigatorio = MODULO_CHIPS
    template_name = 'chips/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self.request.GET.get('tab', 'dashboard')
        if tab not in ABAS_VALIDAS:
            tab = 'dashboard'
        context['active_tab'] = tab

        self._contexto_dashboard(context)
        self._contexto_assignment(context)
        self._contexto_inventario(context)
        self._contexto_operadoras(context)
        self._contexto_envelopes(context)
        return context

    def _contexto_dashboard(self, context):
        date_from, date_to = resolver_periodo(self.request)
        context['date_from'] = date_from.isoformat()
        context['date_to'] = date_to.isoformat()

        padrao_inicio, padrao_fim = periodo_padrao()
        mes_ant_inicio, mes_ant_fim = periodo_mes_anterior()
        context['periodo_mes_atual_url'] = (
            f'?tab=dashboard&date_from={padrao_inicio.isoformat()}&date_to={padrao_fim.isoformat()}'
        )
        context['periodo_mes_anterior_url'] = (
            f'?tab=dashboard&date_from={mes_ant_inicio.isoformat()}&date_to={mes_ant_fim.isoformat()}'
        )

        context['total_chips'] = Chip.objects.filter(is_active=True).count()
        context['available_chips'] = Chip.objects.filter(
            custody=Chip.CustodyChoices.WITH_TI,
            status=Chip.StatusChoices.AVAILABLE,
        ).count()
        context['in_use_chips'] = Chip.objects.filter(
            custody=Chip.CustodyChoices.WITH_PERSON,
        ).count()
        context['blocked_chips'] = Chip.objects.filter(status=Chip.StatusChoices.BLOCKED).count()
        context['canceled_chips'] = Chip.objects.filter(status=Chip.StatusChoices.CANCELED).count()
        context['lost_chips'] = Chip.objects.filter(status=Chip.StatusChoices.LOST).count()

        movs = ChipMovement.objects.filter(
            timestamp__date__gte=date_from,
            timestamp__date__lte=date_to,
        )
        context['period_deliveries'] = movs.filter(
            action=ChipMovement.ActionChoices.DELIVERY,
        ).count()
        context['period_transfers'] = movs.filter(
            action=ChipMovement.ActionChoices.TRANSFER,
        ).count()
        context['period_returns'] = movs.filter(
            action=ChipMovement.ActionChoices.RETURN,
        ).count()

        recargas_periodo = Recharge.objects.filter(
            timestamp__date__gte=date_from,
            timestamp__date__lte=date_to,
        )
        agg = recargas_periodo.aggregate(qtd=Count('id'), total=Sum('amount'))
        context['period_recharges_count'] = agg['qtd'] or 0
        context['period_recharges_total'] = agg['total'] or 0

        context['period_blocks'] = Chip.objects.filter(
            last_blocked_at__date__gte=date_from,
            last_blocked_at__date__lte=date_to,
        ).count()

        hoje = timezone.localdate()
        limite = hoje + timedelta(days=30)
        vencendo = 0
        for chip in chips_com_anotacoes_operacionais(
            Chip.objects.filter(custody=Chip.CustodyChoices.WITH_PERSON)
        ):
            cycle_start = None
            if chip.last_recharge_at:
                cycle_start = timezone.localtime(chip.last_recharge_at).date()
            elif chip.activated_at:
                cycle_start = chip.activated_at
            if cycle_start and cycle_start + timedelta(days=90) <= limite:
                vencendo += 1
        context['recharge_due_soon'] = vencendo

        recharges_total = Recharge.objects.aggregate(total=Sum('amount'))['total']
        context['total_recharge_value'] = recharges_total if recharges_total else 0.00

        context['history_logs'] = ChipMovement.objects.select_related('chip').filter(
            timestamp__date__gte=date_from,
            timestamp__date__lte=date_to,
        ).order_by('-timestamp')[:100]

        context['audit_logs'] = logs_do_modulo(MODULO_CHIPS, limite=50)
        context['audit_titulo'] = 'Registro de auditoria de chips'

    def _contexto_assignment(self, context):
        context['available_chips'] = Chip.objects.filter(
            status=Chip.StatusChoices.AVAILABLE,
            custody=Chip.CustodyChoices.WITH_TI,
        ).select_related('operator')
        context['in_use_chips'] = Chip.objects.filter(
            custody=Chip.CustodyChoices.WITH_PERSON,
        ).select_related('operator')
        context['assignment_form'] = AssignmentForm()

    def _contexto_inventario(self, context):
        context['chips'] = Chip.objects.select_related('operator', 'batch').order_by('-created_at')
        context['envelopes'] = Batch.objects.filter(
            tipo=Batch.TipoChoices.ENVELOPE,
            status=Batch.StatusChoices.OPEN,
        ).order_by('identifier')

    def _contexto_operadoras(self, context):
        context['operators'] = Operator.objects.all().order_by('name')

    def _contexto_envelopes(self, context):
        context['batches'] = Batch.objects.all().order_by('-received_at')


class ChipsAssignmentPostView(ModuloObrigatorioMixin, View):
    """POST de entrega/transferência — redireciona para aba assignment."""

    modulo_obrigatorio = MODULO_CHIPS

    def post(self, request):
        form = AssignmentForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Corrija os erros do formulário.')
            return redirect('/chips/?tab=assignment')

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

        return redirect('/chips/?tab=assignment')


# Alias para compatibilidade com urls e imports existentes
DashboardView = ChipsView
