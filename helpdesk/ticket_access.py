"""
Regras de visibilidade de chamados por papel do usuário.
Usuário padrão (STANDARD) vê apenas os chamados que ele próprio abriu ou onde é solicitante.
"""
from django.db.models import Q, QuerySet

from core.models import CustomUser


def _eh_admin_ou_superuser(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role == CustomUser.RoleChoices.ADMIN


def usuario_pode_gerenciar_categorias(user) -> bool:
    """ADMIN e superusuário podem criar categorias no modal de novo chamado."""
    return _eh_admin_ou_superuser(user)


def usuario_pode_definir_prioridade(user) -> bool:
    """Somente ADMIN e superusuário definem prioridade na criação ou edição."""
    return _eh_admin_ou_superuser(user)


def usuario_pode_editar_chamado(user) -> bool:
    """Somente ADMIN e superusuário podem editar chamados."""
    return _eh_admin_ou_superuser(user)


def usuario_pode_transferir_chamado(user) -> bool:
    """Somente ADMIN e superusuário podem transferir técnico responsável."""
    return _eh_admin_ou_superuser(user)


def usuario_pode_operar_kanban(user) -> bool:
    """Administradores e usuários de TI podem mover cards e operar o fluxo do Kanban. Restrito para STANDARD."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role in (CustomUser.RoleChoices.ADMIN, CustomUser.RoleChoices.IT_USER)


def usuarios_solicitantes_equipe(user) -> QuerySet:
    """Membros ativos da mesma equipe do gerente (inclui o próprio gerente)."""
    if not user or not user.is_authenticated:
        return CustomUser.objects.none()
    if not user.equipe_id:
        return CustomUser.objects.filter(pk=user.pk, is_active=True)
    return CustomUser.objects.filter(
        is_active=True,
        equipe_id=user.equipe_id,
    ).order_by('first_name', 'last_name', 'username')


def usuarios_tecnicos_para_transferencia() -> QuerySet:
    """Técnicos disponíveis para transferência: usuários ADMIN ativos."""
    return CustomUser.objects.filter(
        is_active=True,
        role=CustomUser.RoleChoices.ADMIN,
    ).order_by('first_name', 'last_name', 'username')


def usuario_ve_todos_chamados(user) -> bool:
    """ADMIN, MANAGER e superusuário enxergam todos os chamados."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role in (
        CustomUser.RoleChoices.ADMIN,
        CustomUser.RoleChoices.IT_USER,
    )


def filtrar_chamados_para_usuario(queryset: QuerySet, user) -> QuerySet:
    """Restringe o queryset aos chamados do usuário quando o papel for STANDARD."""
    if usuario_ve_todos_chamados(user):
        return queryset
    return queryset.filter(_filtro_chamados_proprios(user))


def usuario_pode_acessar_chamado(user, ticket) -> bool:
    """Verifica se o usuário pode visualizar ou interagir com um chamado específico."""
    if usuario_ve_todos_chamados(user):
        return True
    if ticket.created_by_id == user.pk:
        return True
    if ticket.requester_user_id == user.pk:
        return True
    if ticket.created_by_id is not None:
        return False
    nome = (user.get_full_name() or user.username).strip().lower()
    solicitante = ticket.requester_name.strip().lower()
    return solicitante in (nome, user.username.strip().lower())


def usuario_pode_ver_quem_abriu_chamado(user, ticket) -> bool:
    """
    Solicitante vinculado por FK só vê quem abriu o chamado se for ele mesmo.
    Quem abriu e perfis ADMIN/MANAGER sempre veem.
    """
    if usuario_ve_todos_chamados(user):
        return True
    if ticket.created_by_id == user.pk:
        return True
    if ticket.requester_user_id == user.pk and ticket.created_by_id == user.pk:
        return True
    if ticket.requester_user_id is None and ticket.created_by_id is None:
        return True
    return False


def _filtro_chamados_proprios(user) -> Q:
    """
    Chamados criados pelo usuário logado ou onde ele é solicitante vinculado.
    Inclui legado sem created_by, vinculado pelo nome do solicitante.
    """
    nome = (user.get_full_name() or user.username).strip()
    return (
        Q(created_by=user)
        | Q(requester_user=user)
        | Q(created_by__isnull=True, requester_name__iexact=nome)
        | Q(created_by__isnull=True, requester_name__iexact=user.username)
    )
