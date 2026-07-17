"""MCP Users — tools somente leitura."""

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-users')


@mcp.tool()
def list_users(
    role: str = '',
    equipe: str = '',
    q: str = '',
    active: str = 'true',
    limit: int = 20,
) -> str:
    """Lista usuários (sem senha). Filtros: role, equipe, q, active, limit."""
    try:
        return get_client().get_text('users/', {
            'role': role or None,
            'equipe': equipe or None,
            'q': q or None,
            'active': active or None,
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def get_user(user_id: int) -> str:
    """Retorna usuário pelo ID (sem senha)."""
    try:
        return get_client().get_text(f'users/{user_id}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def lookup_user_by_username(username: str) -> str:
    """Busca usuário pelo username."""
    try:
        return get_client().get_text(f'users/by-username/{username}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def list_equipes(q: str = '', active: str = 'true', limit: int = 20) -> str:
    """Lista equipes organizacionais."""
    try:
        return get_client().get_text('equipes/', {
            'q': q or None,
            'active': active or None,
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def list_equipe_membros(equipe_id: int, limit: int = 50) -> str:
    """Lista membros de uma equipe."""
    try:
        return get_client().get_text(f'equipes/{equipe_id}/membros/', {'limit': limit})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
