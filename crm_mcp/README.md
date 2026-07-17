# Servidores MCP do CRM TI (somente leitura via HTTP)

## O que é

Seis servidores MCP (stdio) que chamam a API Django em `/api/mcp/` com Bearer token.

| Servidor | Módulo Python | Tools |
|----------|---------------|-------|
## Tools de escrita (Assistente)

| Tool | Endpoint |
|------|----------|
| `send_assistente_message` | POST `tickets/<id>/assistente/comentarios/` |
| `set_ticket_priority` | POST `tickets/<id>/priority/` |
| `set_ticket_status` | POST `tickets/<id>/status/` |
| `escalar_para_ti` | POST `tickets/<id>/assistente/escalar/` |
| mcp-chips | `crm_mcp.chips.server` | list_chips, get_chip, lookup_chip_by_line, list_chip_movements |
| mcp-equipment | `crm_mcp.equipment.server` | list_equipment, get_equipment, lookup_equipment_by_tag, list_equipment_logs |
| mcp-emails | `crm_mcp.emails.server` | list_domains, list_accounts, get_account |
| mcp-users | `crm_mcp.users.server` | list_users, get_user, lookup_user_by_username, list_equipes, list_equipe_membros |
| mcp-audit | `crm_mcp.audit.server` | list_acoes, get_acao, sistema_status |

O pacote chama-se `crm_mcp` (não `mcp`) para não conflitar com o SDK oficial `mcp` no PyPI.

## Variáveis de ambiente

### No Django (VPS / `.env`)

```bash
MCP_API_TOKEN=um-segredo-longo-aleatorio
```

Sem `MCP_API_TOKEN`, os endpoints retornam **503**.

### Nos servidores MCP (Cursor / local)

```bash
CRM_TI_API_BASE=https://ti.moneypromotora.com.br
CRM_TI_MCP_TOKEN=um-segredo-longo-aleatorio
```

`CRM_TI_MCP_TOKEN` deve ser **igual** a `MCP_API_TOKEN`.

## Instalação local

Na raiz do repositório:

```bash
pip install -r crm_mcp/requirements.txt
```

Garanta que a raiz do repo esteja no `PYTHONPATH` (ou rode a partir da raiz).

Teste um servidor:

```bash
set CRM_TI_API_BASE=https://ti.moneypromotora.com.br
set CRM_TI_MCP_TOKEN=seu-token
python -m crm_mcp.audit.server
```

## Cursor

Veja [`.cursor/mcp.json`](../.cursor/mcp.json). Ajuste o caminho do `python` se necessário e preencha `CRM_TI_MCP_TOKEN`.

## Curl (smoke da API)

```bash
curl -H "Authorization: Bearer SEU_TOKEN" "https://ti.moneypromotora.com.br/api/mcp/sistema/status/"
```
