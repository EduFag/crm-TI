"""Espelha EquipmentLog em RegistroAcao e registra edições cadastrais."""

from core.audit import registrar_acao, registrar_alteracoes
from core.models import RegistroAcao
from core.permissions import MODULO_EQUIPMENT
from equipment.models import EquipmentLog

_ACAO_POR_LOG = {
    EquipmentLog.ActionChoices.CREATED: RegistroAcao.AcaoChoices.CREATED,
    EquipmentLog.ActionChoices.ASSIGNED: RegistroAcao.AcaoChoices.ASSIGNED,
    EquipmentLog.ActionChoices.RETURNED: RegistroAcao.AcaoChoices.RETURNED,
    EquipmentLog.ActionChoices.MAINTENANCE: RegistroAcao.AcaoChoices.STATUS_CHANGED,
    EquipmentLog.ActionChoices.SCRAPPED: RegistroAcao.AcaoChoices.STATUS_CHANGED,
}


def log_do_equipment_log(equipment, log_action, employee_name, actor):
    """Espelha uma entrada de EquipmentLog no RegistroAcao."""
    acao = _ACAO_POR_LOG.get(log_action, RegistroAcao.AcaoChoices.UPDATED)
    labels = dict(EquipmentLog.ActionChoices.choices)
    return registrar_acao(
        modulo=MODULO_EQUIPMENT,
        acao=acao,
        descricao=f'Equipamento {equipment.tag}: {labels.get(log_action, log_action)} ({employee_name or "Sistema"}).',
        actor=actor,
        obj=equipment,
        metadata={'equipment_log_action': log_action, 'employee_name': employee_name},
    )


def log_cadastro(equipment, log_action, employee_name, actor):
    log_do_equipment_log(equipment, log_action, employee_name, actor)


def log_edicao_cadastral(equipment, actor, antes):
    return registrar_alteracoes(
        modulo=MODULO_EQUIPMENT,
        actor=actor,
        obj_antes=antes,
        obj_depois=equipment,
        campos=[
            'type', 'tag', 'serial_number', 'brand_model',
            'purchase_date', 'warranty_end', 'purchase_value',
        ],
        descricao_prefixo=f'Dados cadastrais do equipamento {equipment.tag} atualizados.',
    )
