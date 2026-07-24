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
    if models:
        model = models[0]
    elif integracao.provider == IntegracaoIA.Provider.DEEPSEEK:
        model = 'deepseek-v4-flash'
    else:
        model = 'deepseek-chat'
    return api_key, base_url, model


def _resolver_modelo_visao(integracao: IntegracaoIA) -> tuple[str, str, str]:
    """Prefere modelo com visão (vl/vision/v4); DeepSeek → v4-flash se só houver alias legado."""
    api_key, base_url, model_texto = _resolver_endpoint_e_modelo(integracao)
    creds = integracao.get_credentials()
    models = [str(m).strip() for m in (creds.get('models') or []) if str(m).strip()]

    for m in models:
        low = m.lower()
        if any(x in low for x in ('vl', 'vision', 'v4', 'gpt-4o', 'gemini')):
            return api_key, base_url, m

    if integracao.provider == IntegracaoIA.Provider.DEEPSEEK:
        # Alias legado deepseek-chat/reasoner: visão estável em v4-flash
        return api_key, base_url, 'deepseek-v4-flash'

    if len(models) > 1:
        return api_key, base_url, models[1]
    return api_key, base_url, model_texto or (models[0] if models else 'gpt-4o-mini')


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
    # DeepSeek: aliases antigos ainda funcionam, mas v4 é o padrão atual
    if integracao.provider == IntegracaoIA.Provider.DEEPSEEK and model in (
        'deepseek-chat', 'deepseek-reasoner',
    ):
        # Mantém alias se configurado; visão usa _resolver_modelo_visao
        pass
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


def chat_completion_vision(
    prompt: str,
    image_bytes: bytes,
    mime: str = 'image/jpeg',
    *,
    timeout: float = 90.0,
) -> str:
    """
    Descreve uma imagem via content multimodal (OpenAI-compatible).
    Preferir JPEG; imagem antes do texto no content (melhor compatibilidade).
    """
    import base64

    integracao = obter_integracao_ativa()
    if not integracao:
        raise LlmError('Nenhuma integração IA ativa.')

    if not image_bytes:
        raise LlmError('Imagem vazia.')
    if len(image_bytes) > 5 * 1024 * 1024:
        raise LlmError('Imagem maior que 5MB.')

    mime = (mime or 'image/jpeg').split(';')[0].strip().lower() or 'image/jpeg'
    # Aceita octet-stream só se já normalizado como jpeg no caller; força jpeg
    if mime == 'application/octet-stream':
        mime = 'image/jpeg'
    if not mime.startswith('image/'):
        raise LlmError(f'Arquivo não é imagem (mime={mime}).')

    api_key, base_url, model = _resolver_modelo_visao(integracao)
    b64 = base64.b64encode(image_bytes).decode('ascii')
    data_url = f'data:{mime};base64,{b64}'

    url = urljoin(base_url + '/', 'chat/completions')
    # Imagem antes do texto — alguns provedores preferem essa ordem
    payload = {
        'model': model,
        'temperature': 0.2,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': data_url}},
                    {'type': 'text', 'text': (prompt or '').strip() or 'Descreva a imagem.'},
                ],
            }
        ],
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    logger.info('LLM visão model=%s mime=%s bytes=%s', model, mime, len(image_bytes))
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        logger.exception('Falha de rede no LLM visão')
        raise LlmError(f'Falha de rede (visão): {exc}') from exc

    if resp.status_code >= 400:
        logger.error('LLM visão HTTP %s model=%s: %s', resp.status_code, model, resp.text[:800])
        raise LlmError(
            f'Visão indisponível (HTTP {resp.status_code}, modelo {model}). '
            'Use um modelo multimodal (ex.: deepseek-v4-flash / gpt-4o) na integração IA.'
        )

    data = resp.json()
    try:
        content = data['choices'][0]['message'].get('content') or ''
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmError('Resposta de visão inválida.') from exc
    texto = content.strip() if isinstance(content, str) else str(content)
    if not texto:
        raise LlmError('Modelo de visão retornou descrição vazia.')
    return texto
