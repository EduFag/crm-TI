# Documentação — `helpdesk/templates/helpdesk/`

Templates HTML do módulo **helpdesk**.

## Para que serve

Telas completas e fragmentos reutilizáveis para Kanban dinâmico e drawer lateral de ticket.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `kanban.html` | Página principal do quadro Kanban (`/helpdesk/`). |
| `_kanban_board.html` | Partial do board — atualizado via HTMX quando o poll detecta mudança. |
| `_poll.html` | Div oculta com `hx-trigger="every 4s"` — poll leve sem socket aberto. |
| `_ticket_card.html` | Card individual de um chamado na coluna (badge prioridade inclui "Sem prioridade"). |
| `dashboard.html` | Dashboard de métricas (`/helpdesk/dashboard/`). |
| `_dashboard_metrics.html` | Partial das métricas — atualizado via poll HTMX. |
| `history.html` | Histórico de chamados (filtro `__null__` para sem prioridade). |
| `_ticket_create_modal.html` | Modal de criação — campos condicionais por papel (USER/MANAGER/ADMIN). |
| `_category_field.html` | Select de categoria com painel de criação inline (ADMIN/superuser). |
| `_drawer.html` | Painel lateral com detalhes, transferência e link para edição. |
| `_ticket_edit_section.html` | Formulário de edição de chamado (ADMIN/superuser). |
| `_comments_list.html` | Lista de comentários no drawer. |
| `_nav.html` | Navegação interna do módulo helpdesk. |

## Convenção

Arquivos com prefixo `_` são **partials** incluídos ou carregados por HTMX, não páginas completas.
