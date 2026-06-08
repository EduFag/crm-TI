# Documentação — `core/`

App **núcleo** do sistema: autenticação, usuário customizado, permissões por módulo e tela inicial após login.

## Para que serve

- Modelo de usuário com papéis (RBAC): ADMIN, MANAGER, USER.
- URLs `/`, `/login/`, `/logout/`, `/sem-permissao/`, `/usuarios/`.
- Layout base HTML compartilhado pelos outros módulos.
- Controle de acesso por módulo (menu lateral, views e APIs).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app `CoreConfig`. |
| `models.py` | `CustomUser` estende `AbstractUser` com `role` e timestamps. |
| `permissions.py` | Matriz role→módulo, `ModuloObrigatorioMixin`, decorator `@requer_modulo`. |
| `context_processors.py` | `modulos_menu` — módulos permitidos no menu lateral. |
| `forms.py` | Formulários de criação e edição de usuários. |
| `views.py` | Dashboard, gestão de usuários, página sem permissão. |
| `urls.py` | Rotas de dashboard, login, logout, usuários e sem-permissao. |
| `admin.py` | Registro de `CustomUser` no Django Admin. |
| `tests.py` | Testes automatizados do app (quando implementados). |
| `migrations/` | Migrações do banco para `CustomUser`. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Templates HTML. Ver `templates/DOCUMENTACAO.md`. |

## Papéis e módulos

| Papel | Módulos |
|-------|---------|
| USER | helpdesk |
| MANAGER | helpdesk, chips, emails, equipment |
| ADMIN | todos + gestao_usuarios + discador |

Superusuários ignoram restrições. Cadastro de usuários é somente por ADMIN (sem auto-registro público).

## Subpastas

- `migrations/` — schema do usuário customizado.
- `templates/` — `base.html`, login, dashboard e gestão de usuários.
