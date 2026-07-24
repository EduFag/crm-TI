"""Endpoints MCP do discador (JoyTec) — leitura e escrita para Assistente."""

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from helpdesk.assistente_services import (
    consultar_acesso_discador,
    consultar_licencas_discador,
    criar_acesso_discador,
    liberar_acesso_discador,
    liberar_licenca_ramal,
    listar_campanhas_discador,
    listar_ramais_discador,
)
from mcp_api.auth import requer_token_mcp
from mcp_api.views.helpdesk import _json_body, _service_response


@require_GET
@requer_token_mcp
def get_licencas(request):
    slug = (request.GET.get('slug') or 'joytec').strip()
    return _service_response(consultar_licencas_discador, slug)


@require_GET
@requer_token_mcp
def get_ramais(request):
    status = (request.GET.get('status') or '').strip()
    slug = (request.GET.get('slug') or 'joytec').strip()
    try:
        limit = int(request.GET.get('limit') or 40)
    except (TypeError, ValueError):
        limit = 40
    return _service_response(listar_ramais_discador, status, slug, limit)


@require_GET
@requer_token_mcp
def get_acessos(request):
    q = (request.GET.get('q') or '').strip()
    slug = (request.GET.get('slug') or 'joytec').strip()
    return _service_response(consultar_acesso_discador, q, slug)


@require_GET
@requer_token_mcp
def get_campanhas(request):
    slug = (request.GET.get('slug') or 'joytec').strip()
    return _service_response(listar_campanhas_discador, slug)


@csrf_exempt
@require_http_methods(['POST'])
@requer_token_mcp
def post_criar_acesso(request):
    data = _json_body(request)
    return _service_response(
        criar_acesso_discador,
        data.get('titular_nome', ''),
        data.get('login_discador', ''),
        data.get('tipo') or 'CONSULTOR',
        data.get('ramal_id'),
        data.get('ramal_numero') or '',
        data.get('campanha_id'),
        data.get('campanha_nome') or '',
        data.get('slug') or 'joytec',
    )


@csrf_exempt
@require_http_methods(['POST'])
@requer_token_mcp
def post_liberar_acesso(request):
    data = _json_body(request)
    try:
        acesso_id = int(data.get('acesso_id') or 0)
    except (TypeError, ValueError):
        return _service_response(
            lambda: (_ for _ in ()).throw(
                AssistenteServiceError('acesso_id inválido.')
            )
        )
    return _service_response(liberar_acesso_discador, acesso_id)


@csrf_exempt
@require_http_methods(['POST'])
@requer_token_mcp
def post_liberar_licenca(request):
    data = _json_body(request)
    return _service_response(
        liberar_licenca_ramal,
        data.get('ramal_id'),
        data.get('ramal_numero') or '',
        data.get('slug') or 'joytec',
    )
