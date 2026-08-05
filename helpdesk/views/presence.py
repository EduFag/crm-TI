"""Heartbeat de presença online no helpdesk."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from helpdesk.presence import listar_ti_online_resumo, registrar_heartbeat
from helpdesk.ticket_access import usuario_eh_operador_helpdesk


@login_required
@require_POST
def presence_heartbeat(request):
    """Atualiza last_seen do usuário logado."""
    registrar_heartbeat(request.user)
    payload = {'ok': True}
    if usuario_eh_operador_helpdesk(request.user):
        payload['ti_online'] = listar_ti_online_resumo()
    return JsonResponse(payload)


@login_required
def presence_ti_online(request):
    """Lista TI online (para UI do drawer)."""
    if not usuario_eh_operador_helpdesk(request.user):
        return JsonResponse({'results': []}, status=403)
    return JsonResponse({'ok': True, 'results': listar_ti_online_resumo()})
