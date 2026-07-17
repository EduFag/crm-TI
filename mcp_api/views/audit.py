from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET

from core.models import RegistroAcao
from mcp_api.auth import requer_token_mcp
from mcp_api.serializers import parse_limit, serialize_acao


@require_GET
@requer_token_mcp
def list_acoes(request):
    qs = RegistroAcao.objects.select_related('actor', 'content_type').order_by('-timestamp')

    modulo = (request.GET.get('modulo') or '').strip()
    if modulo:
        qs = qs.filter(modulo=modulo)

    acao = (request.GET.get('acao') or '').strip()
    if acao:
        qs = qs.filter(acao=acao)

    actor = (request.GET.get('actor') or '').strip()
    if actor:
        if actor.isdigit():
            qs = qs.filter(actor_id=int(actor))
        else:
            qs = qs.filter(actor__username__iexact=actor)

    q = (request.GET.get('q') or '').strip()
    if q:
        filtro = Q(descricao__icontains=q) | Q(object_repr__icontains=q)
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)

    limit = parse_limit(request)
    itens = [serialize_acao(a) for a in qs[:limit]]
    return JsonResponse({'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def get_acao(request, pk):
    reg = get_object_or_404(
        RegistroAcao.objects.select_related('actor', 'content_type'),
        pk=pk,
    )
    return JsonResponse(serialize_acao(reg))


@require_GET
@requer_token_mcp
def sistema_status(request):
    """Health mínimo para o agente MCP."""
    return JsonResponse({
        'ok': True,
        'sistema_url': getattr(settings, 'SISTEMA_URL_PUBLICA', ''),
        'timestamp': timezone.now().isoformat(),
        'debug': settings.DEBUG,
        'modulos_api': [
            'helpdesk', 'chips', 'equipment', 'emails', 'users', 'audit',
        ],
    })
