"""Cliente HTTP OpenAI-compatible (DeepSeek e similares)."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urljoin

import httpx

from integracoes.models import AssistenteConfig, IntegracaoIA

logger = logging.getLogger(__name__)


class LlmError(Exception):
    pass


def obter_integracao_ativa() -> IntegracaoIA | None:
    config = AssistenteConfig.get_solo()
    if config.integracao_id and config.integracao and config.integracao.is_active:
        return config.integracao
    return (
        IntegracaoIA.objects.filter(is_active=True, provider=IntegracaoIA.Provider.DEEPSEEK)
        .order_by('-updated_at')
        .first()
        or IntegracaoIA.objects.filter(is_active=True).order_by('-updated_at').first()
    )


def _resolver_endpoint_e_modelo(integracao: IntegracaoIA) -> tuple[str, str, str]:
    creds = integracao.get_credentials()
    api_key = (creds.get('api_key') or '').strip()
    if not api_key:
        raise LlmError('Integração sem api_key.')
    base_url = (creds.get('base_url') or '').strip().rstrip('/')
    if not base_url:
        from integracoes.providers import base_url_do_provedor
        base_url = (base_url_do_provedor(integracao.provider) or '').rstrip('/')
    if not base_url:
        raise LlmError('Integração sem base_url.')
    models = creds.get('models') or []
    model = models[0] if models else 'deepseek-chat'
    return api_key, base_url, model


def chat_completion(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict] | None = None,
    temperature: float = 0.4,
    timeout: float = 45.0,
) -> dict[str, Any]:
    """
    Chama /chat/completions. Retorna o objeto message da choice[0]
    (content + tool_calls possíveis).
    """
    integracao = obter_integracao_ativa()
    if not integracao:
        raise LlmError('Nenhuma integração IA ativa.')

    api_key, base_url, model = _resolver_endpoint_e_modelo(integracao)
    url = urljoin(base_url + '/', 'chat/completions')
    payload: dict[str, Any] = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
    }
    if tools:
        payload['tools'] = tools
        payload['tool_choice'] = 'auto'

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        logger.exception('Falha de rede no LLM')
        raise LlmError(f'Falha de rede: {exc}') from exc

    if resp.status_code >= 400:
        logger.error('LLM HTTP %s: %s', resp.status_code, resp.text[:500])
        raise LlmError(f'LLM retornou HTTP {resp.status_code}')

    data = resp.json()
    try:
        return data['choices'][0]['message']
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmError('Resposta LLM inválida.') from exc


def chat_text(messages: list[dict[str, Any]], **kwargs) -> str:
    msg = chat_completion(messages, tools=None, **kwargs)
    return (msg.get('content') or '').strip()
