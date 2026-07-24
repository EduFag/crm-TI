# Servidores MCP do CRM TI

## O que é

Servidores MCP (stdio) que chamam a API Django em `/api/mcp/` com Bearer token.

| Servidor | Módulo Python | Tools |
|----------|---------------|-------|
| mcp-helpdesk | `crm_mcp.helpdesk.server` | tickets, assistente, chips/usuario helpers |
| mcp-chips | `crm_mcp.chips.server` | list_chips, get_chip, lookup_chip_by_line, list_chip_movements |
| mcp-discador | `crm_mcp.discador.server` | licenças, ramais, acessos, campanhas, criar/liberar |
| mcp-equipment | `crm_mcp.equipment.server` | list_equipment, get_equipment, lookup_equipment_by_tag, list_equipment_logs |
| mcp-emails | `crm_mcp.emails.server` | list_domains, list_accounts, get_account |
| mcp-users | `crm_mcp.users.server` | list_users, get_user, lookup_user_by_username, list_equipes, list_equipe_membros |
| mcp-audit | `crm_mcp.audit.server` | list_acoes, get_acao, sistema_status |

## Tools de escrita (Assistente / Discador)

| Tool | Endpoint |
|------|----------|
| `send_assistente_message` | POST `tickets/<id>/assistente/comentarios/` |
| `set_ticket_priority` | POST `tickets/<id>/priority/` |
| `set_ticket_status` | POST `tickets/<id>/status/` |
| `escalar_para_ti` | POST `tickets/<id>/assistente/escalar/` |
| `consultar_licencas_discador` | GET `discador/licencas/` |
| `listar_ramais_discador` | GET `discador/ramais/` |
| `consultar_acesso_discador` | GET `discador/acessos/` |
| `listar_campanhas_discador` | GET `discador/campanhas/` |
| `criar_acesso_discador` | POST `discador/acessos/criar/` |
| `liberar_acesso_discador` | POST `discador/acessos/liberar/` |
| `liberar_licenca_ramal` | POST `discador/ramais/liberar-licenca/` |

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
python -m crm_mcp.discador.server
```

## Cursor

Veja [`.cursor/mcp.json`](../.cursor/mcp.json). Ajuste o caminho do `python` se necessário e preencha `CRM_TI_MCP_TOKEN`.

## Curl (smoke da API)

```bash
curl -H "Authorization: Bearer SEU_TOKEN" "https://ti.moneypromotora.com.br/api/mcp/sistema/status/"
curl -H "Authorization: Bearer SEU_TOKEN" "https://ti.moneypromotora.com.br/api/mcp/discador/licencas/"
```
