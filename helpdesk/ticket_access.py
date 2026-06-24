"""
Regras de visibilidade e permissões de chamados por papel do usuário.
Matriz completa documentada em helpdesk/DOCUMENTACAO.md e .agent/skills/rbac-helpdesk/SKILL.md.
"""
from typing import Optional

from django.db.models import Q, QuerySet

from core.models import CustomUser


def _role(user) -> Optional[str]:
    if not user or not user.is_authenticated:
        return None
    return getattr(user, 'role', None)


def usuario_eh_operador_helpdesk(user) -> bool:
    """Membro TI, Administrador ou superuser — operações completas no helpdesk."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _role(user) in (CustomUser.RoleChoices.ADMIN, CustomUser.RoleChoices.IT_USER)


def usuario_pode_acessar_dashboard_e_historico(user) -> bool:
    """Dashboard e histórico: Membro TI, Administrador ou superuser."""
    return usuario_eh_operador_helpdesk(user)


def usuario_pode_ver_arquivados(user) -> bool:
    """Arquivados visíveis apenas no histórico para operadores helpdesk."""
    return usuario_eh_operador_helpdesk(user)


def usuario_pode_gerenciar_categorias(user) -> bool:
    return usuario_eh_operador_helpdesk(user)


def usuario_pode_definir_prioridade(user) -> bool:
    return usuario_eh_operador_helpdesk(user)


def usuario_pode_transferir_chamado(user) -> bool:
    return usuario_eh_operador_helpdesk(user)


def usuario_pode_operar_kanban(user) -> bool:
    """Somente operadores helpdesk movem cards no Kanban."""
    return usuario_eh_operador_helpdesk(user)


def usuario_ve_todos_chamados(user) -> bool:
    """Visão global no Kanban: operadores, supervisor e superuser."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _role(user) in (
        CustomUser.RoleChoices.ADMIN,
        CustomUser.RoleChoices.IT_USER,
        CustomUser.RoleChoices.SUPERVISOR,
    )


def usuarios_solicitantes_equipe(user) -> QuerySet:
    """Membros ativos das equipes do usuário (inclui o próprio)."""
    if not user or not user.is_authenticated:
        return CustomUser.objects.none()
    if not user.equipes.exists():
        return CustomUser.objects.filter(pk=user.pk, is_active=True)
    return CustomUser.objects.filter(
        is_active=True,
        equipes__in=user.equipes.all(),
    ).distinct().order_by('first_name', 'last_name', 'username')


def usuarios_tecnicos_para_transferencia() -> QuerySet:
    """Técnicos disponíveis para transferência: ADMIN e IT_USER ativos."""
    return CustomUser.objects.filter(
        is_active=True,
        role__in=[CustomUser.RoleChoices.ADMIN, CustomUser.RoleChoices.IT_USER],
    ).order_by('first_name', 'last_name', 'username')


def _filtro_chamados_proprios(user) -> Q:
    """Chamados criados pelo usuário, onde é solicitante ou co-autor."""
    nome = (user.get_full_name() or user.username).strip()
    return (
        Q(created_by=user)
        | Q(requester_user=user)
        | Q(co_authors=user)
        | Q(created_by__isnull=True, requester_name__iexact=nome)
        | Q(created_by__isnull=True, requester_name__iexact=user.username)
    )


def _filtro_chamados_equipe(user) -> Q:
    """Chamados vinculados às equipes do usuário."""
    equipes_user = user.equipes.all()
    if not equipes_user.exists():
        return Q(pk__in=[])
    return (
        Q(equipe__in=equipes_user)
        | Q(created_by__equipes__in=equipes_user)
        | Q(requester_user__equipes__in=equipes_user)
    )


def filtrar_chamados_para_usuario(queryset: QuerySet, user) -> QuerySet:
    """Restringe queryset conforme papel do usuário."""
    if usuario_ve_todos_chamados(user):
        return queryset
    role = _role(user)
    if role == CustomUser.RoleChoices.TEAM_LEADER:
        filtro = _filtro_chamados_equipe(user) | _filtro_chamados_proprios(user)
    else:
        filtro = _filtro_chamados_proprios(user)
    # distinct() + order_by com M2M quebra no PostgreSQL — filtra por PK
    ids = queryset.filter(filtro).values_list('pk', flat=True).distinct()
    return queryset.filter(pk__in=ids)


def usuario_pode_acessar_chamado(user, ticket) -> bool:
    """Verifica se o usuário pode visualizar um chamado específico."""
    if not user or not user.is_authenticated:
        return False
    if usuario_ve_todos_chamados(user):
        return True
    qs = type(ticket).objects.filter(pk=ticket.pk)
    return filtrar_chamados_para_usuario(qs, user).exists()


def usuario_eh_autor_ou_coautor(user, ticket) -> bool:
    """Autor (quem abriu), solicitante vinculado ou co-autor."""
    if ticket.created_by_id == user.pk:
        return True
    if ticket.requester_user_id == user.pk:
        return True
    return ticket.co_authors.filter(pk=user.pk).exists()


def usuario_pode_comentar_chamado(user, ticket) -> bool:
    """Regras de comentário por papel."""
    if not usuario_pode_acessar_chamado(user, ticket):
        return False
    if usuario_eh_operador_helpdesk(user):
        return True
    role = _role(user)
    if role == CustomUser.RoleChoices.SUPERVISOR:
        return True
    if role in (CustomUser.RoleChoices.TEAM_LEADER, CustomUser.RoleChoices.MULTIPLIER):
        return usuario_eh_autor_ou_coautor(user, ticket)
    return True


def usuario_pode_editar_chamado(user, ticket=None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if usuario_eh_operador_helpdesk(user):
        return True
    if ticket:
        return usuario_pode_acessar_chamado(user, ticket) and usuario_eh_autor_ou_coautor(user, ticket)
    return False


def usuario_pode_excluir_chamado(user, ticket=None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if usuario_eh_operador_helpdesk(user):
        return True
    if ticket:
        return usuario_pode_acessar_chamado(user, ticket) and usuario_eh_autor_ou_coautor(user, ticket)
    return False


def usuario_pode_ver_quem_abriu_chamado(user, ticket) -> bool:
    """Solicitante vinculado só vê quem abriu se for ele mesmo; perfis avançados sempre veem."""
    if usuario_eh_operador_helpdesk(user):
        return True
    role = _role(user)
    if role in (CustomUser.RoleChoices.SUPERVISOR, CustomUser.RoleChoices.TEAM_LEADER):
        return True
    if ticket.created_by_id == user.pk:
        return True
    if ticket.requester_user_id == user.pk and ticket.created_by_id == user.pk:
        return True
    if usuario_eh_autor_ou_coautor(user, ticket):
        return True
    if ticket.requester_user_id is None and ticket.created_by_id is None:
        return True
    return False
