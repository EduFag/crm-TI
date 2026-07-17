from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from helpdesk.models import Comment, Ticket
from mcp_api.auth import requer_token_mcp
from mcp_api.serializers import parse_limit, serialize_comment, serialize_ticket


@require_GET
@requer_token_mcp
def list_tickets(request):
    qs = Ticket.objects.select_related(
        'category', 'specific_category', 'equipe',
        'requester_user', 'created_by', 'assigned_to',
    ).order_by('-updated_at')

    status = (request.GET.get('status') or '').strip()
    if status:
        qs = qs.filter(status=status)

    archived = (request.GET.get('archived') or '').strip().lower()
    if archived == '1' or archived == 'true':
        qs = qs.filter(is_archived=True)
    elif archived == '0' or archived == 'false':
        qs = qs.filter(is_archived=False)

    active = (request.GET.get('active') or '').strip().lower()
    if active in ('1', 'true'):
        qs = qs.filter(is_active=True)
    elif active in ('0', 'false'):
        qs = qs.filter(is_active=False)

    assignee = (request.GET.get('assigned_to') or '').strip()
    if assignee:
        if assignee.isdigit():
            qs = qs.filter(assigned_to_id=int(assignee))
        else:
            qs = qs.filter(assigned_to__username__iexact=assignee)

    q = (request.GET.get('q') or '').strip()
    if q:
        filtro = Q(title__icontains=q) | Q(description__icontains=q) | Q(requester_name__icontains=q)
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)

    limit = parse_limit(request)
    itens = [serialize_ticket(t) for t in qs[:limit]]
    return JsonResponse({'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def get_ticket(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            'category', 'specific_category', 'equipe',
            'requester_user', 'created_by', 'assigned_to', 'resolved_by',
        ),
        pk=pk,
    )
    return JsonResponse(serialize_ticket(ticket, detalhe=True))


@require_GET
@requer_token_mcp
def list_ticket_comments(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    qs = (
        Comment.objects.filter(ticket=ticket, is_active=True)
        .select_related('author')
        .order_by('created_at')
    )
    limit = parse_limit(request, default=50)
    itens = [serialize_comment(c) for c in qs[:limit]]
    return JsonResponse({'ticket_id': ticket.pk, 'count': len(itens), 'results': itens})
