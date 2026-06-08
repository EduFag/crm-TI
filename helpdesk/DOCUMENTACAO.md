# Documentação — `helpdesk/`

App de **chamados de TI** com Kanban, métricas, histórico e atualização em tempo quase real (SSE + HTMX).

## Para que serve

Registrar tickets (título, prioridade, categoria, solicitante), movê-los entre colunas de status, comentar, arquivar resolvidos antigos e exibir dashboard de métricas.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app. |
| `models.py` | `Ticket` (status Kanban, prioridade, arquivamento, `created_by`) e `Comment`. |
| `ticket_access.py` | Filtro de chamados: USER vê apenas os próprios; ADMIN/MANAGER veem todos. |
| `urls.py` | Rotas sob `/helpdesk/` (kanban, dashboard, histórico, SSE, partials). |
| `admin.py` | Administração de tickets e comentários. |
| `tests.py` | Testes automatizados. |
| `views/` | Lógica de telas e APIs parciais. Ver `views/DOCUMENTACAO.md`. |
| `migrations/` | Evolução do schema. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Front do helpdesk. Ver `templates/DOCUMENTACAO.md`. |

## Status do Kanban (`Ticket.StatusChoices`)

Novos → Em Atendimento → Pendente → Resolvido (com arquivamento automático após 7 dias resolvido).
