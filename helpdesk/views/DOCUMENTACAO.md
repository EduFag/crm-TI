# Documentação — `helpdesk/views/`

Views e endpoints do **helpdesk**.

## Para que serve

Kanban interativo, dashboard de métricas, histórico filtrado, drawer de detalhe do ticket, comentários e stream SSE para refresh via HTMX.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `__init__.py` | Exporta views de `kanban`, `dashboard`, `history` e `sse`. |
| `kanban.py` | `KanbanView`, `KanbanBoardPartialView`, criação/edição de status, drawer e comentários. |
| `dashboard.py` | `DashboardView` e `DashboardMetricsPartialView` — métricas agregadas. |
| `history.py` | `HistoryListView` — listagem de chamados passados/arquivados. |
| `sse.py` | `sse_stream` — Server-Sent Events; emite `ticket_updated` quando há alterações no banco. |
