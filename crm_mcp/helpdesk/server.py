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
def send_assistente_message(ticket_id: int, text: str) -> str:
    """Envia mensagem no chamado como Assistente de IA."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/assistente/comentarios/',
            {'text': text},
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
    """Descreve imagem anexada via visão (attachment_ref ex.: ticket:12 ou comment:34)."""
    try:
        return get_client().post_text(
            f'tickets/{ticket_id}/anexos/ler-imagem/',
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
    """Busca usuário CRM por username ou nome."""
    try:
        return get_client().get_text('assistente/consultar-usuario/', {'q': q})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
