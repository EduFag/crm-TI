"""Autenticação da API externa (/api/v1/) via token por usuário."""

import json
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from integracoes.token_api import autenticar_username_token, resolver_user_por_bearer


def requer_token_api_externa(view_func):
    """Exige Authorization: Bearer <token> e anexa request.api_user / request.api_token."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION') or ''
        if not auth.startswith('Bearer '):
            return JsonResponse({'ok': False, 'error': 'Token Bearer obrigatório.'}, status=401)

        recebido = auth[7:].strip()
        user, token_obj, erro = resolver_user_por_bearer(recebido)
        if erro or not user:
            return JsonResponse({'ok': False, 'error': erro or 'Token inválido.'}, status=401)

        request.api_user = user
        request.api_token = token_obj
        return view_func(request, *args, **kwargs)

    return wrapper


def _json_body(request) -> dict:
    try:
        if request.body:
            return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return {k: v for k, v in request.POST.items()}


def _serializar_user(user) -> dict:
    return {
        'id': user.pk,
        'username': user.username,
        'nome': user.get_full_name() or user.username,
    }


@csrf_exempt
@require_POST
def auth(request):
    """POST /api/v1/auth/ — valida username + token."""
    data = _json_body(request)
    username = data.get('username') or ''
    token = data.get('token') or ''

    user, token_obj, erro = autenticar_username_token(username, token)
    if erro or not user:
        # Credenciais inválidas / sem permissão → 401 (403 só se quisermos distinguir)
        status = 403 if erro and 'permissão' in erro.lower() else 401
        return JsonResponse({'ok': False, 'error': erro or 'Credenciais inválidas.'}, status=status)

    return JsonResponse({
        'ok': True,
        'user': _serializar_user(user),
        'token': {
            'id': token_obj.pk,
            'nome': token_obj.nome,
            'prefixo': token_obj.prefixo,
        },
    })
