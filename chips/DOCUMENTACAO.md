# Documentação — `chips/`

App de **gestão de chips celulares** (linhas, operadoras, lotes, entregas, devoluções e recargas).

## Para que serve

Inventário central de chips, cadastro de operadoras e lotes, fluxo de atribuição a funcionários e registro financeiro de recargas. Atende requisitos RF03–RF14 do escopo de chips.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app Django. |
| `models.py` | `Operator`, `Batch`, `Chip`, `ChipMovement`, `Recharge`. |
| `urls.py` | Rotas sob `/chips/` (dashboard, operadoras, lotes, gestão, atribuição, recarga). |
| `admin.py` | Modelos no Django Admin. |
| `tests.py` | Testes do módulo. |
| `views/` | Views divididas por domínio. Ver `views/DOCUMENTACAO.md`. |
| `audit.py` | Dual-write de movimentações e CRUD em `RegistroAcao`. |
| `migrations/` | Schema do banco. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Interface web. Ver `templates/DOCUMENTACAO.md`. |

## Modelos principais

- **Operator** — operadora (Claro, Vivo, etc.).
- **Batch** — lote/saquinho de recebimento.
- **Chip** — linha, ICCID, plano, status, vínculo com operadora e lote.
- **ChipMovement** — entrega ou devolução a funcionário.
- **Recharge** — histórico de recargas em valor monetário.
