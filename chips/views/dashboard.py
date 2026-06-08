from django.views.generic import TemplateView
from core.audit import logs_do_modulo
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from django.db.models import Sum, Subquery, OuterRef
from chips.models import Chip, ChipMovement, Recharge

class DashboardView(ModuloObrigatorioMixin, TemplateView):
    modulo_obrigatorio = MODULO_CHIPS
    template_name = 'chips/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # RF01 - Métricas / Contadores
        context['total_chips'] = Chip.objects.count()
        context['available_chips'] = Chip.objects.filter(status=Chip.StatusChoices.AVAILABLE).count()
        context['in_use_chips'] = Chip.objects.filter(status=Chip.StatusChoices.IN_USE).count()
        context['blocked_chips'] = Chip.objects.filter(status=Chip.StatusChoices.BLOCKED).count()
        context['canceled_chips'] = Chip.objects.filter(status=Chip.StatusChoices.CANCELED).count()
        context['lost_chips'] = Chip.objects.filter(status=Chip.StatusChoices.LOST).count()
        
        recharges_total = Recharge.objects.aggregate(total=Sum('amount'))['total']
        context['total_recharge_value'] = recharges_total if recharges_total else 0.00
        
        # RF02 - Chips em Uso com última recarga
        # Usando Subquery para trazer apenas o valor e data da ÚLTIMA recarga de cada chip em uso.
        last_recharge_amount = Recharge.objects.filter(chip=OuterRef('pk')).order_by('-timestamp').values('amount')[:1]
        last_recharge_date = Recharge.objects.filter(chip=OuterRef('pk')).order_by('-timestamp').values('timestamp')[:1]
        
        in_use_qs = Chip.objects.filter(status=Chip.StatusChoices.IN_USE).select_related('operator').annotate(
            last_recharge_amount=Subquery(last_recharge_amount),
            last_recharge_date=Subquery(last_recharge_date)
        )
        
        # Para saber quem está com o chip em uso, buscamos o último movimento de entrega
        # Como é uma query para dashboard, e a relação é indireta pelo histórico, 
        # resolveremos os nomes de funcionários diretamente no template ou com anotação.
        # Aqui, vamos mapear o funcionário pela última 'DELIVERY'
        last_delivery_emp = ChipMovement.objects.filter(
            chip=OuterRef('pk'), action=ChipMovement.ActionChoices.DELIVERY
        ).order_by('-timestamp').values('employee_name')[:1]
        
        context['chips_in_use'] = in_use_qs.annotate(employee=Subquery(last_delivery_emp))
        
        # RF03 - Últimas 50 movimentações
        context['history_logs'] = ChipMovement.objects.select_related('chip').order_by('-timestamp')[:50]
        context['audit_logs'] = logs_do_modulo(MODULO_CHIPS, limite=50)
        context['audit_titulo'] = 'Registro de auditoria de chips'
        
        return context
