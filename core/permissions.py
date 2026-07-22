"""
Controle de acesso por módulo (RBAC) baseado no campo role do CustomUser.
Superusuários ignoram todas as restrições.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect

from core.models import CustomUser

# Códigos dos módulos do sistema (menu lateral e proteção de views)
MODULO_HELPDESK = 'helpdesk'
MODULO_CHIPS = 'chips'
MODULO_EMAILS = 'emails'
MODULO_EQUIPMENT = 'equipment'
MODULO_DISCADOR = 'discador'
MODULO_GESTAO_USUARIOS = 'gestao_usuarios'
MODULO_INTEGRACOES = 'integracoes'

TODOS_MODULOS = frozenset({
    MODULO_HELPDESK,
    MODULO_CHIPS,
    MODULO_EMAILS,
    MODULO_EQUIPMENT,
    MODULO_DISCADOR,
    MODULO_GESTAO_USUARIOS,
    MODULO_INTEGRACOES,
})

# Matriz role → módulos permitidos
MODULOS_POR_ROLE: dict[str, frozenset[str]] = {
    CustomUser.RoleChoices.STANDARD: frozenset({MODULO_HELPDESK}),
    CustomUser.RoleChoices.MULTIPLIER: frozenset({MODULO_HELPDESK}),
    CustomUser.RoleChoices.TEAM_LEADER: frozenset({MODULO_HELPDESK}),
    CustomUser.RoleChoices.SUPERVISOR: frozenset({MODULO_HELPDESK}),
    CustomUser.RoleChoices.IT_USER: frozenset({
        MODULO_HELPDESK,
        MODULO_CHIPS,
        MODULO_EMAILS,
        MODULO_EQUIPMENT,
        MODULO_DISCADOR,
        MODULO_GESTAO_USUARIOS,
        MODULO_INTEGRACOES,
    }),
    CustomUser.RoleChoices.ADMIN: frozenset({MODULO_HELPDESK}),
}


def usuario_pode_acessar_modulo(user, modulo: str) -> bool:
    """Verifica se o usuário autenticado pode acessar o módulo informado."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'role', CustomUser.RoleChoices.STANDARD)
    modulos = MODULOS_POR_ROLE.get(role, frozenset())
    return modulo in modulos


def modulos_permitidos_para_usuario(user) -> list[str]:
    """Retorna lista ordenada de módulos que o usuário pode ver no menu."""
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return sorted(TODOS_MODULOS)
    role = getattr(user, 'role', CustomUser.RoleChoices.STANDARD)
    return sorted(MODULOS_POR_ROLE.get(role, frozenset()))


def resposta_sem_permissao(request):
    """Resposta padrão quando o usuário não tem acesso ao módulo."""
    if request.headers.get('HX-Request'):
        return HttpResponseForbidden('Sem permissão para acessar este módulo.')
    if request.content_type == 'application/json' or request.META.get('HTTP_ACCEPT', '').startswith('application/json'):
        return JsonResponse({'error': 'Sem permissão para acessar este módulo.'}, status=403)
    return redirect('sem_permissao')


def requer_modulo(modulo: str):
    """Decorator para views function-based que exigem acesso a um módulo."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not usuario_pode_acessar_modulo(request.user, modulo):
                return resposta_sem_permissao(request)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class ModuloObrigatorioMixin(LoginRequiredMixin):
    """
    Mixin para class-based views: exige login e permissão no módulo definido.
    Subclasses devem definir modulo_obrigatorio (string) ou None para só exigir login.
    """
    modulo_obrigatorio: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.modulo_obrigatorio and not usuario_pode_acessar_modulo(request.user, self.modulo_obrigatorio):
            return resposta_sem_permissao(request)
        return super().dispatch(request, *args, **kwargs)
