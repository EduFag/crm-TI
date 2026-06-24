# Documentação — `chips/templates/chips/`

Templates HTML do namespace **chips**.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `index.html` | Página única em `/chips/` — 4 abas (jQuery), KPIs, gráficos Chart.js, grid Tabulator, operadoras e envelopes. |
| `_transfer_modal.html` | Modal HTMX de transferência de chip (acionado pelo grid). |
| `_grid_create_modal.html` | Modal HTMX para cadastrar nova linha no grid. |

## Abas (`?tab=`)

| Tab | Conteúdo |
|-----|----------|
| `dashboard` | Filtro de período, KPIs, gráficos, histórico e auditoria. |
| `chips` | Planilha Tabulator — cadastro, edição, transferência e recarga. |
| `operators` | Listagem e CRUD de operadoras (modais HTMX). |
| `envelopes` | Listagem e CRUD de envelopes/lotes (modais HTMX). |

Abas legadas `assignment` e `inventory` abrem automaticamente a aba `chips`.
