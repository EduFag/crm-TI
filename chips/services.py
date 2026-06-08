"""Operações de domínio do módulo chips."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import CustomUser
from chips.audit import (
    log_devolucao,
    log_entrega,
    log_transferencia,
)
from chips.models import Batch, Chip, ChipMovement
from chips.queries import chip_para_grid_dict, chips_com_anotacoes_operacionais


def _titular_atual(chip):
    """Retorna o último movimento de entrega/transferência."""
    return chip.movements.filter(
        action__in=[
            ChipMovement.ActionChoices.DELIVERY,
            ChipMovement.ActionChoices.TRANSFER,
        ],
    ).order_by('-timestamp').first()


@transaction.atomic
def entregar_chip(
    chip,
    *,
    employee_name,
    employee_user=None,
    actor,
    activated_at=None,
):
    """Entrega chip disponível na TI para uma pessoa."""
    if chip.custody != Chip.CustodyChoices.WITH_TI:
        raise ValidationError('Somente chips na TI podem ser entregues.')

    hoje = activated_at or timezone.localdate()
    if not chip.activated_at:
        chip.activated_at = hoje

    chip.custody = Chip.CustodyChoices.WITH_PERSON
    chip.status = Chip.StatusChoices.IN_USE
    chip.batch = None
    chip.save()

    ChipMovement.objects.create(
        chip=chip,
        employee_name=employee_name,
        employee_user=employee_user,
        action=ChipMovement.ActionChoices.DELIVERY,
        registered_by=actor,
    )
    log_entrega(chip, employee_name, actor)
    return _chip_grid(chip.pk)


@transaction.atomic
def transferir_chip(chip, *, novo_nome, novo_user=None, actor):
    """Transfere posse sem alterar activated_at nem ciclo de recarga."""
    if chip.custody != Chip.CustodyChoices.WITH_PERSON:
        raise ValidationError('Somente chips em uso podem ser transferidos.')

    anterior = _titular_atual(chip)
    nome_anterior = anterior.employee_name if anterior else 'Desconhecido'

    ChipMovement.objects.create(
        chip=chip,
        employee_name=novo_nome,
        employee_user=novo_user,
        action=ChipMovement.ActionChoices.TRANSFER,
        registered_by=actor,
    )
    log_transferencia(chip, nome_anterior, novo_nome, actor)
    return _chip_grid(chip.pk)


@transaction.atomic
def devolver_para_ti(chip, *, envelope, actor):
    """Devolve chip da rua para envelope na TI."""
    if chip.custody != Chip.CustodyChoices.WITH_PERSON:
        raise ValidationError('Somente chips em uso podem ser devolvidos.')

    if envelope.tipo != Batch.TipoChoices.ENVELOPE:
        raise ValidationError('Selecione um envelope válido.')

    anterior = _titular_atual(chip)
    nome_anterior = anterior.employee_name if anterior else 'Desconhecido'

    ChipMovement.objects.create(
        chip=chip,
        employee_name=nome_anterior,
        employee_user=anterior.employee_user if anterior else None,
        action=ChipMovement.ActionChoices.RETURN,
        registered_by=actor,
    )
    log_devolucao(chip, nome_anterior, actor)

    chip.custody = Chip.CustodyChoices.WITH_TI
    chip.status = Chip.StatusChoices.AVAILABLE
    chip.batch = envelope
    chip.save()
    return _chip_grid(chip.pk)


@transaction.atomic
def registrar_bloqueio(chip, actor):
    """Marca chip como bloqueado e registra data."""
    chip.status = Chip.StatusChoices.BLOCKED
    chip.last_blocked_at = timezone.now()
    chip.save()
    return chip


@transaction.atomic
def criar_chip_operacional(
    *,
    line_number,
    operator,
    custody,
    employee_name='',
    employee_user=None,
    activated_at=None,
    batch=None,
    actor,
):
    """Cria chip e posiciona na TI ou entrega direto ao callcenter."""
    chip = Chip.objects.create(
        line_number=line_number.strip(),
        operator=operator,
        custody=custody,
        batch=batch if custody == Chip.CustodyChoices.WITH_TI else None,
        status=(
            Chip.StatusChoices.AVAILABLE
            if custody == Chip.CustodyChoices.WITH_TI
            else Chip.StatusChoices.IN_USE
        ),
        activated_at=(
            activated_at or timezone.localdate()
            if custody == Chip.CustodyChoices.WITH_PERSON
            else None
        ),
    )

    if custody == Chip.CustodyChoices.WITH_PERSON:
        ChipMovement.objects.create(
            chip=chip,
            employee_name=employee_name,
            employee_user=employee_user,
            action=ChipMovement.ActionChoices.DELIVERY,
            registered_by=actor,
        )
        log_entrega(chip, employee_name, actor)

    from chips.audit import log_chip_criado
    log_chip_criado(chip, actor)
    return _chip_grid(chip.pk)


@transaction.atomic
def atualizar_chip_grid(chip, *, dados, actor):
    """Atualiza campos editáveis inline do grid."""
    from chips.audit import log_chip_atualizado

    antes = Chip.objects.get(pk=chip.pk)

    if dados.get('line_number'):
        chip.line_number = dados['line_number'].strip()

    if dados.get('operator_id'):
        chip.operator_id = int(dados['operator_id'])

    if dados.get('activated_at'):
        chip.activated_at = date.fromisoformat(dados['activated_at'])

    custody_nova = dados.get('custody')
    if custody_nova and custody_nova != chip.custody:
        if custody_nova == Chip.CustodyChoices.WITH_TI:
            batch_id = dados.get('batch_id')
            if not batch_id:
                raise ValidationError('Selecione o envelope para chips na TI.')
            envelope = Batch.objects.get(pk=int(batch_id))
            if chip.custody == Chip.CustodyChoices.WITH_PERSON:
                devolver_para_ti(chip, envelope=envelope, actor=actor)
                chip.refresh_from_db()
            else:
                chip.custody = Chip.CustodyChoices.WITH_TI
                chip.status = Chip.StatusChoices.AVAILABLE
                chip.batch = envelope
                chip.save()
        elif custody_nova == Chip.CustodyChoices.WITH_PERSON:
            nome = (dados.get('employee_name') or '').strip()
            if not nome:
                raise ValidationError('Informe o titular para entregar o chip.')
            user = None
            if dados.get('employee_user_id'):
                user = CustomUser.objects.filter(pk=int(dados['employee_user_id'])).first()
            if chip.custody == Chip.CustodyChoices.WITH_TI:
                entregar_chip(
                    chip,
                    employee_name=nome,
                    employee_user=user,
                    actor=actor,
                    activated_at=chip.activated_at,
                )
                chip.refresh_from_db()
            else:
                transferir_chip(chip, novo_nome=nome, novo_user=user, actor=actor)
                chip.refresh_from_db()
    else:
        if dados.get('batch_id') and chip.custody == Chip.CustodyChoices.WITH_TI:
            chip.batch_id = int(dados['batch_id'])
        if dados.get('employee_name') and chip.custody == Chip.CustodyChoices.WITH_PERSON:
            nome = dados['employee_name'].strip()
            if nome:
                atual = _titular_atual(chip)
                if not atual or atual.employee_name != nome:
                    transferir_chip(chip, novo_nome=nome, novo_user=None, actor=actor)
                    chip.refresh_from_db()
        chip.save()

    chip.refresh_from_db()
    log_chip_atualizado(chip, actor, antes)
    return _chip_grid(chip.pk)


def _chip_grid(pk):
    chip = chips_com_anotacoes_operacionais(Chip.objects.filter(pk=pk)).first()
    return chip_para_grid_dict(chip) if chip else {}
