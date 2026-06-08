# Documentação — `helpdesk/`

App de **chamados de TI** com Kanban, métricas, histórico e atualização em tempo quase real (poll HTMX + partials).

## Para que serve

Registrar tickets (título, prioridade, categoria, solicitante), movê-los entre colunas de status, comentar, arquivar resolvidos antigos e exibir dashboard de métricas.

## Matriz de permissões (criação e gestão)

| Ação | USER | MANAGER | ADMIN / superuser |
|------|------|---------|-------------------|
| Solicitante na criação | Automático (ele mesmo) | Equipe + nome livre | Texto ou qualquer usuário |
| Prioridade na criação | null | null | Define (opcional) |
| Criar categorias | Não | Não | Sim |
| Editar chamado | Não | Não | Sim |
| Transferir técnico | Não | Não | Sim (ADMIN ativos) |

Prioridade fica **null** até triagem pela TI. Gerente vê todos os chamados; equipe restringe apenas seleção de solicitante.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app. |
| `models.py` | `TicketCategory`, `Ticket` (status Kanban, prioridade nullable, arquivamento, `created_by`, `requester_user`) e `Comment`. |
| `forms.py` | `TicketCreateForm` (campos por papel) e `TicketUpdateForm` (edição ADMIN). |
| `ticket_access.py` | Filtro de chamados, permissões de categoria/prioridade/edição/transferência e querysets de equipe/técnicos. |
| `urls.py` | Rotas sob `/helpdesk/` (kanban, dashboard, histórico, poll, partials, edição). |
| `admin.py` | Administração de tickets e comentários. |
| `tests.py` | Testes automatizados. |
| `views/` | Lógica de telas e APIs parciais. Ver `views/DOCUMENTACAO.md`. |
| `migrations/` | Evolução do schema. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Front do helpdesk. Ver `templates/DOCUMENTACAO.md`. |

## Status do Kanban (`Ticket.StatusChoices`)

Novos → Em Atendimento → Pendente → Resolvido (com arquivamento automático após 7 dias resolvido).
