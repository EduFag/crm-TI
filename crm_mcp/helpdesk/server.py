"""MCP Helpdesk — tools somente leitura."""

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-helpdesk')


@mcp.tool()
def list_tickets(
    status: str = '',
    q: str = '',
    assigned_to: str = '',
    archived: str = 'false',
    active: str = 'true',
    limit: int = 20,
) -> str:
    """Lista chamados do helpdesk. Filtros: status (NEW|IN_PROGRESS|PENDING|RESOLVED), q, assigned_to, archived, active, limit."""
    try:
        return get_client().get_text('tickets/', {
            'status': status or None,
            'q': q or None,
            'assigned_to': assigned_to or None,
            'archived': archived or None,
            'active': active or None,
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def get_ticket(ticket_id: int) -> str:
    """Retorna detalhes de um chamado pelo ID."""
    try:
        return get_client().get_text(f'tickets/{ticket_id}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def list_ticket_comments(ticket_id: int, limit: int = 50) -> str:
    """Lista comentários ativos de um chamado."""
    try:
        return get_client().get_text(f'tickets/{ticket_id}/comments/', {'limit': limit})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
