# Documentação — `chips/`

App de **gestão de chips celulares** (linhas, operadoras, envelopes, entregas, transferências e recargas).

## Para que serve

Inventário central de chips, cadastro de operadoras e envelopes físicos na TI, planilha operacional do callcenter (Tabulator), fluxo de atribuição/transferência a titulares e registro financeiro de recargas. Ciclo de recarga: **90 dias** a partir da última recarga (ou data de ativação se nunca recarregou).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app Django. |
| `models.py` | `Operator`, `Batch`, `Chip`, `ChipMovement`, `Recharge`. |
| `urls.py` | Rotas sob `/chips/` (dashboard, API grid, operadoras, envelopes, gestão, atribuição, recarga). |
| `forms.py` | Formulários com titular estilo helpdesk (nome livre / usuário). |
| `services.py` | Operações: entregar, transferir, devolver para TI, bloquear. |
| `queries.py` | Anotações e serialização JSON do grid. |
| `period.py` | Filtro de período do dashboard (default: mês atual). |
| `audit.py` | Dual-write de movimentações e CRUD em `RegistroAcao`. |
| `views/` | Views divididas por domínio. Ver `views/DOCUMENTACAO.md`. |
| `migrations/` | Schema do banco. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Interface web. Ver `templates/DOCUMENTACAO.md`. |

## Modelos principais

- **Operator** — operadora (Claro, TIM, Vivo, etc.).
- **Batch** — lote ou **envelope** físico na TI (`tipo`, `nome`, `setor`, `received_at`).
- **Chip** — linha, custódia (`WITH_TI` / `WITH_PERSON`), `activated_at`, `last_blocked_at`, operadora, envelope.
- **ChipMovement** — entrega, devolução ou **transferência**; `employee_name` + `employee_user` opcional.
- **Recharge** — histórico de recargas em valor monetário.

## API do grid (Tabulator)

| Método | Rota | Função |
|--------|------|--------|
| GET | `/chips/api/grid/` | Lista chips operacionais + operadoras/envelopes |
| POST | `/chips/api/grid/create/` | Nova linha |
| PATCH | `/chips/api/grid/<id>/` | Edição inline |
| POST | `/chips/api/grid/<id>/transfer/` | Transferência de posse |
| POST | `/chips/api/grid/<id>/return/` | Devolução para envelope na TI |
| GET | `/chips/api/grid/<id>/transfer/modal/` | Modal HTMX de transferência |

## Onde visualizar

- **Página única** (`/chips/`) — 4 abas: dashboard (KPIs + gráficos), chips (Tabulator), operadoras e envelopes.
- **Auditoria** — via `RegistroAcao` no rodapé do dashboard.
