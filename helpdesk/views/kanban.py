import json
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.http import JsonResponse
from helpdesk.models import Ticket, Comment

class KanbanView(LoginRequiredMixin, TemplateView):
    template_name = 'helpdesk/kanban.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Aplica a regra de arquivar resolvidos antigos antes de carregar o kanban
        Ticket.archive_old_resolved_tickets(days=7)
        
        # Apenas tickets ativos e NÃO arquivados no Kanban
        tickets = Ticket.objects.filter(is_active=True, is_archived=False).select_related('assigned_to')
        
        context['tickets_new'] = tickets.filter(status=Ticket.StatusChoices.NEW).order_by('-created_at')
        context['tickets_in_progress'] = tickets.filter(status=Ticket.StatusChoices.IN_PROGRESS).order_by('-created_at')
        context['tickets_pending'] = tickets.filter(status=Ticket.StatusChoices.PENDING).order_by('-created_at')
        context['tickets_resolved'] = tickets.filter(status=Ticket.StatusChoices.RESOLVED).order_by('-updated_at')
        
        return context

class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    fields = ['title', 'description', 'priority', 'category', 'requester_name']
    template_name = 'helpdesk/ticket_form.html'
    success_url = reverse_lazy('helpdesk:kanban')


@login_required
@require_POST
def ticket_update_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
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


@login_required
def ticket_drawer(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    comments = ticket.comments.filter(is_active=True).order_by('-created_at')
    return render(request, 'helpdesk/_drawer.html', {'ticket': ticket, 'comments': comments})


@login_required
@require_POST
def ticket_add_comment(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    text = request.POST.get('text', '').strip()
    if text:
        Comment.objects.create(ticket=ticket, author=request.user, text=text)
    comments = ticket.comments.filter(is_active=True).order_by('-created_at')
    return render(request, 'helpdesk/_comments_list.html', {'ticket': ticket, 'comments': comments})

class KanbanBoardPartialView(KanbanView):
    """Retorna apenas o HTML do quadro para ser injetado via HTMX no evento SSE."""
    template_name = 'helpdesk/_kanban_board.html'
