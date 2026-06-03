# Documentação — `core/`

App **núcleo** do sistema: autenticação, usuário customizado e tela inicial após login.

## Para que serve

- Modelo de usuário com papéis (RBAC): ADMIN, MANAGER, USER.
- URLs `/`, `/login/`, `/logout/`.
- Layout base HTML compartilhado pelos outros módulos.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app `CoreConfig`. |
| `models.py` | `CustomUser` estende `AbstractUser` com `role` e timestamps. |
| `views.py` | `dashboard_view` — página inicial autenticada. |
| `urls.py` | Rotas de dashboard, login e logout. |
| `admin.py` | Registro de `CustomUser` no Django Admin. |
| `tests.py` | Testes automatizados do app (quando implementados). |
| `migrations/` | Migrações do banco para `CustomUser`. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Templates HTML. Ver `templates/DOCUMENTACAO.md`. |

## Subpastas

- `migrations/` — schema do usuário customizado.
- `templates/` — `base.html`, login e dashboard.
