"""MCP Helpdesk — leitura + escrita (Assistente)."""

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


@mcp.tool()
def send_assistente_message(ticket_id: int, text: str, interno: bool = False) -> str:
    """Envia mensagem no chamado como Assistente. interno=True: só TI vê."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/assistente/comentarios/',
            {'text': text, 'interno': bool(interno)},
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def set_ticket_priority(ticket_id: int, priority: str) -> str:
    """Define prioridade: LOW, MEDIUM, HIGH ou URGENT."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/priority/',
            {'priority': priority},
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def set_ticket_status(ticket_id: int, status: str) -> str:
    """Altera coluna Kanban: NEW, IN_PROGRESS, PENDING ou RESOLVED."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/status/',
            {'status': status},
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def escalar_para_ti(ticket_id: int, motivo: str = '') -> str:
    """Encerra o Assistente e pede intervenção da TI (status PENDING se NEW)."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/assistente/escalar/',
            {'motivo': motivo},
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def listar_categorias_especificas() -> str:
    """Lista categorias específicas ativas (id e nome) para triagem."""
    try:
        return get_client().get_text('categorias-especificas/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def triar_chamado(ticket_id: int, priority: str, specific_category_id: int = 0) -> str:
    """Triagem: prioridade + categoria específica. specific_category_id=0 omite categoria."""
    body = {'priority': priority}
    if specific_category_id:
        body['specific_category_id'] = specific_category_id
    try:
        return get_client().post_text(f'tickets/{ticket_id}/assistente/triar/', body)
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def recusar_chamado(ticket_id: int, motivo: str) -> str:
    """Recusa chamado (título/descrição incorretos) com motivo."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/assistente/recusar/',
            {'motivo': motivo},
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def listar_anexos(ticket_id: int) -> str:
    """Lista anexos do ticket e comentários (refs ticket:ID / comment:ID)."""
    try:
        return get_client().get_text(f'tickets/{ticket_id}/anexos/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def ler_imagem_anexo(ticket_id: int, attachment_ref: str) -> str:
    """Lê print: visão multimodal se houver, senão OCR local → texto."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/anexos/ler-imagem/',
            {'attachment_ref': attachment_ref},
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def ler_pdf_anexo(ticket_id: int, attachment_ref: str) -> str:
    """Extrai texto de PDF (nativo ou OCR local)."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/anexos/ler-pdf/',
            {'attachment_ref': attachment_ref},
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def ler_anexo_texto(ticket_id: int, attachment_ref: str) -> str:
    """Converte imagem ou PDF em texto para IA só-texto (ex.: DeepSeek)."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/anexos/ler-texto/',
            {'attachment_ref': attachment_ref},
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def consultar_chips(q: str) -> str:
    """Busca chips por consultor ou número (WhatsApp)."""
    try:
        return get_client().get_text('assistente/consultar-chips/', {'q': q})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def consultar_usuario(q: str) -> str:
    """Busca usuário CRM por username ou nome. eh_membro_ti=true = TI."""
    try:
        return get_client().get_text('assistente/consultar-usuario/', {'q': q})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def atualizar_solicitante(
    ticket_id: int,
    user_id: int = 0,
    nome_livre: str = '',
) -> str:
    """Corrige solicitante: user_id (conta, >0) ou nome_livre (sem conta)."""
    body = {}
    if user_id:
        body['user_id'] = user_id
    if nome_livre:
        body['nome_livre'] = nome_livre
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/assistente/solicitante/',
            body,
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def atualizar_descricao_chamado(
    ticket_id: int,
    description: str,
    title: str = '',
) -> str:
    """Reescreve descrição (e título opcional) do chamado."""
    body = {'description': description}
    if title:
        body['title'] = title
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/assistente/descricao/',
            body,
        )
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def consultar_licencas_discador(slug: str = 'joytec') -> str:
    """KPIs de licenças do discador (JoyTec): livres, em uso, slots do contrato."""
    try:
        return get_client().get_text('discador/licencas/', {'slug': slug or 'joytec'})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def listar_ramais_discador(status: str = '', slug: str = 'joytec', limit: int = 40) -> str:
    """Lista ramais. status: FREE|IN_USE|NOT_CONFIGURED."""
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
    """Busca acesso no discador por titular, login ou ramal."""
    try:
        return get_client().get_text('discador/acessos/', {'q': q, 'slug': slug or 'joytec'})
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
    """Cria acesso no discador. Sem ramal, usa um FREE."""
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
    """Remove acesso; ramal fica FREE."""
    try:
        return get_client().post_text('discador/acessos/liberar/', {'acesso_id': acesso_id})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def liberar_licenca_ramal(ramal_id: int = 0, ramal_numero: str = '', slug: str = 'joytec') -> str:
    """Marca ramal NOT_CONFIGURED (libera slot do contrato)."""
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
