import csv
import io

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView

from core.permissions import MODULO_HELPDESK, ModuloObrigatorioMixin, resposta_sem_permissao
from helpdesk.models import Ticket, TicketCategory
from helpdesk.ticket_access import filtrar_chamados_para_usuario, usuario_pode_acessar_dashboard_e_historico

COLUNAS_CSV_HISTORICO = [
    'ID',
    'Título',
    'Descrição',
    'Solicitante',
    'Usuário solicitante',
    'Categoria',
    'Categoria específica',
    'Status',
    'Prioridade',
    'Técnico',
    'Equipe',
    'Criado por',
    'Arquivado',
    'Recusado',
    'Motivo recusa',
    'Criado em',
    'Atualizado em',
    'Resolvido em',
]


def _nome_usuario(user):
    if not user:
        return ''
    return user.get_full_name() or user.username


def _formatar_data(dt):
    if not dt:
        return ''
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return dt.strftime('%d/%m/%Y %H:%M')


def queryset_historico_base(user):
    return filtrar_chamados_para_usuario(
        Ticket.objects.filter(is_active=True),
        user,
    ).select_related(
        'assigned_to',
        'created_by',
        'requester_user',
        'category',
        'specific_category',
        'equipe',
    ).order_by('-created_at')


def aplicar_filtros_historico(queryset, request):
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    category = request.GET.get('category')
    archived = request.GET.get('archived')
    search = request.GET.get('search')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if status:
        queryset = queryset.filter(status=status)
    if priority == '__null__':
        queryset = queryset.filter(priority__isnull=True)
    elif priority:
        queryset = queryset.filter(priority=priority)
    if category:
        queryset = queryset.filter(category_id=category)
    if archived == 'yes':
        queryset = queryset.filter(is_archived=True)
    elif archived == 'no':
        queryset = queryset.filter(is_archived=False)
    if search:
        queryset = queryset.filter(title__icontains=search)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__lte=f"{date_to} 23:59:59")

    return queryset


def _linha_csv_ticket(ticket):
    return {
        'ID': ticket.id,
        'Título': ticket.title,
        'Descrição': ticket.description,
        'Solicitante': ticket.requester_name,
        'Usuário solicitante': _nome_usuario(ticket.requester_user),
        'Categoria': ticket.category.name if ticket.category_id else '',
        'Categoria específica': ticket.specific_category.name if ticket.specific_category_id else '',
        'Status': ticket.get_status_display(),
        'Prioridade': ticket.get_priority_display() if ticket.priority else '',
        'Técnico': _nome_usuario(ticket.assigned_to),
        'Equipe': ticket.equipe.name if ticket.equipe_id else '',
        'Criado por': _nome_usuario(ticket.created_by),
        'Arquivado': 'Sim' if ticket.is_archived else 'Não',
        'Recusado': 'Sim' if ticket.is_rejected else 'Não',
        'Motivo recusa': ticket.rejection_reason or '',
        'Criado em': _formatar_data(ticket.created_at),
        'Atualizado em': _formatar_data(ticket.updated_at),
        'Resolvido em': _formatar_data(ticket.resolved_at),
    }


def gerar_csv_historico(tickets):
    buffer = io.StringIO()
    buffer.write('\ufeff')
    writer = csv.DictWriter(buffer, fieldnames=COLUNAS_CSV_HISTORICO, delimiter=';')
    writer.writeheader()
    for ticket in tickets:
        writer.writerow(_linha_csv_ticket(ticket))
    return buffer.getvalue()


class HistoryListView(ModuloObrigatorioMixin, ListView):
    modulo_obrigatorio = MODULO_HELPDESK
    template_name = 'helpdesk/history.html'
    model = Ticket
    context_object_name = 'tickets'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not usuario_pode_acessar_dashboard_e_historico(request.user):
            return resposta_sem_permissao(request)
        Ticket.archive_old_tickets()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = queryset_historico_base(self.request.user)
        return aplicar_filtros_historico(qs, self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Ticket.StatusChoices
        context['priority_choices'] = Ticket.PriorityChoices
        context['categorias'] = TicketCategory.objects.filter(is_active=True).order_by('name')
        return context


@login_required
def history_export_csv(request):
    if not usuario_pode_acessar_dashboard_e_historico(request.user):
        return resposta_sem_permissao(request)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if not date_from or not date_to:
        params = request.GET.copy()
        params['erro'] = 'export_periodo'
        return redirect(f"{reverse('helpdesk:history')}?{params.urlencode()}")

    qs = aplicar_filtros_historico(queryset_historico_base(request.user), request)
    conteudo = gerar_csv_historico(qs)

    response = HttpResponse(conteudo, content_type='text/csv; charset=utf-8')
    filename = f'chamados_{date_from}_{date_to}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
