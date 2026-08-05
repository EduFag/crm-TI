"""Presença online (heartbeat) dos membros da TI no helpdesk."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from core.models import CustomUser
from helpdesk.models import UserPresence
from helpdesk.ticket_access import usuario_eh_operador_helpdesk

# Janela considerada "online"
ONLINE_SEGUNDOS = 120


def registrar_heartbeat(user) -> UserPresence | None:
    """Atualiza last_seen do usuário autenticado."""
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    agora = timezone.now()
    obj, _ = UserPresence.objects.update_or_create(
        user=user,
        defaults={'last_seen': agora},
    )
    return obj


def usuarios_ti_online(*, excluir_user_id: int | None = None) -> list:
    """Lista membros TI/admin online nos últimos ONLINE_SEGUNDOS."""
    corte = timezone.now() - timedelta(seconds=ONLINE_SEGUNDOS)
    qs = (
        UserPresence.objects.filter(last_seen__gte=corte)
        .select_related('user')
        .order_by('-last_seen')
    )
    online = []
    for presence in qs:
        user = presence.user
        if not user or not user.is_active:
            continue
        if excluir_user_id and user.pk == excluir_user_id:
            continue
        if usuario_eh_operador_helpdesk(user):
            online.append(user)
    return online


def listar_ti_online_resumo() -> list[dict]:
    """Resumo para tool/UI do Assistente."""
    itens = []
    for user in usuarios_ti_online():
        itens.append({
            'user_id': user.pk,
            'username': user.username,
            'nome': user.get_full_name() or user.username,
        })
    return itens
