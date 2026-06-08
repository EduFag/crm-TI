# Documentação — `core/`

App **núcleo** do sistema: autenticação, usuário customizado, permissões por módulo e tela inicial após login.

## Para que serve

- Modelo de usuário com papéis (RBAC): ADMIN, MANAGER, USER.
- Equipes organizacionais (`Equipe`) para agrupar usuários.
- URLs `/`, `/login/`, `/logout/`, `/sem-permissao/`, `/usuarios/`, `/equipes/`.
- Layout base HTML compartilhado pelos outros módulos.
- Controle de acesso por módulo (menu lateral, views e APIs).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app `CoreConfig`. |
| `models.py` | `Equipe` e `CustomUser` (AbstractUser + `role`, `equipe`, timestamps). |
| `permissions.py` | Matriz role→módulo, `ModuloObrigatorioMixin`, decorator `@requer_modulo`. |
| `context_processors.py` | `modulos_menu` — módulos permitidos no menu lateral. |
| `forms.py` | Formulários de equipes e de criação/edição de usuários. |
| `htmx.py` | `HtmxModalMixin` — formulários POST como modal flutuante na listagem. |
| `views.py` | Dashboard, gestão de usuários, gestão de equipes, sem permissão e handlers 403/404/500. |
| `urls.py` | Rotas de dashboard, login, logout, usuários, equipes e sem-permissao. |
| `admin.py` | Registro de `Equipe` e `CustomUser` no Django Admin. |
| `tests.py` | Testes automatizados do app (quando implementados). |
| `migrations/` | Migrações do banco. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Templates HTML. Ver `templates/DOCUMENTACAO.md`. |

## Papéis e módulos

| Papel | Módulos |
|-------|---------|
| USER | helpdesk |
| MANAGER | helpdesk, chips, emails, equipment |
| ADMIN | todos + gestao_usuarios + discador |

Superusuários ignoram restrições. Cadastro de usuários e equipes é somente por ADMIN (sem auto-registro público).

## Equipes

- Usuário pode ficar **sem equipe** (`equipe` null).
- ADMIN atribui equipe no formulário de usuário (`/usuarios/`) ou via Django Admin.
- CRUD de equipes em `/equipes/` (somente ADMIN).

## Subpastas

- `migrations/` — schema do usuário customizado e equipes.
- `templates/` — `base.html`, login, dashboard, gestão de usuários/equipes e páginas de erro (403/404/500).
