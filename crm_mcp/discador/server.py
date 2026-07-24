"""MCP Discador (JoyTec) — leitura + escrita."""

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-discador')


@mcp.tool()
def consultar_licencas_discador(slug: str = 'joytec') -> str:
    """KPIs de licenças: contratadas, ramais livres, slots disponíveis no contrato."""
    try:
        return get_client().get_text('discador/licencas/', {'slug': slug or 'joytec'})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def listar_ramais_discador(status: str = '', slug: str = 'joytec', limit: int = 40) -> str:
    """Lista ramais. status: FREE|IN_USE|NOT_CONFIGURED (vazio = todos)."""
    try:
        return get_client().get_text('discador/ramais/', {
            'status': status or None,
            'slug': slug or 'joytec',
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def consultar_acesso_discador(q: str, slug: str = 'joytec') -> str:
    """Busca acessos por titular, login ou número do ramal."""
    try:
        return get_client().get_text('discador/acessos/', {
            'q': q,
            'slug': slug or 'joytec',
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def listar_campanhas_discador(slug: str = 'joytec') -> str:
    """Lista campanhas ativas do discador."""
    try:
        return get_client().get_text('discador/campanhas/', {'slug': slug or 'joytec'})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def criar_acesso_discador(
    titular_nome: str,
    login_discador: str,
    tipo: str = 'CONSULTOR',
    ramal_numero: str = '',
    ramal_id: int = 0,
    campanha_nome: str = '',
    campanha_id: int = 0,
    slug: str = 'joytec',
) -> str:
    """Cria acesso no discador. Sem ramal, usa um FREE. Informe campanha_nome ou campanha_id."""
    body = {
        'titular_nome': titular_nome,
        'login_discador': login_discador,
        'tipo': tipo or 'CONSULTOR',
        'ramal_numero': ramal_numero or '',
        'campanha_nome': campanha_nome or '',
        'slug': slug or 'joytec',
    }
    if ramal_id:
        body['ramal_id'] = ramal_id
    if campanha_id:
        body['campanha_id'] = campanha_id
    try:
        return get_client().post_text('discador/acessos/criar/', body)
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def liberar_acesso_discador(acesso_id: int) -> str:
    """Remove acesso; ramal fica FREE (ainda consome licença)."""
    try:
        return get_client().post_text('discador/acessos/liberar/', {'acesso_id': acesso_id})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def liberar_licenca_ramal(
    ramal_id: int = 0,
    ramal_numero: str = '',
    slug: str = 'joytec',
) -> str:
    """Marca ramal NOT_CONFIGURED (libera slot do contrato). Sem acesso vinculado."""
    body = {'slug': slug or 'joytec', 'ramal_numero': ramal_numero or ''}
    if ramal_id:
        body['ramal_id'] = ramal_id
    try:
        return get_client().post_text('discador/ramais/liberar-licenca/', body)
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
