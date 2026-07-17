"""MCP Emails — tools somente leitura."""

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-emails')


@mcp.tool()
def list_domains(q: str = '', limit: int = 20) -> str:
    """Lista domínios de e-mail cadastrados."""
    try:
        return get_client().get_text('domains/', {'q': q or None, 'limit': limit})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def list_accounts(
    status: str = '',
    domain: str = '',
    q: str = '',
    limit: int = 20,
) -> str:
    """Lista contas de e-mail. Filtros: status (ACTIVE|BLOCKED), domain, q, limit."""
    try:
        return get_client().get_text('accounts/', {
            'status': status or None,
            'domain': domain or None,
            'q': q or None,
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def get_account(account_id: int) -> str:
    """Retorna uma conta de e-mail pelo ID (sem senha)."""
    try:
        return get_client().get_text(f'accounts/{account_id}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
