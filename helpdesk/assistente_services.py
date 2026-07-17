"""Serviços de escrita do Assistente (usados pelo MCP e pelo runtime Django)."""

from __future__ import annotations

from django.utils import timezone

from helpdesk.models import Comment, Ticket
from helpdesk.ticket_access import usuario_eh_operador_helpdesk


PRIORIDADES = {c.value for c in Ticket.PriorityChoices}
STATUS_VALIDOS = {c.value for c in Ticket.StatusChoices}


class AssistenteServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def ticket_assumido_pela_ti(ticket: Ticket) -> bool:
    return usuario_eh_operador_helpdesk(ticket.assigned_to)


def assistente_pode_atuar(ticket: Ticket) -> bool:
    """Regras para o Assistente continuar conversando no chamado."""
    from integracoes.models import AssistenteConfig

    config = AssistenteConfig.get_solo()
    if not config.ativo:
        return False
    if not ticket.is_active or ticket.is_archived:
        return False
    if ticket.status == Ticket.StatusChoices.RESOLVED:
        return False
    if ticket.assistente_escalado:
        return False
    if ticket_assumido_pela_ti(ticket):
        return False
    if usuario_eh_operador_helpdesk(ticket.created_by):
        return False
    return True


def send_assistente_message(ticket_id: int, text: str) -> dict:
    texto = (text or '').strip()
    if not texto:
        raise AssistenteServiceError('Texto do comentário é obrigatório.')
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    comment = Comment.objects.create(
        ticket=ticket,
        author=None,
        text=texto,
        is_assistente=True,
    )
    ticket.updated_at = timezone.now()
    ticket.save(update_fields=['updated_at'])
    return {
        'ok': True,
        'comment_id': comment.pk,
        'ticket_id': ticket.pk,
        'text': comment.text,
    }


def set_ticket_priority(ticket_id: int, priority: str) -> dict:
    priority = (priority or '').strip().upper()
    if priority not in PRIORIDADES:
        raise AssistenteServiceError(f'Prioridade inválida. Use: {", ".join(sorted(PRIORIDADES))}.')
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    antes = ticket.priority
    ticket.priority = priority
    ticket.save(update_fields=['priority', 'updated_at'])
    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'priority_antes': antes,
        'priority': ticket.priority,
    }


def set_ticket_status(ticket_id: int, status: str) -> dict:
    status = (status or '').strip().upper()
    if status not in STATUS_VALIDOS:
        raise AssistenteServiceError(f'Status inválido. Use: {", ".join(sorted(STATUS_VALIDOS))}.')
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    antes = ticket.status
    ticket.status = status
    update_fields = ['status', 'updated_at']
    if status == Ticket.StatusChoices.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
        update_fields.append('resolved_at')
    ticket.save(update_fields=update_fields)
    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'status_antes': antes,
        'status': ticket.status,
    }


def escalar_para_ti(ticket_id: int, motivo: str = '') -> dict:
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    ticket.assistente_escalado = True
    update_fields = ['assistente_escalado', 'updated_at']
    if ticket.status == Ticket.StatusChoices.NEW:
        ticket.status = Ticket.StatusChoices.PENDING
        update_fields.append('status')
    ticket.save(update_fields=update_fields)

    motivo_limpo = (motivo or '').strip()
    texto = (
        'Encaminhei este chamado para a equipe de TI analisar. '
        'Um técnico assumirá o atendimento em breve.'
    )
    if motivo_limpo:
        texto = f'{texto}\n\nMotivo: {motivo_limpo}'
    comment = Comment.objects.create(
        ticket=ticket,
        author=None,
        text=texto,
        is_assistente=True,
    )
    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'assistente_escalado': True,
        'status': ticket.status,
        'comment_id': comment.pk,
    }
