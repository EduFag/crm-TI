from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from helpdesk.models import InformativeMessage
from helpdesk.ticket_access import filtrar_mensagens_informativas


@login_required
def informative_center(request):
    """
    Retorna o Drawer inicial da Central Informativa.
    """
    return render(request, 'helpdesk/informative/_drawer.html')


@login_required
def informative_list(request):
    """
    Retorna a lista de mensagens (chat).
    Usado para carregar e fazer o polling.
    """
    qs = filtrar_mensagens_informativas(request.user)
    messages = qs.select_related('created_by').prefetch_related('acknowledged_by')
    
    context = {
        'messages': messages,
    }
    return render(request, 'helpdesk/informative/_list.html', context)


@login_required
def informative_create(request):
    """
    Cria uma nova mensagem informativa.
    """
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            InformativeMessage.objects.create(
                text=text,
                created_by=request.user
            )
    # Retorna a lista atualizada
    return informative_list(request)


@login_required
def informative_acknowledge(request, message_id):
    """
    Alterna o status de 'OK' do usuário na mensagem.
    """
    if request.method == 'POST':
        qs = filtrar_mensagens_informativas(request.user)
        message = get_object_or_404(qs, pk=message_id)
        
        if request.user in message.acknowledged_by.all():
            message.acknowledged_by.remove(request.user)
        else:
            message.acknowledged_by.add(request.user)
            
    # Para ser eficiente e manter o scroll, vamos renderizar apenas a _list
    return informative_list(request)
