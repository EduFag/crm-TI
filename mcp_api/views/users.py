from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from core.models import CustomUser, Equipe
from mcp_api.auth import requer_token_mcp
from mcp_api.serializers import (
    filtro_q_usuario,
    parse_limit,
    serialize_equipe,
    serialize_user,
)


@require_GET
@requer_token_mcp
def list_users(request):
    qs = CustomUser.objects.prefetch_related('equipes').order_by('username')

    role = (request.GET.get('role') or '').strip()
    if role:
        qs = qs.filter(role=role)

    active = (request.GET.get('active') or '').strip().lower()
    if active in ('1', 'true'):
        qs = qs.filter(is_active=True)
    elif active in ('0', 'false'):
        qs = qs.filter(is_active=False)

    equipe = (request.GET.get('equipe') or '').strip()
    if equipe:
        if equipe.isdigit():
            qs = qs.filter(equipes__pk=int(equipe))
        else:
            qs = qs.filter(equipes__name__icontains=equipe)

    qs = filtro_q_usuario(qs, (request.GET.get('q') or '').strip()).distinct()
    limit = parse_limit(request)
    itens = [serialize_user(u) for u in qs[:limit]]
    return JsonResponse({'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def get_user(request, pk):
    user = get_object_or_404(CustomUser.objects.prefetch_related('equipes'), pk=pk)
    return JsonResponse(serialize_user(user))


@require_GET
@requer_token_mcp
def lookup_user_by_username(request, username):
    user = CustomUser.objects.prefetch_related('equipes').filter(username__iexact=username).first()
    if not user:
        return JsonResponse({'error': 'Usuário não encontrado.'}, status=404)
    return JsonResponse(serialize_user(user))


@require_GET
@requer_token_mcp
def list_equipes(request):
    qs = Equipe.objects.all().order_by('name')
    active = (request.GET.get('active') or '').strip().lower()
    if active in ('1', 'true'):
        qs = qs.filter(is_active=True)
    elif active in ('0', 'false'):
        qs = qs.filter(is_active=False)
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(name__icontains=q)
    limit = parse_limit(request)
    itens = [serialize_equipe(e) for e in qs[:limit]]
    return JsonResponse({'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def list_equipe_membros(request, pk):
    equipe = get_object_or_404(Equipe, pk=pk)
    qs = equipe.membros.prefetch_related('equipes').order_by('username')
    limit = parse_limit(request)
    itens = [serialize_user(u) for u in qs[:limit]]
    return JsonResponse({
        'equipe': serialize_equipe(equipe),
        'count': len(itens),
        'results': itens,
    })
