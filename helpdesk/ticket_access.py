"""
Regras de visibilidade de chamados por papel do usuário.
Usuário padrão (USER) vê apenas os chamados que ele próprio abriu ou onde é solicitante.
"""
from django.db.models import Q, QuerySet

from core.models import CustomUser


def usuario_pode_gerenciar_categorias(user) -> bool:
    """ADMIN e superusuário podem criar categorias no modal de novo chamado."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role == CustomUser.RoleChoices.ADMIN


def usuario_ve_todos_chamados(user) -> bool:
    """ADMIN, MANAGER e superusuário enxergam todos os chamados."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role in (
        CustomUser.RoleChoices.ADMIN,
        CustomUser.RoleChoices.MANAGER,
    )


def filtrar_chamados_para_usuario(queryset: QuerySet, user) -> QuerySet:
    """Restringe o queryset aos chamados do usuário quando o papel for USER."""
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
