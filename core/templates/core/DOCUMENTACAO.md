# Documentação — `core/templates/core/`

Templates HTML do módulo **core**.

## Para que serve

Interface de login, dashboard principal e herança de layout para o restante do CRM.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `login.html` | Tela de autenticação (`LoginView`, rota `/login/`). |
| `dashboard.html` | Home do sistema após login (rota `/`). |

## Relacionado

O arquivo `../base.html` (em `core/templates/`) é o **layout mestre** usado pelos outros apps via `{% extends %}`.
