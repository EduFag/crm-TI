"""MCP Audit — tools somente leitura."""

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-audit')


@mcp.tool()
def list_acoes(
    modulo: str = '',
    acao: str = '',
    actor: str = '',
    q: str = '',
    limit: int = 20,
) -> str:
    """Lista registros de auditoria. Filtros: modulo, acao, actor, q, limit."""
    try:
        return get_client().get_text('acoes/', {
            'modulo': modulo or None,
            'acao': acao or None,
            'actor': actor or None,
            'q': q or None,
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def get_acao(acao_id: int) -> str:
    """Retorna um registro de auditoria pelo ID."""
    try:
        return get_client().get_text(f'acoes/{acao_id}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def sistema_status() -> str:
    """Status mínimo da API MCP e URL pública do sistema."""
    try:
        return get_client().get_text('sistema/status/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
