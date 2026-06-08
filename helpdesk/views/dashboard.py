from django.views.generic import TemplateView
from core.audit import logs_do_modulo
from core.permissions import MODULO_HELPDESK, ModuloObrigatorioMixin
from django.db.models import Count
from helpdesk.models import Ticket
from helpdesk.ticket_access import filtrar_chamados_para_usuario

class DashboardView(ModuloObrigatorioMixin, TemplateView):
    template_name = 'helpdesk/dashboard.html'
    modulo_obrigatorio = MODULO_HELPDESK
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        tickets = filtrar_chamados_para_usuario(
            Ticket.objects.filter(is_active=True),
            self.request.user,
        )
        
        context['total_tickets'] = tickets.count()
        context['total_archived'] = tickets.filter(is_archived=True).count()
        context['total_kanban_active'] = tickets.filter(is_archived=False).count()
        
        # Distribuição de status no geral
        context['status_distribution'] = tickets.values('status').annotate(total=Count('id')).order_by('-total')
        
        # Distribuição por prioridade
        context['priority_distribution'] = tickets.values('priority').annotate(total=Count('id')).order_by('-total')
        
        # Mapeamento limpo para os templates
        context['status_labels'] = dict(Ticket.StatusChoices.choices)
        context['priority_labels'] = dict(Ticket.PriorityChoices.choices)
        context['audit_logs'] = logs_do_modulo(MODULO_HELPDESK, limite=50)
        context['audit_titulo'] = 'Últimas ações do Helpdesk'
        
        return context

class DashboardMetricsPartialView(DashboardView):
    """Retorna apenas os gráficos e KPIs atualizados para injeção via HTMX SSE."""
    template_name = 'helpdesk/_dashboard_metrics.html'
