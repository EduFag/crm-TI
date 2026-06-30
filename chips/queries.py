"""Consultas e anotações reutilizáveis do módulo chips."""

from datetime import timedelta

from django.db.models import OuterRef, Subquery
from django.utils import timezone

from chips.models import Chip, ChipMovement, Recharge


def _ultima_entrega_subquery():
    return ChipMovement.objects.filter(
        chip=OuterRef('pk'),
        action__in=[
            ChipMovement.ActionChoices.DELIVERY,
            ChipMovement.ActionChoices.TRANSFER,
        ],
    ).order_by('-timestamp')


def _ultimo_movimento_subquery():
    return ChipMovement.objects.filter(chip=OuterRef('pk')).order_by('-timestamp')


def chips_com_anotacoes_operacionais(queryset=None):
    """Anota chips com titular, recargas e datas do ciclo."""
    qs = queryset if queryset is not None else Chip.objects.all()

    ultima_entrega = _ultima_entrega_subquery()
    ultimo_movimento = _ultimo_movimento_subquery()
    ultima_recarga = Recharge.objects.filter(chip=OuterRef('pk')).order_by('-timestamp')

    return qs.select_related('operator', 'batch').annotate(
        employee_name=Subquery(ultima_entrega.values('employee_name')[:1]),
        employee_user_id=Subquery(ultima_entrega.values('employee_user_id')[:1]),
        last_delivery_at=Subquery(ultima_entrega.values('timestamp')[:1]),
        last_movement_at=Subquery(ultimo_movimento.values('timestamp')[:1]),
        last_recharge_at=Subquery(ultima_recarga.values('timestamp')[:1]),
    )


def _para_data(valor):
    """Converte datetime/date anotado para date com segurança."""
    if not valor:
        return None
    if hasattr(valor, 'hour'):
        try:
            return timezone.localtime(valor).date()
        except (ValueError, TypeError):
            # datetime ingênuo ou tipo inesperado
            if hasattr(valor, 'date'):
                return valor.date()
    if hasattr(valor, 'isoformat') and hasattr(valor, 'year') and not hasattr(valor, 'hour'):
        return valor
    return valor


def chips_operacionais():
    """Chips visíveis no grid do callcenter (em uso ou na TI)."""
    return chips_com_anotacoes_operacionais(
        Chip.objects.filter(
            is_active=True,
        ).exclude(status=Chip.StatusChoices.CANCELED)
    )


def _calcular_ciclo(chip):
    """Calcula vencimento e dias restantes do ciclo de 90 dias."""
    cycle_start = None
    if chip.last_recharge_at:
        cycle_start = _para_data(chip.last_recharge_at)
    elif chip.activated_at:
        cycle_start = chip.activated_at

    if not cycle_start:
        return None, None, 'ok'

    recharge_due_at = cycle_start + timedelta(days=90)
    days_to_recharge = (recharge_due_at - timezone.localdate()).days

    if days_to_recharge < 0:
        status = 'overdue'
    elif days_to_recharge <= 5:
        status = 'danger'
    elif days_to_recharge <= 10:
        status = 'warning'
    else:
        status = 'ok'

    return recharge_due_at, days_to_recharge, status


def chip_para_grid_dict(chip):
    """Serializa um chip anotado para JSON do Tabulator."""
    envelope_label = chip.batch.label if chip.batch_id else ''
    recharge_due_at, days_to_recharge, recharge_status = _calcular_ciclo(chip)

    return {
        'id': chip.id,
        'line_number': chip.line_number,
        'employee_name': chip.employee_name or '',
        'employee_user_id': chip.employee_user_id,
        'activated_at': chip.activated_at.isoformat() if chip.activated_at else '',
        'last_delivery_at': (
            _para_data(chip.last_delivery_at).isoformat()
            if chip.last_delivery_at else ''
        ),
        'last_recharge_at': (
            _para_data(chip.last_recharge_at).isoformat()
            if chip.last_recharge_at else ''
        ),
        'last_blocked_at': (
            _para_data(chip.last_blocked_at).isoformat()
            if chip.last_blocked_at else ''
        ),
        'operator_id': chip.operator_id,
        'operator_name': chip.operator.name,
        'batch_id': chip.batch_id,
        'envelope_label': envelope_label,
        'status': chip.status,
        'recharge_due_at': recharge_due_at.isoformat() if recharge_due_at else '',
        'days_to_recharge': days_to_recharge,
        'recharge_status': recharge_status,
    }
