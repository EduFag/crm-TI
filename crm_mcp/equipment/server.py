"""MCP Equipment — tools somente leitura."""

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-equipment')


@mcp.tool()
def list_equipment(
    status: str = '',
    equipment_type: str = '',
    q: str = '',
    limit: int = 20,
) -> str:
    """Lista equipamentos. Filtros: status, equipment_type (NOTEBOOK|DESKTOP|...), q, limit."""
    try:
        return get_client().get_text('equipment/', {
            'status': status or None,
            'type': equipment_type or None,
            'q': q or None,
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def get_equipment(equipment_id: int) -> str:
    """Retorna um equipamento pelo ID."""
    try:
        return get_client().get_text(f'equipment/{equipment_id}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def lookup_equipment_by_tag(tag: str) -> str:
    """Busca equipamento pela tag de patrimônio."""
    try:
        return get_client().get_text(f'equipment/by-tag/{tag}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def list_equipment_logs(equipment_id: int, limit: int = 20) -> str:
    """Lista logs de ciclo de vida do equipamento."""
    try:
        return get_client().get_text(f'equipment/{equipment_id}/logs/', {'limit': limit})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
