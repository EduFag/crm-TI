import json
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.permissions import MODULO_HELPDESK, requer_modulo
from helpdesk.models import PushSubscription


@cache_control(max_age=0, no_cache=True, must_revalidate=True)
@require_http_methods(['GET', 'HEAD'])
def service_worker_js(request):
    """Serve o SW em /helpdesk/sw.js para escopo correto do Push."""
    caminho = finders.find('helpdesk/sw.js')
    if not caminho:
        return HttpResponse('// Service Worker não encontrado', status=404, content_type='application/javascript')

    resposta = HttpResponse(content_type='application/javascript; charset=utf-8')
    resposta['Service-Worker-Allowed'] = '/helpdesk/'

    if request.method == 'GET':
        conteudo = Path(caminho).read_text(encoding='utf-8')
        versao = getattr(settings, 'HELPDESK_FRONTEND_VERSION', '1')
        conteudo = conteudo.replace('__HELPDESK_FRONTEND_VERSION__', versao)
        resposta.content = conteudo

    return resposta


@requer_modulo(MODULO_HELPDESK)
@require_GET
def push_status(request):
    """Indica se o usuário já tem subscription ativa no servidor."""
    total = PushSubscription.objects.filter(user=request.user, is_active=True).count()
    return JsonResponse({
        'configured': bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY),
        'subscriptions': total,
        'registered': total > 0,
    })


@requer_modulo(MODULO_HELPDESK)
@require_GET
def push_vapid_public_key(request):
    """Retorna a chave pública VAPID para inscrição no browser."""
    chave = settings.VAPID_PUBLIC_KEY
    if not chave or not settings.VAPID_PRIVATE_KEY:
        return JsonResponse({'error': 'Web Push não configurado no servidor.'}, status=503)
    return JsonResponse({'publicKey': chave})


@requer_modulo(MODULO_HELPDESK)
@require_POST
def push_subscribe(request):
    """Salva ou reativa a subscription Web Push do usuário."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    endpoint = data.get('endpoint')
    keys = data.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return JsonResponse({'success': False, 'error': 'Dados de subscription incompletos'}, status=400)

    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    sub, created = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            'user': request.user,
            'p256dh': p256dh,
            'auth': auth,
            'user_agent': user_agent,
            'is_active': True,
        },
    )
    return JsonResponse({'success': True, 'created': created, 'id': sub.pk})


@requer_modulo(MODULO_HELPDESK)
@require_POST
def push_unsubscribe(request):
    """Desativa a subscription Web Push informada."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    endpoint = data.get('endpoint')
    if not endpoint:
        return JsonResponse({'success': False, 'error': 'Endpoint obrigatório'}, status=400)

    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).update(is_active=False)
    return JsonResponse({'success': True})
