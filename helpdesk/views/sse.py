import time
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from helpdesk.models import Ticket

@login_required
def sse_stream(request):
    """
    Mantém uma conexão SSE aberta (WSGI) e faz polling no banco de dados.
    Dispara o evento 'ticket_updated' se ocorrer alguma alteração.
    """
    def event_stream():
        last_check = timezone.now()
        
        while True:
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
