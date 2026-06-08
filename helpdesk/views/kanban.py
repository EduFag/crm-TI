import json
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, CreateView
from core.permissions import MODULO_HELPDESK, ModuloObrigatorioMixin, requer_modulo
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden, JsonResponse
from helpdesk.models import Ticket, Comment
from helpdesk.ticket_access import filtrar_chamados_para_usuario, usuario_pode_acessar_chamado

class KanbanView(ModuloObrigatorioMixin, TemplateView):
    template_name = 'helpdesk/kanban.html'
    modulo_obrigatorio = MODULO_HELPDESK

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Aplica a regra de arquivar resolvidos antigos antes de carregar o kanban
        Ticket.archive_old_resolved_tickets(days=7)
        
        # Apenas tickets ativos e NÃO arquivados no Kanban
        tickets = filtrar_chamados_para_usuario(
            Ticket.objects.filter(is_active=True, is_archived=False),
            self.request.user,
        ).select_related('assigned_to', 'created_by')
        
        context['tickets_new'] = tickets.filter(status=Ticket.StatusChoices.NEW).order_by('-created_at')
        context['tickets_in_progress'] = tickets.filter(status=Ticket.StatusChoices.IN_PROGRESS).order_by('-created_at')
        context['tickets_pending'] = tickets.filter(status=Ticket.StatusChoices.PENDING).order_by('-created_at')
        context['tickets_resolved'] = tickets.filter(status=Ticket.StatusChoices.RESOLVED).order_by('-updated_at')
        
        return context

class TicketCreateView(ModuloObrigatorioMixin, CreateView):
    modulo_obrigatorio = MODULO_HELPDESK
    model = Ticket
    fields = ['title', 'description', 'priority', 'category', 'requester_name']
    template_name = 'helpdesk/ticket_form.html'
    success_url = reverse_lazy('helpdesk:kanban')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nome_solicitante_padrao'] = (
            self.request.user.get_full_name() or self.request.user.username
        )
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if not form.instance.requester_name.strip():
            form.instance.requester_name = (
                self.request.user.get_full_name() or self.request.user.username
            )
        return super().form_valid(form)


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_update_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
    except json.JSONDecodeError:
        new_status = request.POST.get('status')

    if new_status in dict(Ticket.StatusChoices.choices):
        ticket.status = new_status
        if not ticket.assigned_to and new_status != Ticket.StatusChoices.NEW:
            ticket.assigned_to = request.user
            Comment.objects.create(
                ticket=ticket,
                author=request.user,
                text=f'Chamado atribuído automaticamente a {request.user.username} (movimentado para {ticket.get_status_display()}).'
            )
        ticket.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Status inválido'}, status=400)


@requer_modulo(MODULO_HELPDESK)
def ticket_drawer(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão para acessar este chamado.')
    comments = ticket.comments.filter(is_active=True).order_by('-created_at')
    return render(request, 'helpdesk/_drawer.html', {'ticket': ticket, 'comments': comments})


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_add_comment(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão para comentar neste chamado.')
    text = request.POST.get('text', '').strip()
    if text:
        Comment.objects.create(ticket=ticket, author=request.user, text=text)
    comments = ticket.comments.filter(is_active=True).order_by('-created_at')
    return render(request, 'helpdesk/_comments_list.html', {'ticket': ticket, 'comments': comments})

class KanbanBoardPartialView(KanbanView):
    """Retorna apenas o HTML do quadro para ser injetado via HTMX no evento SSE."""
    template_name = 'helpdesk/_kanban_board.html'
