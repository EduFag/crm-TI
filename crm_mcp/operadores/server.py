"""MCP Operadores — tools somente leitura (operadores e WhatsApp)."""

from mcp.server.fastmcp import FastMCP

from crm_mcp.shared.client import CrmTiApiError, get_client

mcp = FastMCP('crm-ti-operadores')


@mcp.tool()
def list_operadores(q: str = '', limit: int = 20) -> str:
    """Lista operadores. Filtro opcional q (nome, PA, ilha, setor)."""
    try:
        return get_client().get_text('operadores/', {'q': q or None, 'limit': limit})
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def get_operador(operador_id: int) -> str:
    """Retorna operador + contas WhatsApp vinculadas."""
    try:
        return get_client().get_text(f'operadores/{operador_id}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def list_whatsapp(status: str = '', q: str = '', limit: int = 20) -> str:
    """Lista contas WhatsApp. status: ACTIVE|RESTRICTED|SUSPENDED|BANNED."""
    try:
        return get_client().get_text('whatsapp/', {
            'status': status or None,
            'q': q or None,
            'limit': limit,
        })
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


@mcp.tool()
def get_whatsapp(whatsapp_id: int) -> str:
    """Retorna uma conta WhatsApp pelo ID."""
    try:
        return get_client().get_text(f'whatsapp/{whatsapp_id}/')
    except CrmTiApiError as exc:
        return f'Erro: {exc}'


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
