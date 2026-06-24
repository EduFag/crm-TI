# Documentação — `helpdesk/`

App de **chamados de TI** com Kanban, métricas, histórico e atualização em tempo quase real (poll HTMX + partials).

## Para que serve

Registrar tickets (título, prioridade, categoria, solicitante, co-autores), movê-los entre colunas de status, comentar, arquivar resolvidos antigos e exibir dashboard de métricas.

## Matriz de papéis (RBAC)

| Papel | Código | Módulos | Ver chamados | Arquivados | Kanban move | Comentar |
|-------|--------|---------|--------------|------------|-------------|----------|
| Superuser | `is_superuser` | Todos | Todos | Sim | Sim | Todos |
| Membro Equipe (TI) | `IT_USER` | chips, emails, equipment, discador, helpdesk | Todos | Sim | Sim | Todos |
| Administrador | `ADMIN` | helpdesk | Todos | Sim | Sim | Todos |
| Supervisor | `SUPERVISOR` | helpdesk | Todos ativos | Não | Não | Qualquer visível |
| Líder de Equipe | `TEAM_LEADER` | helpdesk | Equipes do usuário | Não | Não | Só autor/solicitante/co-autor |
| Multiplicador | `MULTIPLIER` | helpdesk | Próprios + co-autor | Não | Não | Só autor/solicitante/co-autor |
| Usuário Padrão | `STANDARD` | helpdesk | Próprios | Não | Não | Próprios |

**Criação de chamados:**
- `STANDARD`: sempre para si.
- `SUPERVISOR` / `TEAM_LEADER`: equipes das quais é membro; eu / nome livre.
- `MULTIPLIER`: eu / nome livre / co-autor da equipe (M2M `co_authors`).
- `IT_USER` / `ADMIN` / superuser: nome livre ou usuário do sistema.

**Co-autores:** campo `Ticket.co_authors` — concedem visibilidade e permissão de comentário ao multiplicador compartilhar chamados.

**Django Admin:** apenas `is_superuser` (`is_staff=True`). Demais papéis não devem ter acesso ao admin.

Implementação central: `ticket_access.py`. Skill do agente: `.agent/skills/rbac-helpdesk/SKILL.md`.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app. |
| `models.py` | `TicketCategory`, `Ticket` (status Kanban, prioridade nullable, arquivamento, `created_by`, `requester_user`, `co_authors`) e `Comment`. |
| `forms.py` | `TicketCreateForm` (campos por papel) e `TicketUpdateForm` (edição). |
| `ticket_access.py` | Filtro de chamados, permissões por papel, co-autores. |
| `context_processors.py` | Flags `eh_operador_helpdesk`, `pode_operar_kanban`, `pode_acessar_dashboard_helpdesk`. |
| `audit.py` | Wrappers de `registrar_acao` para eventos do helpdesk. |
| `urls.py` | Rotas sob `/helpdesk/`. |
| `views/` | Lógica de telas e APIs parciais. Ver `views/DOCUMENTACAO.md`. |
| `templates/` | Front do helpdesk. Ver `templates/DOCUMENTACAO.md`. |

## Status do Kanban (`Ticket.StatusChoices`)

Novos → Em Atendimento → Pendente → Resolvido (arquivamento automático após 2 dias resolvido ou 24h recusado).
