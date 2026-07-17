"""Cliente HTTP compartilhado pelos servidores MCP do CRM TI."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx


class CrmTiApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class CrmTiClient:
    """GET autenticado contra /api/mcp/."""

    def __init__(self, base_url: str | None = None, token: str | None = None, timeout: float = 30.0):
        base = (base_url or os.environ.get('CRM_TI_API_BASE') or '').strip().rstrip('/')
        tok = (token or os.environ.get('CRM_TI_MCP_TOKEN') or '').strip()
        if not base:
            raise CrmTiApiError('Defina CRM_TI_API_BASE (ex.: https://ti.moneypromotora.com.br).')
        if not tok:
            raise CrmTiApiError('Defina CRM_TI_MCP_TOKEN (mesmo valor de MCP_API_TOKEN no Django).')
        self.base_url = base
        self.api_root = f'{base}/api/mcp/'
        self.token = tok
        self.timeout = timeout

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        path = path.lstrip('/')
        url = urljoin(self.api_root, path)
        if params:
            limpos = {k: v for k, v in params.items() if v is not None and v != ''}
            if limpos:
                url = f'{url}?{urlencode(limpos)}'

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise CrmTiApiError(f'Falha de rede: {exc}') from exc

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise CrmTiApiError(
                f'HTTP {resp.status_code}: {detail}',
                status_code=resp.status_code,
            )
        return resp.json()

    def post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        path = path.lstrip('/')
        url = urljoin(self.api_root, path)
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=body or {})
        except httpx.HTTPError as exc:
            raise CrmTiApiError(f'Falha de rede: {exc}') from exc

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise CrmTiApiError(
                f'HTTP {resp.status_code}: {detail}',
                status_code=resp.status_code,
            )
        if not resp.content:
            return {'ok': True}
        return resp.json()

    def get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        data = self.get(path, params)
        return json.dumps(data, ensure_ascii=False, indent=2)

    def post_text(self, path: str, body: dict[str, Any] | None = None) -> str:
        data = self.post(path, body)
        return json.dumps(data, ensure_ascii=False, indent=2)


def get_client() -> CrmTiClient:
    return CrmTiClient()
