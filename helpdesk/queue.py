"""Cálculo dinâmico da posição na fila de atendimento do helpdesk."""

from helpdesk.models import Ticket

# Peso de prioridade (maior = atende antes)
_PESO_PRIORIDADE = {
    Ticket.PriorityChoices.URGENT: 4,
    Ticket.PriorityChoices.HIGH: 3,
    Ticket.PriorityChoices.MEDIUM: 2,
    Ticket.PriorityChoices.LOW: 1,
}

_STATUS_FILA = (
    Ticket.StatusChoices.NEW,
    Ticket.StatusChoices.IN_PROGRESS,
)


def _chave_ordenacao(ticket) -> tuple:
    """Urgente primeiro; empate pelo pk mais antigo (menor id)."""
    peso = _PESO_PRIORIDADE.get(ticket.priority, 0)
    return (-peso, ticket.pk)


def calcular_posicoes_fila(tickets) -> dict:
    """
    Rankeia chamados em Novos + Em Atendimento.

    Retorna dict {ticket_id: posição 1-based}.
    """
    pool = [t for t in tickets if t.status in _STATUS_FILA]
    pool.sort(key=_chave_ordenacao)
    return {t.pk: indice for indice, t in enumerate(pool, start=1)}


def aplicar_posicoes_fila(tickets_new, tickets_in_progress) -> None:
    """Atribui queue_position nos objetos (só cards Novos usam no template)."""
    posicoes = calcular_posicoes_fila(list(tickets_new) + list(tickets_in_progress))
    for ticket in tickets_new:
        ticket.queue_position = posicoes.get(ticket.pk)
    for ticket in tickets_in_progress:
        ticket.queue_position = posicoes.get(ticket.pk)
