# Documentação — `chips/views/`

Views do módulo **chips**, organizadas por responsabilidade.

## Para que serve

Implementa listagens, formulários e ações operacionais expostas em `chips/urls.py`.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `__init__.py` | Reexporta classes de `dashboard`, `management`, `assignments` e `recharges` para `urls.py`. |
| `dashboard.py` | `DashboardView` — métricas e resumo em `/chips/`. |
| `management.py` | CRUD de operadoras, lotes e chips (`Operator*`, `Batch*`, `Chip*`). |
| `assignments.py` | `AssignmentView` e `ReturnChipView` — entrega e devolução de chips. |
| `recharges.py` | `RechargeCreateView` — registro de recarga financeira. |
