"""Endpoints MCP MoneyConsig — proxy para a API B2B cadastrada em Integrações → APIs."""

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from helpdesk.assistente_services import (
    moneyconsig_alerta_ti_criar,
    moneyconsig_alerta_ti_destinatarios,
    moneyconsig_alerta_ti_listar,
    moneyconsig_auth_me,
    moneyconsig_usuario_consultar,
)
from mcp_api.auth import requer_token_mcp
from mcp_api.views.helpdesk import _json_body, _service_response


@require_GET
@requer_token_mcp
def get_auth_me(request):
    return _service_response(moneyconsig_auth_me)


@require_GET
@requer_token_mcp
def get_usuarios_consulta(request):
    username = (request.GET.get('username') or '').strip()
    q = (request.GET.get('q') or '').strip()
    return _service_response(moneyconsig_usuario_consultar, username=username, q=q)


@require_GET
@requer_token_mcp
def get_alerta_ti(request):
    try:
        limite = int(request.GET.get('limite') or 50)
    except (TypeError, ValueError):
        limite = 50
    return _service_response(moneyconsig_alerta_ti_listar, limite=limite)


@csrf_exempt
@require_http_methods(['POST'])
@requer_token_mcp
def post_alerta_ti(request):
    data = _json_body(request)
    ids = data.get('destinatarios_ids') or []
    if not isinstance(ids, list):
        ids = []
    return _service_response(
        moneyconsig_alerta_ti_criar,
        mensagem=data.get('mensagem', ''),
        tipo_destinatario=data.get('tipo_destinatario', ''),
        destinatarios_ids=ids,
    )


@require_GET
@requer_token_mcp
def get_alerta_ti_destinatarios(request, tipo: str):
    return _service_response(
        moneyconsig_alerta_ti_destinatarios,
        tipo=tipo,
        empresas=(request.GET.get('empresas') or '').strip(),
        departamentos=(request.GET.get('departamentos') or '').strip(),
        setores=(request.GET.get('setores') or '').strip(),
        cargos=(request.GET.get('cargos') or '').strip(),
    )
