"""Auditoria do módulo discador (RegistroAcao)."""

from core.audit import registrar_acao, registrar_alteracoes
from core.models import RegistroAcao
from core.permissions import MODULO_DISCADOR


def log_acesso_criado(acesso, actor):
    return registrar_acao(
        modulo=MODULO_DISCADOR,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=(
            f'Acesso criado: {acesso.nome_exibicao} / {acesso.login_discador} '
            f'(ramal {acesso.ramal.numero}).'
        ),
        actor=actor,
        obj=acesso,
        metadata={
            'ramal': acesso.ramal.numero,
            'login': acesso.login_discador,
            'tipo': acesso.tipo,
        },
    )


def log_acesso_atualizado(acesso, actor, antes):
    return registrar_alteracoes(
        modulo=MODULO_DISCADOR,
        actor=actor,
        obj_antes=antes,
        obj_depois=acesso,
        campos=[
            'titular_nome', 'titular_user_id', 'login_discador',
            'ramal_id', 'campanha_id', 'tipo', 'status',
        ],
        descricao_prefixo=f'Acesso {acesso.login_discador} atualizado.',
    )


def log_acesso_excluido(acesso, actor):
    return registrar_acao(
        modulo=MODULO_DISCADOR,
        acao=RegistroAcao.AcaoChoices.DELETED,
        descricao=(
            f'Acesso excluído: {acesso.nome_exibicao} / {acesso.login_discador} '
            f'(ramal {acesso.ramal.numero}).'
        ),
        actor=actor,
        obj=acesso,
        metadata={
            'ramal': acesso.ramal.numero,
            'login': acesso.login_discador,
        },
    )


def log_ramal_criado(ramal, actor):
    return registrar_acao(
        modulo=MODULO_DISCADOR,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Ramal {ramal.numero} cadastrado ({ramal.get_status_display()}).',
        actor=actor,
        obj=ramal,
    )


def log_ramal_atualizado(ramal, actor, antes):
    return registrar_alteracoes(
        modulo=MODULO_DISCADOR,
        actor=actor,
        obj_antes=antes,
        obj_depois=ramal,
        campos=['numero', 'status'],
        descricao_prefixo=f'Ramal {ramal.numero} atualizado.',
    )


def log_ramal_excluido(ramal, actor):
    return registrar_acao(
        modulo=MODULO_DISCADOR,
        acao=RegistroAcao.AcaoChoices.DELETED,
        descricao=f'Ramal {ramal.numero} excluído.',
        actor=actor,
        obj=ramal,
    )


def log_campanha_criada(campanha, actor):
    return registrar_acao(
        modulo=MODULO_DISCADOR,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Campanha "{campanha.nome}" cadastrada.',
        actor=actor,
        obj=campanha,
    )


def log_campanha_atualizada(campanha, actor, antes):
    return registrar_alteracoes(
        modulo=MODULO_DISCADOR,
        actor=actor,
        obj_antes=antes,
        obj_depois=campanha,
        campos=['nome', 'is_active'],
        descricao_prefixo=f'Campanha "{campanha.nome}" atualizada.',
    )


def log_campanha_excluida(campanha, actor):
    return registrar_acao(
        modulo=MODULO_DISCADOR,
        acao=RegistroAcao.AcaoChoices.DELETED,
        descricao=f'Campanha "{campanha.nome}" excluída.',
        actor=actor,
        obj=campanha,
    )


def log_contrato_atualizado(discador, actor):
    return registrar_acao(
        modulo=MODULO_DISCADOR,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=(
            f'Contrato {discador.nome}: {discador.licencas_contratadas} licenças '
            f'a R$ {discador.valor_por_licenca}.'
        ),
        actor=actor,
        obj=discador,
        metadata={
            'licencas_contratadas': discador.licencas_contratadas,
            'valor_por_licenca': str(discador.valor_por_licenca),
        },
    )
