"""Endpoints JSON da API externa do discador (/api/v1/discador/)."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from discador.services import DiscadorApiError, listar_ramais_api
from integracoes.api_auth import requer_token_api_externa


@require_GET
@requer_token_api_externa
def get_ramais(request):
    """GET /api/v1/discador/ramais/ — lista ramais (default: em uso) com titular e login."""
    status = (request.GET.get('status') or 'IN_USE').strip()
    slug = (request.GET.get('slug') or 'joytec').strip()
    try:
        limit = int(request.GET.get('limit') or 200)
    except (TypeError, ValueError):
        limit = 200

    try:
        payload = listar_ramais_api(status=status, slug=slug, limit=limit)
    except DiscadorApiError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=exc.status_code)
    return JsonResponse(payload)
