from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from core.audit import logs_do_modulo
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.models import Chip, ChipMovement, Recharge
from chips.period import periodo_mes_anterior, periodo_padrao, resolver_periodo
from chips.queries import chips_com_anotacoes_operacionais


class DashboardView(ModuloObrigatorioMixin, TemplateView):
    modulo_obrigatorio = MODULO_CHIPS
    template_name = 'chips/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_from, date_to = resolver_periodo(self.request)
        context['date_from'] = date_from.isoformat()
        context['date_to'] = date_to.isoformat()

        padrao_inicio, padrao_fim = periodo_padrao()
        mes_ant_inicio, mes_ant_fim = periodo_mes_anterior()
        context['periodo_mes_atual_url'] = (
            f'?date_from={padrao_inicio.isoformat()}&date_to={padrao_fim.isoformat()}'
        )
        context['periodo_mes_anterior_url'] = (
            f'?date_from={mes_ant_inicio.isoformat()}&date_to={mes_ant_fim.isoformat()}'
        )

        # Snapshot operacional (estado atual)
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

        # Métricas do período
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

        # Chips vencendo em 30 dias (estado atual)
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
            if cycle_start:
                due = cycle_start + timedelta(days=90)
                if due <= limite:
                    vencendo += 1
        context['recharge_due_soon'] = vencendo

        recharges_total = Recharge.objects.aggregate(total=Sum('amount'))['total']
        context['total_recharge_value'] = recharges_total if recharges_total else 0.00

        # Histórico no período
        context['history_logs'] = ChipMovement.objects.select_related('chip').filter(
            timestamp__date__gte=date_from,
            timestamp__date__lte=date_to,
        ).order_by('-timestamp')[:100]

        context['audit_logs'] = logs_do_modulo(MODULO_CHIPS, limite=50)
        context['audit_titulo'] = 'Registro de auditoria de chips'

        return context
