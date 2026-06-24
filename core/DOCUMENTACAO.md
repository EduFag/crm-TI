# Documentação — `core/`

App **núcleo** do sistema: autenticação, usuário customizado, permissões por módulo e tela inicial após login.

## Para que serve

- Modelo de usuário com papéis (RBAC): ADMIN, IT_USER, SUPERVISOR, TEAM_LEADER, MULTIPLIER, STANDARD.
- Equipes organizacionais (`Equipe`) para agrupar usuários.
- URLs `/`, `/login/`, `/logout/`, `/sem-permissao/`, `/usuarios/`, `/equipes/`, `/auditoria/`.
- Layout base HTML compartilhado pelos outros módulos.
- Controle de acesso por módulo (menu lateral, views e APIs).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `models.py` | `Equipe`, `CustomUser` e `RegistroAcao` (auditoria append-only). |
| `permissions.py` | Matriz role→módulo, `ModuloObrigatorioMixin`, decorator `@requer_modulo`. |
| `context_processors.py` | `modulos_menu` — módulos permitidos no menu lateral. |
| `views.py` | Dashboard, gestão de usuários/equipes, auditoria global. |
| `forms.py` | Formulários de equipes e de criação/edição de usuários. |

## Papéis e módulos

| Papel | Módulos |
|-------|---------|
| STANDARD, MULTIPLIER, TEAM_LEADER, SUPERVISOR | helpdesk |
| IT_USER | helpdesk, chips, emails, equipment, discador |
| ADMIN | helpdesk |
| Superuser | todos (inclui gestao_usuarios e auditoria) |

**Gestão de usuários/equipes e auditoria:** somente superuser (`is_superuser`).

**Django Admin:** somente superuser (`is_staff=True`). Demais papéis não devem ter `is_staff`.

## Equipes

- Usuário pode pertencer a várias equipes (`equipes` M2M).
- Atribuição feita por superuser na gestão de usuários ou Django Admin.

## Helpdesk

Permissões detalhadas do helpdesk ficam em `helpdesk/ticket_access.py` e `.agent/skills/rbac-helpdesk/SKILL.md`.
