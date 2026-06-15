"""Wrappers de auditoria do helpdesk."""

from core.audit import registrar_acao
from core.models import RegistroAcao
from core.permissions import MODULO_HELPDESK


def log_chamado_criado(ticket, actor):
    autor = actor.get_full_name() or actor.username if actor else 'Sistema'
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Chamado "{ticket.title}" aberto por {autor}.',
        actor=actor,
        obj=ticket,
        metadata={'status': ticket.status, 'requester_name': ticket.requester_name},
    )


def log_status_alterado(ticket, actor, status_anterior, status_novo):
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.STATUS_CHANGED,
        descricao=(
            f'Status do chamado "{ticket.title}" alterado de '
            f'{status_anterior} para {status_novo}.'
        ),
        actor=actor,
        obj=ticket,
        metadata={'antes': status_anterior, 'depois': status_novo},
    )


def log_atribuicao(ticket, actor, descricao_extra=''):
    texto = f'Chamado "{ticket.title}" atribuído.'
    if descricao_extra:
        texto = f'{texto} {descricao_extra}'
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.ASSIGNED,
        descricao=texto,
        actor=actor,
        obj=ticket,
        metadata={'assigned_to': str(ticket.assigned_to) if ticket.assigned_to else None},
    )


def log_transferencia(ticket, actor, tecnico_anterior, tecnico_novo):
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.TRANSFERRED,
        descricao=(
            f'Técnico do chamado "{ticket.title}" transferido de '
            f'{tecnico_anterior} para {tecnico_novo}.'
        ),
        actor=actor,
        obj=ticket,
    )


def log_edicao(ticket, actor, metadata, descricao):
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=descricao,
        actor=actor,
        obj=ticket,
        metadata=metadata,
    )


def log_comentario(ticket, actor, texto):
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.COMMENT,
        descricao=f'Comentário no chamado "{ticket.title}": {texto[:120]}',
        actor=actor,
        obj=ticket,
    )


def log_chamado_excluido(ticket, actor):
    autor = actor.get_full_name() or actor.username if actor else 'Sistema'
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.DEACTIVATED,
        descricao=f'Chamado "{ticket.title}" excluído por {autor}.',
        actor=actor,
        obj=ticket,
    )


def log_chamado_recusado(ticket, actor, motivo):
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=f'Chamado "{ticket.title}" recusado. Motivo: {motivo}',
        actor=actor,
        obj=ticket,
    )
