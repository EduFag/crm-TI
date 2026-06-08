# Documentação — `helpdesk/views/`

Views e endpoints do **helpdesk**.

## Para que serve

Kanban interativo, dashboard de métricas, histórico filtrado, drawer de detalhe do ticket, comentários e poll leve HTMX para refresh sem bloquear workers.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `__init__.py` | Exporta views de `kanban`, `dashboard`, `history` e `poll`. |
| `kanban.py` | `KanbanView`, `KanbanBoardPartialView`, criação/edição de status, drawer e comentários. |
| `dashboard.py` | `DashboardView` e `DashboardMetricsPartialView` — métricas agregadas. |
| `history.py` | `HistoryListView` — listagem de chamados passados/arquivados. |
| `poll.py` | `poll_ticket_updates` — requisição curta a cada 4s; retorna `HX-Trigger: ticketUpdated` só quando há tickets alterados. |
