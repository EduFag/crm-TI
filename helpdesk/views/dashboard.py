from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from helpdesk.models import Ticket

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'helpdesk/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Analisando TODOS os tickets (arquivados e ativos)
        tickets = Ticket.objects.filter(is_active=True)
        
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
        
        return context

class DashboardMetricsPartialView(DashboardView):
    """Retorna apenas os gráficos e KPIs atualizados para injeção via HTMX SSE."""
    template_name = 'helpdesk/_dashboard_metrics.html'
