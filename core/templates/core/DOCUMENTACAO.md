# Documentação — `core/templates/core/`

Templates HTML do módulo **core**.

## Para que serve

Interface de login, dashboard, gestão de usuários e páginas de erro de permissão.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `login.html` | Tela de autenticação (`LoginView`, rota `/login/`). |
| `dashboard.html` | Home do sistema após login (rota `/`). |
| `user_list.html` | Listagem de usuários (`/usuarios/`) — create/edit via modal HTMX. |
| `equipe_list.html` | Listagem de equipes (`/equipes/`) — create/edit via modal HTMX. |
| `sem_permissao.html` | Página exibida quando o usuário não tem acesso ao módulo. |
| `_htmx_form_modal.html` | Partial reutilizável de modal flutuante para formulários POST (HTMX). |

## Relacionado

O arquivo `../base.html` (em `core/templates/`) é o **layout mestre** usado pelos outros apps via `{% extends %}`.
