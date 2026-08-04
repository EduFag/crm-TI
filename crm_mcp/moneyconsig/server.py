"""MCP MoneyConsig — API B2B via integração cadastrada no CRM (Integrações → APIs)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-moneyconsig')


@mcp.tool()
def moneyconsig_auth_me() -> str:
    """Valida o token MoneyConsig e retorna identidade + escopo do dono do token."""
    try:
        return get_client().get_text('moneyconsig/auth-me/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def moneyconsig_usuario_consultar(username: str = '', q: str = '') -> str:
    """Consulta usuário/funcionário no MoneyConsig (username e/ou q — um obrigatório)."""
    try:
        return get_client().get_text('moneyconsig/usuarios/consulta/', {
            'username': username or None,
            'q': q or None,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def moneyconsig_alerta_ti_listar(limite: int = 50) -> str:
    """Lista alertas TI do escopo do token MoneyConsig (limite 1–100)."""
    try:
        return get_client().get_text('moneyconsig/alerta-ti/', {'limite': limite or 50})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def moneyconsig_alerta_ti_criar(
    mensagem: str,
    tipo_destinatario: str,
    destinatarios_ids: list[int] | None = None,
) -> str:
    """Cria alerta TI no MoneyConsig (mensagem, tipo_destinatario, destinatarios_ids)."""
    body = {
        'mensagem': mensagem or '',
        'tipo_destinatario': tipo_destinatario or '',
        'destinatarios_ids': list(destinatarios_ids or []),
    }
    try:
        return get_client().post_text('moneyconsig/alerta-ti/criar/', body)
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def moneyconsig_alerta_ti_destinatarios(
    tipo: str,
    empresas: str = '',
    departamentos: str = '',
    setores: str = '',
    cargos: str = '',
) -> str:
    """Cascata de destinatários: funcionarios|empresas|departamentos|setores|lojas|equipes|cargos."""
    params = {
        'empresas': empresas or None,
        'departamentos': departamentos or None,
        'setores': setores or None,
        'cargos': cargos or None,
    }
    try:
        return get_client().get_text(
            f'moneyconsig/alerta-ti/destinatarios/{tipo}/',
            params,
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
