import json
import logging
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
from chips.queries import _para_data, chips_com_anotacoes_operacionais
from chips.services import entregar_chip, transferir_chip

logger = logging.getLogger(__name__)

ABAS_VALIDAS = ('chips', 'operators', 'envelopes')


def _auditoria_chips():
    """Carrega logs de auditoria; retorna lista vazia se falhar."""
    try:
        return list(logs_do_modulo(MODULO_CHIPS, limite=50))
    except Exception:
        logger.exception('Falha ao carregar auditoria de chips.')
        return []


def _listar(queryset):
    """Força avaliação do queryset durante o contexto (erros aparecem aqui, não no template)."""
    return list(queryset)


class ChipsView(ModuloObrigatorioMixin, TemplateView):
    """Página única do módulo chips com abas."""
    modulo_obrigatorio = MODULO_CHIPS
    template_name = 'chips/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self.request.GET.get('tab', 'chips')
        # Abas antigas redirecionam para chips
        if tab in ('assignment', 'inventory', 'dashboard'):
            tab = 'chips'
        if tab not in ABAS_VALIDAS:
            tab = 'chips'
        context['active_tab'] = tab
        context['schema_error'] = None

        try:
            self._contexto_dashboard(context)
            self._contexto_operadoras(context)
            self._contexto_envelopes(context)
            self._contexto_chips(context)
        except Exception as exc:
            logger.exception('Erro ao carregar módulo chips: %s', exc)
            context['schema_error'] = (
                'Não foi possível carregar os dados de chips. '
                'Verifique as migrations e os logs do servidor.'
            )
            self._contexto_fallback(context)

        return context

    def _contexto_fallback(self, context):
        """Valores mínimos para a página não quebrar."""
        context.setdefault('date_from', periodo_padrao()[0].isoformat())
        context.setdefault('date_to', periodo_padrao()[1].isoformat())
        context.setdefault('periodo_mes_atual_url', '?tab=chips')
        context.setdefault('periodo_mes_anterior_url', '?tab=chips')
        context.setdefault('total_chips', 0)
        context.setdefault('metric_available', 0)
        context.setdefault('metric_in_use', 0)
        context.setdefault('recharge_due_soon', 0)
        context.setdefault('period_deliveries', 0)
        context.setdefault('period_transfers', 0)
        context.setdefault('period_returns', 0)
        context.setdefault('period_recharges_count', 0)
        context.setdefault('period_recharges_total', 0)
        context.setdefault('period_blocks', 0)
        context.setdefault('total_recharge_value', 0)
        context.setdefault('history_logs', [])
        context.setdefault('audit_logs', [])
        context.setdefault('audit_titulo', 'Registro de auditoria de chips')
        context.setdefault('operators', [])
        context.setdefault('operators_filter', [])
        context.setdefault('batches', [])
        context.setdefault('all_batches', [])
        context.setdefault('chips', [])
        context.setdefault('chart_custodia', '{}')
        context.setdefault('chart_movimentacao', '{}')

    def _contexto_chips(self, context):
        from chips.queries import chips_com_anotacoes_operacionais, _calcular_ciclo
        chips_qs = chips_com_anotacoes_operacionais(
            Chip.objects.filter(is_active=True)
        ).order_by('-created_at')

        # Lista completa para o filtro client-side funcionar em todo o inventário
        chips_list = list(chips_qs)
        for chip in chips_list:
            due_at, days_to, status = _calcular_ciclo(chip)
            chip.recharge_due_at = due_at
            chip.days_to_recharge = days_to
            chip.recharge_status = status

        context['chips'] = chips_list

    def _contexto_dashboard(self, context):
        from django.core.paginator import Paginator
        context['total_chips'] = Chip.objects.filter(is_active=True).count()
        context['metric_available'] = Chip.objects.filter(
            usage_status=Chip.UsageChoices.AVAILABLE,
        ).count()
        context['metric_in_use'] = Chip.objects.filter(
            usage_status=Chip.UsageChoices.IN_USE,
        ).count()
        context['metric_blocked_canceled'] = Chip.objects.filter(
            status__in=[Chip.StatusChoices.BLOCKED, Chip.StatusChoices.CANCELED]
        ).count()
        context['metric_lost'] = Chip.objects.filter(
            status=Chip.StatusChoices.LOST
        ).count()

        from chips.queries import _calcular_ciclo
        vencendo = 0
        for chip in chips_com_anotacoes_operacionais(
            Chip.objects.filter(usage_status=Chip.UsageChoices.IN_USE)
        ):
            _, _, status = _calcular_ciclo(chip)
            if status in ('warning', 'danger'):
                vencendo += 1
        context['recharge_due_soon'] = vencendo

        recent_movs = ChipMovement.objects.all().select_related(
            'chip', 'chip__operator', 'registered_by', 'employee_user'
        ).order_by('-timestamp')
        
        movs_line = self.request.GET.get('movs_line', '').strip()
        if movs_line:
            recent_movs = recent_movs.filter(chip__line_number__icontains=movs_line)
            context['movs_line'] = movs_line

        movs_page = self.request.GET.get('movs_page', 1)
        paginator = Paginator(recent_movs, 15)
        context['recent_movements'] = paginator.get_page(movs_page)

    def _contexto_operadoras(self, context):
        from django.core.paginator import Paginator
        operators_qs = Operator.objects.all().order_by('name')
        operators_page = self.request.GET.get('operators_page', 1)
        paginator = Paginator(operators_qs, 15)
        context['operators'] = paginator.get_page(operators_page)
        context['operators_filter'] = list(
            Operator.objects.all().order_by('name').values('id', 'name')
        )

    def _contexto_envelopes(self, context):
        from django.core.paginator import Paginator
        batches_qs = Batch.objects.all().order_by('-received_at')
        envelopes_page = self.request.GET.get('envelopes_page', 1)
        paginator = Paginator(batches_qs, 15)
        context['batches'] = paginator.get_page(envelopes_page)
        context['all_batches'] = list(Batch.objects.all().order_by('id'))


class ChipsAssignmentPostView(ModuloObrigatorioMixin, View):
    """POST de entrega/transferência — redireciona para aba chips."""

    modulo_obrigatorio = MODULO_CHIPS

    def post(self, request):
        form = AssignmentForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Corrija os erros do formulário.')
            return redirect('/chips/?tab=chips')

        chip = get_object_or_404(Chip, id=form.cleaned_data['chip_id'])
        nome = form.cleaned_data['employee_name']
        usuario = form.cleaned_data.get('employee_user')

        try:
            if chip.usage_status == Chip.UsageChoices.IN_USE:
                transferir_chip(chip, novo_nome=nome, novo_user=usuario, actor=request.user)
                messages.success(request, f'Chip {chip.line_number} transferido para {nome}.')
            else:
                entregar_chip(chip, employee_name=nome, employee_user=usuario, actor=request.user)
                messages.success(request, f'Chip {chip.line_number} entregue para {nome}.')
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))

        return redirect('/chips/?tab=chips')


DashboardView = ChipsView
