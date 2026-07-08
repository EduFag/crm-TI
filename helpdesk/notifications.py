"""Envio de notificações Web Push para eventos de chamados."""

import json
import logging
import time

from django.conf import settings

from helpdesk.models import PushSubscription, Ticket
from helpdesk.ticket_access import usuario_pode_acessar_chamado

logger = logging.getLogger(__name__)

# Tipos de evento reconhecidos pelo frontend e pelo poll
EVENTO_COMMENT = 'COMMENT'
EVENTO_STATUS_CHANGED = 'STATUS_CHANGED'
EVENTO_PRIORITY_CHANGED = 'PRIORITY_CHANGED'
EVENTO_TRIAGE_CHANGED = 'TRIAGE_CHANGED'

_TITULOS_EVENTO = {
    EVENTO_COMMENT: 'Novo comentário',
    EVENTO_STATUS_CHANGED: 'Chamado movido',
    EVENTO_PRIORITY_CHANGED: 'Prioridade alterada',
    EVENTO_TRIAGE_CHANGED: 'Triagem alterada',
}


def _vapid_configurado() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def destinatarios_notificacao(ticket: Ticket, actor):
    """Usuários com acesso ao chamado que devem receber push (exceto o ator)."""
    from core.models import CustomUser

    candidatos = []
    if ticket.created_by_id:
        candidatos.append(ticket.created_by_id)
    if ticket.requester_user_id:
        candidatos.append(ticket.requester_user_id)
    if ticket.assigned_to_id:
        candidatos.append(ticket.assigned_to_id)
    else:
        # Se não está atribuído a ninguém (ex: coluna Novos), todos os operadores que podem ver
        # o chamado devem ser notificados.
        from django.db.models import Q
        roles_operadores = [
            CustomUser.RoleChoices.ADMIN,
            CustomUser.RoleChoices.IT_USER,
            CustomUser.RoleChoices.SUPERVISOR,
        ]
        operadores_ids = list(CustomUser.objects.filter(
            Q(role__in=roles_operadores) | Q(is_superuser=True),
            is_active=True
        ).values_list('pk', flat=True))
        candidatos.extend(operadores_ids)

    co_author_ids = list(ticket.co_authors.values_list('pk', flat=True))
    user_ids = set(candidatos + co_author_ids)

    actor_id = getattr(actor, 'pk', None) if actor else None
    if actor_id:
        user_ids.discard(actor_id)

    if not user_ids:
        return CustomUser.objects.none()

    usuarios = CustomUser.objects.filter(pk__in=user_ids, is_active=True)
    return [u for u in usuarios if usuario_pode_acessar_chamado(u, ticket)]


def _url_chamado(ticket_id: int) -> str:
    return f'/helpdesk/?ticket={ticket_id}'


def enviar_push_usuario(user, titulo: str, corpo: str, url: str, tag: str) -> None:
    """Envia push para todas as subscriptions ativas do usuário."""
    if not _vapid_configurado():
        return

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning('pywebpush não instalado — push ignorado.')
        return

    payload = json.dumps({
        'title': titulo,
        'body': corpo,
        'url': url,
        'tag': tag,
    })

    vapid_claims = {'sub': settings.VAPID_ADMIN_EMAIL}

    subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
    for sub in subscriptions:
        subscription_info = {
            'endpoint': sub.endpoint,
            'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
        except WebPushException as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            if status in (404, 410):
                sub.is_active = False
                sub.save(update_fields=['is_active'])
            else:
                logger.warning('Falha ao enviar push para subscription %s: %s', sub.pk, exc)
        except Exception as exc:
            logger.warning('Erro inesperado ao enviar push: %s', exc)


def notificar_evento_chamado(ticket: Ticket, actor, tipo: str, mensagem: str) -> None:
    """Dispara push para stakeholders do chamado conforme o tipo de evento."""
    titulo_base = _TITULOS_EVENTO.get(tipo, 'Atualização no helpdesk')
    titulo = f'{titulo_base}: #{ticket.pk}'
    corpo = f'{ticket.title}\n{mensagem}' if mensagem else ticket.title
    url = _url_chamado(ticket.pk)
    # Tag única por evento — mesma tag faz Chrome/Windows substituir sem novo toast
    tag = f'helpdesk-{ticket.pk}-{tipo}-{int(time.time() * 1000)}'

    for usuario in destinatarios_notificacao(ticket, actor):
        enviar_push_usuario(usuario, titulo, corpo, url, tag)


def agendar_notificacao_chamado(ticket: Ticket, actor, tipo: str, mensagem: str) -> None:
    """Agenda push após commit da transação atual."""
    from django.db import transaction

    ticket_id = ticket.pk

    def _disparar():
        from django.db import close_old_connections
        close_old_connections()
        try:
            ticket_atual = Ticket.objects.get(pk=ticket_id)
            notificar_evento_chamado(ticket_atual, actor, tipo, mensagem)
        except Ticket.DoesNotExist:
            pass
        finally:
            close_old_connections()

    def _disparar_async():
        import threading
        threading.Thread(target=_disparar, daemon=True).start()

    transaction.on_commit(_disparar_async)
