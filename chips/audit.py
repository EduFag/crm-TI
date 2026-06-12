"""Wrappers de auditoria do módulo chips."""

from core.audit import registrar_acao, registrar_alteracoes
from core.models import RegistroAcao
from core.permissions import MODULO_CHIPS


def log_chip_criado(chip, actor):
    return registrar_acao(
        modulo=MODULO_CHIPS,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Chip {chip.line_number} cadastrado.',
        actor=actor,
        obj=chip,
    )


def log_chip_atualizado(chip, actor, antes):
    return registrar_alteracoes(
        modulo=MODULO_CHIPS,
        actor=actor,
        obj_antes=antes,
        obj_depois=chip,
        campos=[
            'line_number', 'status', 'technology',
            'iccid', 'plan_type', 'operator_id', 'batch_id', 'activated_at',
        ],
        descricao_prefixo=f'Chip {chip.line_number} atualizado.',
    )


def log_operadora_criada(operator, actor):
    return registrar_acao(
        modulo=MODULO_CHIPS,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Operadora "{operator.name}" cadastrada.',
        actor=actor,
        obj=operator,
    )


def log_lote_criado(batch, actor):
    name_str = batch.nome or f"#{batch.id}"
    return registrar_acao(
        modulo=MODULO_CHIPS,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Envelope "{name_str}" cadastrado.',
        actor=actor,
        obj=batch,
    )


def log_entrega(chip, employee_name, actor):
    return registrar_acao(
        modulo=MODULO_CHIPS,
        acao=RegistroAcao.AcaoChoices.DELIVERY,
        descricao=f'Chip {chip.line_number} entregue para {employee_name}.',
        actor=actor,
        obj=chip,
        metadata={'employee_name': employee_name},
    )


def log_devolucao(chip, employee_name, actor):
    return registrar_acao(
        modulo=MODULO_CHIPS,
        acao=RegistroAcao.AcaoChoices.RETURNED,
        descricao=f'Chip {chip.line_number} devolvido por {employee_name}.',
        actor=actor,
        obj=chip,
        metadata={'employee_name': employee_name},
    )


def log_transferencia(chip, employee_anterior, employee_novo, actor):
    return registrar_acao(
        modulo=MODULO_CHIPS,
        acao=RegistroAcao.AcaoChoices.TRANSFERRED,
        descricao=(
            f'Chip {chip.line_number} transferido de {employee_anterior} '
            f'para {employee_novo}.'
        ),
        actor=actor,
        obj=chip,
    )


def log_recarga(recharge, actor):
    return registrar_acao(
        modulo=MODULO_CHIPS,
        acao=RegistroAcao.AcaoChoices.RECHARGE,
        descricao=f'Recarga de R$ {recharge.amount} no chip {recharge.chip.line_number}.',
        actor=actor,
        obj=recharge.chip,
        metadata={'amount': str(recharge.amount)},
    )
