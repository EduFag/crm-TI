import time
from django.http import StreamingHttpResponse
from django.utils import timezone
from core.permissions import MODULO_HELPDESK, requer_modulo
from helpdesk.models import Ticket

# Duração máxima da conexão SSE (segundos). Libera o worker do Gunicorn; o HTMX reconecta sozinho.
_SSE_MAX_SEGUNDOS = 240

@requer_modulo(MODULO_HELPDESK)
def sse_stream(request):
    """
    Mantém uma conexão SSE aberta (WSGI) e faz polling no banco de dados.
    Dispara o evento 'ticket_updated' se ocorrer alguma alteração.
    """
    def event_stream():
        last_check = timezone.now()
        inicio = time.monotonic()

        while time.monotonic() - inicio < _SSE_MAX_SEGUNDOS:
            # Polling: Verifica modificações desde a última checagem
            has_changes = Ticket.objects.filter(updated_at__gt=last_check).exists()
            
            if has_changes:
                last_check = timezone.now()
                # O HTMX escutará esse evento para fazer o partial update
                yield "event: ticket_updated\ndata: update\n\n"
            
            # Ping (keep-alive) para evitar que a conexão caia por inatividade
            yield ": ping\n\n"
            time.sleep(2)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no' # Previne buffer do Nginx
    return response
