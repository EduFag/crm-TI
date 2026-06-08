# Documentação — `chips/views/`

Views do módulo **chips**, organizadas por responsabilidade.

## Para que serve

Implementa listagens, formulários, API JSON do grid Tabulator e ações operacionais expostas em `chips/urls.py`.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `__init__.py` | Reexporta classes para `urls.py`. |
| `dashboard.py` | `ChipsView` — página única com abas em `/chips/`; `ChipsAssignmentPostView` para POST de atribuição. |
| `grid.py` | API JSON e modal de transferência para planilha Tabulator. |
| `management.py` | CRUD de operadoras, envelopes/lotes e chips. |
| `assignments.py` | `AssignmentView` e `ReturnChipView` — entrega, transferência e devolução. |
| `recharges.py` | `RechargeCreateView` — registro de recarga financeira. |
