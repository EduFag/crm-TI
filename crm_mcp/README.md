# Servidores MCP do CRM TI

## O que é

Servidores MCP (stdio) que chamam a API Django em `/api/mcp/` com Bearer token.

| Servidor | Módulo Python | Tools |
|----------|---------------|-------|
| mcp-helpdesk | `crm_mcp.helpdesk.server` | tickets, assistente (triagem/anexos/solicitante), aprendizado (chunks R/W), helpers chips/usuário |
| mcp-chips | `crm_mcp.chips.server` | list/get/lookup + movements + `atualizar_status_chip` / `atualizar_observacao_chip` |
| mcp-discador | `crm_mcp.discador.server` | inventário local CRM (licenças, ramais, acessos, campanhas, criar/liberar) — **não** acessa o site JoyTec |
| mcp-equipment | `crm_mcp.equipment.server` | list_equipment, get_equipment, lookup_equipment_by_tag, list_equipment_logs |
| mcp-emails | `crm_mcp.emails.server` | list_domains, list_accounts, get_account |
| mcp-operadores | `crm_mcp.operadores.server` | list/get operadores, list/get WhatsApp (somente leitura) |
| mcp-users | `crm_mcp.users.server` | list_users, get_user, lookup_user_by_username, list_equipes, list_equipe_membros |
| mcp-audit | `crm_mcp.audit.server` | list_acoes, get_acao, sistema_status |

**MoneyConsig:** sistema interno da Money; API oficial ainda não liberada — sem MCP neste repo.

**Discador JoyTec:** site externo. O MCP/CRM só controla o inventário manual (ramais + responsáveis). Criar ramal novo = suporte humano da discadora.

Discador **não** é espelhado no helpdesk MCP — use `mcp-discador`.

## Tools Helpdesk (leitura + Assistente + aprendizado)

| Tool | Endpoint |
|------|----------|
| `list_tickets` | GET `tickets/` |
| `get_ticket` | GET `tickets/<id>/` |
| `list_ticket_comments` | GET `tickets/<id>/comments/` |
| `send_assistente_message` | POST `tickets/<id>/assistente/comentarios/` |
| `set_ticket_priority` | POST `tickets/<id>/priority/` |
| `set_ticket_status` | POST `tickets/<id>/status/` |
| `escalar_para_ti` | POST `tickets/<id>/assistente/escalar/` |
| `listar_categorias_especificas` | GET `categorias-especificas/` |
| `triar_chamado` | POST `tickets/<id>/assistente/triar/` |
| `recusar_chamado` | POST `tickets/<id>/assistente/recusar/` |
| `listar_anexos` | GET `tickets/<id>/anexos/` |
| `ler_imagem_anexo` | POST `tickets/<id>/anexos/ler-imagem/` |
| `ler_pdf_anexo` | POST `tickets/<id>/anexos/ler-pdf/` |
| `ler_anexo_texto` | POST `tickets/<id>/anexos/ler-texto/` |
| `consultar_chips` | GET `assistente/consultar-chips/` |
| `consultar_usuario` | GET `assistente/consultar-usuario/` |
| `atualizar_solicitante` | POST `tickets/<id>/assistente/solicitante/` |
| `atualizar_descricao_chamado` | POST `tickets/<id>/assistente/descricao/` |
| `list_chunks` | GET `aprendizado/chunks/` |
| `get_chunk` | GET `aprendizado/chunks/<id>/` |
| `search_chunks` | GET `aprendizado/chunks/search/` |
| `create_chunk` | POST `aprendizado/chunks/criar/` |
| `update_chunk` | POST `aprendizado/chunks/<id>/atualizar/` |

## Tools Chips (`mcp-chips`)

| Tool | Endpoint |
|------|----------|
| `list_chips` | GET `chips/` |
| `get_chip` | GET `chips/<id>/` |
| `lookup_chip_by_line` | GET `chips/by-line/<line>/` |
| `list_chip_movements` | GET `chips/<id>/movements/` |
| `atualizar_status_chip` | POST `chips/<id>/status/` |
| `atualizar_observacao_chip` | POST `chips/<id>/observacao/` |

## Tools Discador (`mcp-discador`) — inventário local

| Tool | Endpoint |
|------|----------|
| `consultar_licencas_discador` | GET `discador/licencas/` |
| `listar_ramais_discador` | GET `discador/ramais/` |
| `consultar_acesso_discador` | GET `discador/acessos/` |
| `listar_campanhas_discador` | GET `discador/campanhas/` |
| `criar_acesso_discador` | POST `discador/acessos/criar/` |
| `liberar_acesso_discador` | POST `discador/acessos/liberar/` |
| `liberar_licenca_ramal` | POST `discador/ramais/liberar-licenca/` |

## Tools Operadores (`mcp-operadores`)

| Tool | Endpoint |
|------|----------|
| `list_operadores` | GET `operadores/` |
| `get_operador` | GET `operadores/<id>/` |
| `list_whatsapp` | GET `whatsapp/` |
| `get_whatsapp` | GET `whatsapp/<id>/` |

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
curl -H "Authorization: Bearer SEU_TOKEN" "https://ti.moneypromotora.com.br/api/mcp/operadores/"
curl -H "Authorization: Bearer SEU_TOKEN" "https://ti.moneypromotora.com.br/api/mcp/aprendizado/chunks/"
curl -H "Authorization: Bearer SEU_TOKEN" "https://ti.moneypromotora.com.br/api/mcp/aprendizado/chunks/search/?q=discador"
```
