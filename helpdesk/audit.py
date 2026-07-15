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


def log_comentario(ticket, actor, texto, metadata=None):
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.COMMENT,
        descricao=f'Comentário no chamado "{ticket.title}": {texto[:120]}',
        actor=actor,
        obj=ticket,
        metadata=metadata or {},
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


def log_contestacao(ticket, actor, motivo, finalized_by_nome):
    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.STATUS_CHANGED,
        descricao=(
            f'Chamado "{ticket.title}" contestado por {actor.get_full_name() or actor.username}. '
            f'Havia sido finalizado por {finalized_by_nome}. Motivo: {motivo[:120]}'
        ),
        actor=actor,
        obj=ticket,
        metadata={'motivo': motivo, 'finalized_by': finalized_by_nome},
    )


def log_prioridade_alterada(ticket, actor, prioridade_anterior, prioridade_nova):
    from helpdesk.models import Ticket

    def _rotulo(valor):
        if not valor:
            return 'Sem prioridade'
        return dict(Ticket.PriorityChoices.choices).get(valor, valor)

    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=(
            f'Prioridade do chamado "{ticket.title}" alterada de '
            f'{_rotulo(prioridade_anterior)} para {_rotulo(prioridade_nova)}.'
        ),
        actor=actor,
        obj=ticket,
        metadata={'priority': {'antes': prioridade_anterior, 'depois': prioridade_nova}},
    )


def log_triagem_alterada(ticket, actor, categoria_anterior, categoria_nova):
    def _rotulo(cat):
        return cat.name if cat else 'Nenhuma'

    return registrar_acao(
        modulo=MODULO_HELPDESK,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=(
            f'Triagem do chamado "{ticket.title}" alterada de '
            f'{_rotulo(categoria_anterior)} para {_rotulo(categoria_nova)}.'
        ),
        actor=actor,
        obj=ticket,
        metadata={
            'specific_category': {
                'antes': categoria_anterior.pk if categoria_anterior else None,
                'depois': categoria_nova.pk if categoria_nova else None,
            }
        },
    )
