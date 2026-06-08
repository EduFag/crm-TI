# Documentação — `core/templates/`

Diretório de templates do app **core** (convenção Django: `templates/<app_name>/`).

## Para que serve

Agrupa arquivos HTML renderizados pelas views de login, dashboard, gestão de usuários e o layout global.

## Subpastas

| Pasta | Conteúdo |
|-------|----------|
| `core/` | Templates específicos do app. Ver `core/DOCUMENTACAO.md` nesta árvore. |

## Arquivos neste nível

| Arquivo | Função |
|---------|--------|
| `base.html` | Layout mestre (menu dinâmico por permissão, estrutura) herdado pelos demais módulos. |
| `403.html` | Página amigável de acesso negado (handler Django). |
| `404.html` | Página amigável de recurso não encontrado. |
| `500.html` | Página amigável de erro interno do servidor. |
| `errors/layout.html` | Layout standalone das páginas de erro (sem menu/DB). |

## Subpasta `core/`

Templates específicos do app (`login.html`, `dashboard.html`).
