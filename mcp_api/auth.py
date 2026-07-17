"""Autenticação Bearer para a API MCP."""

import secrets
from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def requer_token_mcp(view_func):
    """Exige Authorization: Bearer <MCP_API_TOKEN>. Sem token configurado → 503."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        esperado = (getattr(settings, 'MCP_API_TOKEN', '') or '').strip()
        if not esperado:
            return JsonResponse(
                {'error': 'API MCP não configurada (MCP_API_TOKEN ausente).'},
                status=503,
            )

        auth = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION') or ''
        if not auth.startswith('Bearer '):
            return JsonResponse({'error': 'Token Bearer obrigatório.'}, status=401)

        recebido = auth[7:].strip()
        if not recebido or not secrets.compare_digest(recebido, esperado):
            return JsonResponse({'error': 'Token inválido.'}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper
