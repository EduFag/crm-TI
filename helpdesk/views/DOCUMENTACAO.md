# Documentação — `helpdesk/views/`

Views e endpoints do **helpdesk**.

## Para que serve

Kanban interativo, dashboard de métricas, histórico filtrado, drawer de detalhe do ticket, comentários, edição/transferência (ADMIN) e poll leve HTMX para refresh sem bloquear workers.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `__init__.py` | Exporta views de `kanban`, `dashboard`, `history` e `poll`. |
| `kanban.py` | Kanban, criação, categorias, status, drawer, comentários, `ticket_edit` e `ticket_transfer`. |
| `dashboard.py` | `DashboardView` e `DashboardMetricsPartialView` — métricas agregadas. |
| `history.py` | `HistoryListView` — listagem de chamados passados/arquivados (filtro prioridade null). |
| `poll.py` | `poll_ticket_updates` — requisição curta a cada 4s; retorna `HX-Trigger: ticketUpdated` só quando há tickets alterados. |

## Rotas de ticket (kanban.py)

| Rota | View |
|------|------|
| `ticket/create/` | Modal de criação (campos condicionais por papel) |
| `ticket/<pk>/drawer/` | Detalhes + comentários |
| `ticket/<pk>/edit/` | Edição completa (ADMIN/superuser) |
| `ticket/<pk>/transfer/` | Transferência rápida de técnico |
| `ticket/<pk>/update-status/` | Drag-and-drop Kanban (ADMIN/superuser) |
| `ticket/<pk>/comment/` | Novo comentário |
