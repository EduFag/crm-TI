# Documentação — `helpdesk/templates/helpdesk/`

Templates HTML do módulo **helpdesk**.

## Para que serve

Telas completas e fragmentos reutilizáveis para Kanban dinâmico e drawer lateral de ticket.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `kanban.html` | Página principal do quadro Kanban (`/helpdesk/`). |
| `_kanban_board.html` | Partial do board — atualizado via HTMX/SSE. |
| `_ticket_card.html` | Card individual de um chamado na coluna. |
| `dashboard.html` | Dashboard de métricas (`/helpdesk/dashboard/`). |
| `_dashboard_metrics.html` | Partial das métricas numéricas/gráficos. |
| `history.html` | Histórico de chamados. |
| `ticket_form.html` | Formulário de criação de ticket. |
| `_drawer.html` | Painel lateral com detalhes do ticket selecionado. |
| `_comments_list.html` | Lista de comentários no drawer. |
| `_nav.html` | Navegação interna do módulo helpdesk. |

## Convenção

Arquivos com prefixo `_` são **partials** incluídos ou carregados por HTMX, não páginas completas.
