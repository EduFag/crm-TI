"""Cálculo dinâmico da posição na fila de atendimento do helpdesk."""

from helpdesk.models import Ticket

# Peso de status: Em Atendimento sempre antes de Novo
_PESO_STATUS = {
    Ticket.StatusChoices.IN_PROGRESS: 2,
    Ticket.StatusChoices.NEW: 1,
}

# Peso de prioridade (maior = atende antes), dentro do mesmo status
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
    """
    1) Em Atendimento antes de Novo
    2) Dentro do status: Urgente > Alta > Média > Baixa
    3) Empate: pk mais antigo (menor id)
    """
    peso_status = _PESO_STATUS.get(ticket.status, 0)
    peso_prioridade = _PESO_PRIORIDADE.get(ticket.priority, 0)
    return (-peso_status, -peso_prioridade, ticket.pk)


def calcular_posicoes_fila(tickets) -> dict:
    """
    Rankeia chamados em Novos + Em Atendimento.

    Retorna dict {ticket_id: posição 1-based}.
    """
    pool = [t for t in tickets if t.status in _STATUS_FILA]
    pool.sort(key=_chave_ordenacao)
    return {t.pk: indice for indice, t in enumerate(pool, start=1)}


def calcular_posicoes_fila_global() -> dict:
    """
    Fila global (todos os chamados ativos), independente do que o usuário enxerga.

    Assim, se o TI vê o card na posição 5, o usuário padrão também vê #5
    mesmo visualizando só o próprio card.
    """
    pool = Ticket.objects.filter(
        is_active=True,
        is_archived=False,
        status__in=_STATUS_FILA,
    ).only('pk', 'priority', 'status')
    return calcular_posicoes_fila(pool)


def aplicar_posicoes_fila(tickets_new, tickets_in_progress, posicoes=None) -> None:
    """Atribui queue_position nos objetos visíveis usando a fila global."""
    if posicoes is None:
        posicoes = calcular_posicoes_fila_global()
    for ticket in tickets_new:
        ticket.queue_position = posicoes.get(ticket.pk)
    for ticket in tickets_in_progress:
        ticket.queue_position = posicoes.get(ticket.pk)
