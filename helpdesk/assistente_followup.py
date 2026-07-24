"""
Follow-up automático do Assistente quando solicitante/criador não responde.

- 5 min sem resposta → mensagem pública com @menção
- 20 min sem resposta → recusa com motivo "Sem resposta"

Disparado de forma leve no poll HTMX (com throttle), como o arquivamento.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

SEGUNDOS_MENCAO = 5 * 60
SEGUNDOS_RECUSA = 20 * 60
THROTTLE_SEGUNDOS = 30

_ultimo_run = None


def limpar_espera_assistente(ticket, *, save: bool = True) -> None:
    """Zera timers de follow-up (resposta do usuário, escalonamento, etc.)."""
    if ticket.assistente_aguardando_desde is None and ticket.assistente_followup_mencao_em is None:
        return
    ticket.assistente_aguardando_desde = None
    ticket.assistente_followup_mencao_em = None
    if save:
        ticket.save(update_fields=[
            'assistente_aguardando_desde',
            'assistente_followup_mencao_em',
            'updated_at',
        ])


def marcar_espera_assistente(ticket) -> None:
    """Inicia/reinicia a espera após mensagem pública normal do Assistente."""
    agora = timezone.now()
    ticket.assistente_aguardando_desde = agora
    ticket.assistente_followup_mencao_em = None
    ticket.save(update_fields=[
        'assistente_aguardando_desde',
        'assistente_followup_mencao_em',
        'updated_at',
    ])


def usuario_e_solicitante_ou_criador(ticket, user) -> bool:
    if not user or not getattr(user, 'pk', None):
        return False
    return user.pk in {
        ticket.requester_user_id,
        ticket.created_by_id,
    }


def _usuarios_para_cobrar(ticket) -> list:
    """Solicitante e/ou criador com conta ativa (para @menção)."""
    vistos = set()
    usuarios = []
    for user in (ticket.requester_user, ticket.created_by):
        if not user or not user.is_active:
            continue
        if user.pk in vistos:
            continue
        vistos.add(user.pk)
        usuarios.append(user)
    return usuarios


def _registrar_mencoes_assistente(ticket, comment, usuarios) -> list:
    """Cria TicketMention + co_authors para cobrança do Assistente."""
    from helpdesk.models import TicketMention

    mencionados = []
    for user in usuarios:
        ticket.co_authors.add(user)
        TicketMention.objects.get_or_create(
            ticket=ticket,
            user=user,
            comment=comment,
            defaults={'mentioned_by': None},
        )
        mencionados.append(user)
    return mencionados


def _enviar_cobranca_mencao(ticket) -> bool:
    """Envia @menção pedindo resposta. Retorna True se enviou."""
    from helpdesk.assistente_services import AssistenteServiceError, send_assistente_message
    from helpdesk.audit import log_comentario
    from helpdesk.models import Comment
    from helpdesk.notifications import (
        EVENTO_COMMENT,
        agendar_notificacao_chamado,
        agendar_notificacao_mencoes,
    )
    from helpdesk.views.kanban import adicionar_nao_lido

    usuarios = _usuarios_para_cobrar(ticket)
    if usuarios:
        tags = ' '.join(f'@{u.username}' for u in usuarios)
        texto = (
            f'{tags}, ainda estou aguardando sua resposta neste chamado para continuar. '
            'Pode responder por aqui, por favor?'
        )
    else:
        nome = (ticket.requester_name or 'solicitante').strip()
        texto = (
            f'{nome}, ainda estou aguardando sua resposta neste chamado para continuar. '
            'Pode responder por aqui, por favor?'
        )

    try:
        resultado = send_assistente_message(
            ticket.pk,
            texto,
            interno=False,
            followup_mencao=True,
        )
    except AssistenteServiceError:
        logger.exception('Falha ao enviar cobrança @ no ticket %s', ticket.pk)
        return False

    comment_id = resultado.get('comment_id')
    comment = Comment.objects.filter(pk=comment_id).first() if comment_id else None
    mencionados = []
    if comment and usuarios:
        mencionados = _registrar_mencoes_assistente(ticket, comment, usuarios)

    preview = texto[:120]
    try:
        meta = {
            'is_assistente': True,
            'followup': 'mencao_5min',
        }
        if mencionados:
            meta['acao_ui'] = 'MENTION'
            meta['mention_user_ids'] = [u.pk for u in mencionados]
        log_comentario(ticket, None, preview, metadata=meta)
    except Exception:
        pass
    try:
        adicionar_nao_lido(ticket, None, usuarios_extra=mencionados or None)
    except Exception:
        pass
    agendar_notificacao_chamado(ticket, None, EVENTO_COMMENT, preview)
    if mencionados:
        agendar_notificacao_mencoes(ticket, mencionados, preview)
    return True


def _recusar_sem_resposta(ticket) -> bool:
    from helpdesk.assistente_services import AssistenteServiceError, recusar_chamado

    try:
        recusar_chamado(ticket.pk, 'Sem resposta')
        return True
    except AssistenteServiceError:
        logger.exception('Falha ao recusar ticket %s por Sem resposta', ticket.pk)
        return False


def processar_followups_assistente(*, forcar: bool = False) -> dict:
    """
    Varre chamados aguardando resposta e aplica menção (5min) / recusa (20min).
    Throttle global de 30s para não sobrecarregar o poll.
    """
    global _ultimo_run

    agora = timezone.now()
    if not forcar and _ultimo_run and (agora - _ultimo_run).total_seconds() < THROTTLE_SEGUNDOS:
        return {'ok': True, 'skipped': True}

    _ultimo_run = agora

    from helpdesk.assistente_services import assistente_pode_atuar
    from helpdesk.models import Ticket

    mencoes = 0
    recusas = 0
    qs = (
        Ticket.objects.filter(
            is_active=True,
            is_archived=False,
            is_rejected=False,
            assistente_escalado=False,
            assistente_aguardando_desde__isnull=False,
        )
        .exclude(status=Ticket.StatusChoices.RESOLVED)
        .select_related('requester_user', 'created_by', 'assigned_to')
        .order_by('assistente_aguardando_desde')[:40]
    )

    for ticket in qs:
        try:
            if not assistente_pode_atuar(ticket):
                limpar_espera_assistente(ticket)
                continue

            espera = agora - ticket.assistente_aguardando_desde
            if espera >= timedelta(seconds=SEGUNDOS_RECUSA):
                desde = ticket.assistente_aguardando_desde
                mencao_em = ticket.assistente_followup_mencao_em
                # Reserva atômica para evitar dupla recusa entre workers
                n = Ticket.objects.filter(
                    pk=ticket.pk,
                    assistente_aguardando_desde=desde,
                    is_rejected=False,
                    assistente_escalado=False,
                ).exclude(status=Ticket.StatusChoices.RESOLVED).update(
                    assistente_aguardando_desde=None,
                    assistente_followup_mencao_em=None,
                    updated_at=agora,
                )
                if n != 1:
                    continue
                if _recusar_sem_resposta(ticket):
                    recusas += 1
                else:
                    Ticket.objects.filter(
                        pk=ticket.pk,
                        assistente_aguardando_desde__isnull=True,
                        is_rejected=False,
                    ).exclude(status=Ticket.StatusChoices.RESOLVED).update(
                        assistente_aguardando_desde=desde,
                        assistente_followup_mencao_em=mencao_em,
                        updated_at=timezone.now(),
                    )
                continue

            if (
                espera >= timedelta(seconds=SEGUNDOS_MENCAO)
                and ticket.assistente_followup_mencao_em is None
            ):
                n = Ticket.objects.filter(
                    pk=ticket.pk,
                    assistente_followup_mencao_em__isnull=True,
                    assistente_aguardando_desde=ticket.assistente_aguardando_desde,
                ).update(
                    assistente_followup_mencao_em=agora,
                    updated_at=agora,
                )
                if n != 1:
                    continue
                ticket.assistente_followup_mencao_em = agora
                if _enviar_cobranca_mencao(ticket):
                    mencoes += 1
                else:
                    # Libera para tentar de novo no próximo ciclo
                    Ticket.objects.filter(pk=ticket.pk).update(
                        assistente_followup_mencao_em=None,
                        updated_at=timezone.now(),
                    )
        except Exception:
            logger.exception('Erro no follow-up do Assistente ticket %s', ticket.pk)

    return {'ok': True, 'mencoes': mencoes, 'recusas': recusas}
