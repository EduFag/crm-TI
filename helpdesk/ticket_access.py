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
    return user.role in (CustomUser.RoleChoices.ADMIN, CustomUser.RoleChoices.IT_USER)


def usuario_pode_acessar_dashboard_e_historico(user) -> bool:
    """Apenas ADMIN e IT_USER podem acessar dashboard e histórico."""
    return _eh_admin_ou_superuser(user)


def usuario_pode_gerenciar_categorias(user) -> bool:
    """ADMIN e superusuário podem criar categorias no modal de novo chamado."""
    return _eh_admin_ou_superuser(user)


def usuario_pode_definir_prioridade(user) -> bool:
    """Somente ADMIN e superusuário definem prioridade na criação ou edição."""
    return _eh_admin_ou_superuser(user)


def usuario_pode_editar_chamado(user, ticket=None) -> bool:
    """Administradores e usuários de TI podem editar qualquer chamado. STANDARD e SUPERVISOR apenas os que têm acesso."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role in (CustomUser.RoleChoices.ADMIN, CustomUser.RoleChoices.IT_USER):
        return True
    if ticket:
        return usuario_pode_acessar_chamado(user, ticket)
    return True


def usuario_pode_transferir_chamado(user) -> bool:
    """Somente ADMIN e superusuário podem transferir técnico responsável."""
    return _eh_admin_ou_superuser(user)


def usuario_pode_excluir_chamado(user, ticket=None) -> bool:
    """Administradores e usuários de TI podem excluir qualquer chamado. STANDARD e SUPERVISOR apenas os que têm acesso."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role in (CustomUser.RoleChoices.ADMIN, CustomUser.RoleChoices.IT_USER):
        return True
    if ticket:
        return usuario_pode_acessar_chamado(user, ticket)
    return True


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
    if not user.equipes.exists():
        return CustomUser.objects.filter(pk=user.pk, is_active=True)
    return CustomUser.objects.filter(
        is_active=True,
        equipes__in=user.equipes.all(),
    ).distinct().order_by('first_name', 'last_name', 'username')


def usuarios_tecnicos_para_transferencia() -> QuerySet:
    """Técnicos disponíveis para transferência: usuários ADMIN e IT_USER ativos."""
    return CustomUser.objects.filter(
        is_active=True,
        role__in=[CustomUser.RoleChoices.ADMIN, CustomUser.RoleChoices.IT_USER],
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
    return queryset.filter(_filtro_chamados_proprios(user)).distinct()


def usuario_pode_acessar_chamado(user, ticket) -> bool:
    """Verifica se o usuário pode visualizar ou interagir com um chamado específico."""
    if usuario_ve_todos_chamados(user):
        return True
    if ticket.created_by_id == user.pk:
        return True
    if ticket.requester_user_id == user.pk:
        return True
        
    if getattr(user, 'role', None) == CustomUser.RoleChoices.SUPERVISOR:
        equipes_user = user.equipes.all()
        if equipes_user.exists():
            if ticket.equipe_id and ticket.equipe_id in [e.id for e in equipes_user]:
                return True
            if ticket.created_by_id and ticket.created_by.equipes.filter(id__in=equipes_user).exists():
                return True
            if ticket.requester_user_id and ticket.requester_user.equipes.filter(id__in=equipes_user).exists():
                return True
            
    if ticket.created_by_id is not None:
        return False
    nome = (user.get_full_name() or user.username).strip().lower()
    solicitante = ticket.requester_name.strip().lower()
    return solicitante in (nome, user.username.strip().lower())


def usuario_pode_ver_quem_abriu_chamado(user, ticket) -> bool:
    """
    Solicitante vinculado por FK só vê quem abriu o chamado se for ele mesmo.
    Quem abriu e perfis avançados sempre veem.
    """
    if usuario_ve_todos_chamados(user):
        return True
    if getattr(user, 'role', None) == CustomUser.RoleChoices.SUPERVISOR:
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
    Se for SUPERVISOR, inclui chamados de toda a sua equipe.
    """
    nome = (user.get_full_name() or user.username).strip()
    q = (
        Q(created_by=user)
        | Q(requester_user=user)
        | Q(created_by__isnull=True, requester_name__iexact=nome)
        | Q(created_by__isnull=True, requester_name__iexact=user.username)
    )
    if getattr(user, 'role', None) == CustomUser.RoleChoices.SUPERVISOR:
        equipes_user = user.equipes.all()
        if equipes_user.exists():
            q = q | Q(equipe__in=equipes_user) | Q(created_by__equipes__in=equipes_user) | Q(requester_user__equipes__in=equipes_user)
    return q
