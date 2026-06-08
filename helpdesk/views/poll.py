from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.permissions import MODULO_HELPDESK, requer_modulo
from helpdesk.models import Ticket

_CHAVE_SESSAO_POLL = 'helpdesk_poll_desde'


@requer_modulo(MODULO_HELPDESK)
def poll_ticket_updates(request):
    """
    Verificação leve via HTMX (hx-trigger="every Ns").
    Requisição curta — não mantém socket aberto nem bloqueia worker do Gunicorn.
    """
    agora = timezone.now()
    since_raw = request.session.get(_CHAVE_SESSAO_POLL)

    tem_mudanca = False
    if since_raw:
        since = parse_datetime(since_raw)
        if since is not None:
            if timezone.is_naive(since):
                since = timezone.make_aware(since)
            tem_mudanca = Ticket.objects.filter(updated_at__gt=since).exists()

    request.session[_CHAVE_SESSAO_POLL] = agora.isoformat()
    request.session.modified = True

    if tem_mudanca:
        return HttpResponse(status=200, headers={'HX-Trigger': 'ticketUpdated'})
    return HttpResponse(status=204)
