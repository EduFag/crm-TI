"""Wrappers de auditoria do módulo emails."""

from core.audit import registrar_acao
from core.models import RegistroAcao
from core.permissions import MODULO_EMAILS


def log_conta_criada(account, actor):
    return registrar_acao(
        modulo=MODULO_EMAILS,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Conta de e-mail {account.address} criada.',
        actor=actor,
        obj=account,
    )


def log_reset_senha(account, actor):
    return registrar_acao(
        modulo=MODULO_EMAILS,
        acao=RegistroAcao.AcaoChoices.PASSWORD_RESET,
        descricao=f'Reset de senha solicitado para {account.address}.',
        actor=actor,
        obj=account,
    )


def log_conta_bloqueada(account, actor):
    return registrar_acao(
        modulo=MODULO_EMAILS,
        acao=RegistroAcao.AcaoChoices.BLOCKED,
        descricao=f'Conta {account.address} bloqueada.',
        actor=actor,
        obj=account,
    )


def log_conta_desbloqueada(account, actor):
    return registrar_acao(
        modulo=MODULO_EMAILS,
        acao=RegistroAcao.AcaoChoices.UNBLOCKED,
        descricao=f'Conta {account.address} desbloqueada.',
        actor=actor,
        obj=account,
    )


def log_dominio_criado(domain, actor):
    return registrar_acao(
        modulo=MODULO_EMAILS,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Domínio @{domain.name} cadastrado.',
        actor=actor,
        obj=domain,
    )
