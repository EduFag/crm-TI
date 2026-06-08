from django.views.generic import ListView
from core.permissions import MODULO_HELPDESK, ModuloObrigatorioMixin
from helpdesk.models import Ticket
from helpdesk.ticket_access import filtrar_chamados_para_usuario

class HistoryListView(ModuloObrigatorioMixin, ListView):
    modulo_obrigatorio = MODULO_HELPDESK
    template_name = 'helpdesk/history.html'
    model = Ticket
    context_object_name = 'tickets'
    paginate_by = 20

    def get_queryset(self):
        qs = filtrar_chamados_para_usuario(
            super().get_queryset().filter(is_active=True),
            self.request.user,
        ).select_related('assigned_to', 'created_by', 'requester_user').order_by('-created_at')
        
        # Recupera os filtros da QueryString
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        category = self.request.GET.get('category')
        archived = self.request.GET.get('archived')
        search = self.request.GET.get('search')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if category:
            qs = qs.filter(category=category)
        if archived == 'yes':
            qs = qs.filter(is_archived=True)
        elif archived == 'no':
            qs = qs.filter(is_archived=False)
            
        if search:
            qs = qs.filter(title__icontains=search)
            
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=f"{date_to} 23:59:59")
            
        return qs
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Ticket.StatusChoices
        context['priority_choices'] = Ticket.PriorityChoices
        context['category_choices'] = Ticket.CategoryChoices
        return context
