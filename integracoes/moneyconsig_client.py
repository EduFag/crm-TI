"""Cliente HTTP da API B2B MoneyConsig."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import requests

from integracoes.models import IntegracaoApi

logger = logging.getLogger(__name__)

TIMEOUT = 30
DEFAULT_BASE = 'https://sistema.moneypromotora.com.br'


def normalizar_base_url(url: str) -> str:
    """Garante scheme https:// e remove barra final.

    Aceita host sem scheme (ex.: sistema.moneypromotora.com.br).
    """
    base = (url or '').strip().rstrip('/')
    if not base:
        return DEFAULT_BASE
    low = base.lower()
    if low.startswith('http://') or low.startswith('https://'):
        return base
    # Host sem scheme → assume HTTPS
    return f'https://{base}'


def obter_integracao_moneyconsig() -> IntegracaoApi | None:
    """Retorna a primeira integração MoneyConsig ativa."""
    return (
        IntegracaoApi.objects.filter(
            provider=IntegracaoApi.Provider.MONEYCONSIG,
            is_active=True,
        )
        .order_by('name')
        .first()
    )


def moneyconsig_disponivel() -> bool:
    return obter_integracao_moneyconsig() is not None


def _erro(mensagem: str, **extra: Any) -> dict:
    return {'ok': False, 'erro': mensagem, **extra}


def _resolver_creds() -> tuple[str, str] | dict:
    """Devolve (base_url, api_token) ou dict de erro."""
    integracao = obter_integracao_moneyconsig()
    if not integracao:
        return _erro(
            'Nenhuma integração MoneyConsig ativa. '
            'Cadastre em Integrações → APIs.',
        )
    creds = integracao.get_credentials()
    token = (creds.get('api_token') or '').strip()
    if not token:
        return _erro('Token MoneyConsig ausente na integração cadastrada.')
    base = normalizar_base_url(creds.get('base_url') or DEFAULT_BASE)
    return base, token


def _headers(token: str) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }


def _request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict:
    resolved = _resolver_creds()
    if isinstance(resolved, dict):
        return resolved
    base, token = resolved
    url = urljoin(base + '/', path.lstrip('/'))
    try:
        resp = requests.request(
            method,
            url,
            headers=_headers(token),
            params=params or None,
            json=json_body,
            timeout=TIMEOUT,
        )
    except requests.Timeout:
        logger.warning('MoneyConsig timeout: %s %s', method, path)
        return _erro('Timeout ao chamar a API MoneyConsig.')
    except requests.RequestException as exc:
        logger.warning('MoneyConsig rede: %s %s — %s', method, path, exc)
        return _erro(f'Falha de rede na API MoneyConsig: {exc}')

    if resp.status_code == 401:
        return _erro('Token MoneyConsig inválido ou sem permissão B2B (HTTP 401).', http_status=401)

    try:
        data = resp.json()
    except ValueError:
        return _erro(
            f'Resposta não-JSON da API MoneyConsig (HTTP {resp.status_code}).',
            http_status=resp.status_code,
        )

    if resp.status_code >= 400:
        msg = data.get('detail') or data.get('erro') or data.get('message') or resp.reason
        return _erro(str(msg), http_status=resp.status_code, resposta=data)

    if isinstance(data, dict):
        return {'ok': True, **data}
    return {'ok': True, 'data': data}


def auth_me() -> dict:
    """Valida o token e retorna identidade + escopo."""
    return _request('GET', '/api/b2b/auth/me/')


def usuarios_consulta(*, username: str = '', q: str = '') -> dict:
    """Consulta User/Funcionario no MoneyConsig (username e/ou q)."""
    username = (username or '').strip()
    q = (q or '').strip()
    if not username and not q:
        return _erro('Informe username e/ou q para consultar usuário.')
    params: dict[str, str] = {}
    if username:
        params['username'] = username
    if q:
        params['q'] = q
    return _request('GET', '/api/b2b/usuarios/consulta/', params=params)


def alerta_ti_listar(*, limite: int = 50) -> dict:
    """Lista alertas TI do escopo do token."""
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        limite = 50
    limite = max(1, min(100, limite))
    return _request('GET', '/api/b2b/alerta-ti/', params={'limite': limite})


def alerta_ti_criar(
    *,
    mensagem: str,
    tipo_destinatario: str,
    destinatarios_ids: list[int] | None = None,
) -> dict:
    """Cria alerta TI no MoneyConsig."""
    mensagem = (mensagem or '').strip()
    tipo_destinatario = (tipo_destinatario or '').strip()
    if not mensagem:
        return _erro('Informe a mensagem do alerta.')
    if not tipo_destinatario:
        return _erro('Informe tipo_destinatario.')
    ids = destinatarios_ids or []
    if not isinstance(ids, list) or not ids:
        return _erro('Informe destinatarios_ids (lista de inteiros).')
    try:
        ids_int = [int(x) for x in ids]
    except (TypeError, ValueError):
        return _erro('destinatarios_ids deve ser lista de inteiros.')
    return _request(
        'POST',
        '/api/b2b/alerta-ti/',
        json_body={
            'mensagem': mensagem,
            'tipo_destinatario': tipo_destinatario,
            'destinatarios_ids': ids_int,
        },
    )


def alerta_ti_destinatarios(
    tipo: str,
    *,
    empresas: str = '',
    departamentos: str = '',
    setores: str = '',
    cargos: str = '',
) -> dict:
    """Cascata de destinatários filtrada por escopo."""
    tipo = (tipo or '').strip().lower()
    permitidos = {
        'funcionarios', 'empresas', 'departamentos',
        'setores', 'lojas', 'equipes', 'cargos',
    }
    if tipo not in permitidos:
        return _erro(
            f'tipo inválido. Use um de: {", ".join(sorted(permitidos))}.',
        )
    params: dict[str, str] = {}
    for key, val in (
        ('empresas', empresas),
        ('departamentos', departamentos),
        ('setores', setores),
        ('cargos', cargos),
    ):
        val = (val or '').strip()
        if val:
            params[key] = val
    return _request(
        'GET',
        f'/api/b2b/alerta-ti/destinatarios/{tipo}/',
        params=params or None,
    )
