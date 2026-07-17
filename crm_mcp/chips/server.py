"""MCP Chips — tools somente leitura."""

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-chips')


@mcp.tool()
def list_chips(
    status: str = '',
    usage_status: str = '',
    q: str = '',
    active: str = 'true',
    limit: int = 20,
) -> str:
    """Lista chips. Filtros: status, usage_status (AVAILABLE|IN_USE|UNAVAILABLE), q, active, limit."""
    try:
        return get_client().get_text('chips/', {
            'status': status or None,
            'usage_status': usage_status or None,
            'q': q or None,
            'active': active or None,
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def get_chip(chip_id: int) -> str:
    """Retorna um chip pelo ID."""
    try:
        return get_client().get_text(f'chips/{chip_id}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def lookup_chip_by_line(line_number: str) -> str:
    """Busca chip pelo número da linha (com ou sem máscara)."""
    try:
        return get_client().get_text(f'chips/by-line/{line_number}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def list_chip_movements(chip_id: int, limit: int = 20) -> str:
    """Lista movimentações (entrega/devolução/transferência) de um chip."""
    try:
        return get_client().get_text(f'chips/{chip_id}/movements/', {'limit': limit})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
