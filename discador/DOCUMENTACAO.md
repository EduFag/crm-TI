# Documentação — `discador/`

App de **integração com discador 3C Plus**: importação de ligações, blacklist, regras de reciclagem e processamento de bases CSV.

## Para que serve

Automatizar bloqueio de telefones conforme qualificação de campanhas, manter histórico de importações/processamentos e gerar bases “recicladas” livres de números bloqueados para novas campanhas.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app. |
| `models.py` | `ConfiguracaoAPI`, `LigacaoImportada`, `RegraReciclagem`, `Blacklist`, `ImportacaoAPI`, `ProcessamentoBase`. |
| `views.py` | Telas: dashboard, config API, atualizar blacklist, regras, reciclar bases, consulta, históricos. |
| `urls.py` | Rotas sob `/discador/`. |
| `forms.py` | Formulários Django das telas de configuração e upload. |
| `migrations/` | Schema. Ver `migrations/DOCUMENTACAO.md`. |
| `services/` | Integração API e processamento. Ver `services/DOCUMENTACAO.md`. |
| `utils/` | Normalização de telefone/CPF. Ver `utils/DOCUMENTACAO.md`. |
| `templates/` | Interface web. Ver `templates/DOCUMENTACAO.md`. |

## Fluxo resumido

1. Configurar API 3C Plus → importar ligações → aplicar `RegraReciclagem` → gravar `Blacklist`.
2. Upload CSV em “Reciclar bases” → `csv_processor` filtra bloqueados → arquivos em `MEDIA/discador/`.
