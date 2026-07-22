"""Regras de negócio do módulo discador (licenças, históricos, sincronização)."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from discador.models import (
    AcessoDiscador,
    Campanha,
    Discador,
    DiscadorContratoHistorico,
    Ramal,
    RamalAtribuicaoHistorico,
)

SLUG_JOYTEC = 'joytec'


def get_or_create_joytec() -> Discador:
    """Garante o registro JoyTec (seed de fallback se migration não rodou)."""
    discador, criado = Discador.objects.get_or_create(
        slug=SLUG_JOYTEC,
        defaults={
            'nome': 'JoyTec',
            'valor_por_licenca': Decimal('0.00'),
            'licencas_contratadas': 37,
            'is_active': True,
        },
    )
    if criado:
        DiscadorContratoHistorico.objects.create(
            discador=discador,
            valor_por_licenca=discador.valor_por_licenca,
            licencas_contratadas=discador.licencas_contratadas,
            observacao='Cadastro inicial do contrato JoyTec.',
            registered_by=None,
        )
    return discador


def contar_licencas_consumidas(discador: Discador) -> int:
    return Ramal.objects.filter(
        discador=discador,
        status__in=[Ramal.StatusChoices.IN_USE, Ramal.StatusChoices.FREE],
    ).count()


def kpis_licencas(discador: Discador) -> dict:
    ramais = Ramal.objects.filter(discador=discador)
    em_uso = ramais.filter(status=Ramal.StatusChoices.IN_USE).count()
    livres = ramais.filter(status=Ramal.StatusChoices.FREE).count()
    nao_config = ramais.filter(status=Ramal.StatusChoices.NOT_CONFIGURED).count()
    consumidas = em_uso + livres
    contratadas = discador.licencas_contratadas
    return {
        'contratadas': contratadas,
        'consumidas': consumidas,
        'em_uso': em_uso,
        'livres': livres,
        'nao_configurados': nao_config,
        'disponiveis': max(contratadas - consumidas, 0),
        'custo_mensal': discador.valor_por_licenca * contratadas,
        'estourado': consumidas > contratadas,
        'no_limite': consumidas >= contratadas,
    }


def status_consome_licenca(status: str) -> bool:
    return status in (Ramal.StatusChoices.IN_USE, Ramal.StatusChoices.FREE)


def validar_teto_licencas(discador: Discador, status_novo: str, ramal: Ramal | None = None):
    """Bloqueia se o novo status passa a consumir uma licença além do contratado."""
    if not status_consome_licenca(status_novo):
        return
    ja_consumia = bool(ramal and status_consome_licenca(ramal.status))
    if ja_consumia:
        return
    if contar_licencas_consumidas(discador) >= discador.licencas_contratadas:
        raise ValidationError(
            f'Limite de {discador.licencas_contratadas} licenças atingido. '
            'Libere um ramal (Não configurado) ou aumente o contrato.'
        )


def derivar_status_acesso(titular_nome: str, login_discador: str) -> str:
    tem_titular = bool((titular_nome or '').strip())
    tem_login = bool((login_discador or '').strip())
    if tem_titular and tem_login:
        return Ramal.StatusChoices.IN_USE
    if tem_login:
        return Ramal.StatusChoices.FREE
    return Ramal.StatusChoices.NOT_CONFIGURED


def _registrar_atribuicao(
    *,
    ramal: Ramal,
    action: str,
    actor,
    titular_nome: str = '',
    login_discador: str = '',
    campanha_nome: str = '',
    tipo: str = '',
    status: str = '',
    observacao: str = '',
):
    return RamalAtribuicaoHistorico.objects.create(
        ramal=ramal,
        discador=ramal.discador if ramal else None,
        ramal_numero=ramal.numero if ramal else '',
        action=action,
        titular_nome=titular_nome or '',
        login_discador=login_discador or '',
        campanha_nome=campanha_nome or '',
        tipo=tipo or '',
        status=status or (ramal.status if ramal else ''),
        observacao=observacao or '',
        registered_by=actor if getattr(actor, 'is_authenticated', False) else None,
    )


def _ramal_tem_acesso(ramal: Ramal) -> bool:
    return AcessoDiscador.objects.filter(ramal_id=ramal.pk).exists()


@transaction.atomic
def criar_ramal(*, discador: Discador, numero: str, status: str, actor) -> Ramal:
    validar_teto_licencas(discador, status)
    ramal = Ramal.objects.create(discador=discador, numero=numero.strip(), status=status)
    _registrar_atribuicao(
        ramal=ramal,
        action=RamalAtribuicaoHistorico.ActionChoices.CREATED,
        actor=actor,
        status=status,
        observacao='Cadastro do ramal.',
    )
    return ramal


@transaction.atomic
def atualizar_ramal(*, ramal: Ramal, numero: str, status: str, actor) -> Ramal:
    status_antigo = ramal.status
    validar_teto_licencas(ramal.discador, status, ramal=ramal)
    # Não permitir marcar Livre/Não configurado se houver acesso com titular em uso
    if _ramal_tem_acesso(ramal):
        acesso = ramal.acesso
        if status == Ramal.StatusChoices.NOT_CONFIGURED and acesso.login_discador:
            raise ValidationError(
                'Remova o acesso vinculado antes de marcar o ramal como Não configurado.'
            )
        if status != Ramal.StatusChoices.IN_USE and acesso.titular_nome:
            # Mantém coerência: acesso com titular implica Em uso
            if status == Ramal.StatusChoices.FREE:
                raise ValidationError(
                    'Este ramal possui titular no acesso. Edite ou exclua o acesso primeiro.'
                )
    ramal.numero = numero.strip()
    ramal.status = status
    ramal.save()
    if status_antigo != status:
        _registrar_atribuicao(
            ramal=ramal,
            action=RamalAtribuicaoHistorico.ActionChoices.STATUS_CHANGED,
            actor=actor,
            status=status,
            observacao=f'Status: {status_antigo} → {status}',
        )
        if _ramal_tem_acesso(ramal):
            acesso = ramal.acesso
            acesso.status = status
            acesso.save(update_fields=['status', 'updated_at'])
    return ramal


@transaction.atomic
def excluir_ramal(*, ramal: Ramal, actor) -> None:
    if _ramal_tem_acesso(ramal):
        raise ValidationError('Exclua o acesso vinculado a este ramal antes de removê-lo.')
    _registrar_atribuicao(
        ramal=ramal,
        action=RamalAtribuicaoHistorico.ActionChoices.DELETED,
        actor=actor,
        status=ramal.status,
        observacao='Ramal excluído.',
    )
    ramal.delete()


@transaction.atomic
def criar_campanha(*, discador: Discador, nome: str, is_active: bool = True) -> Campanha:
    return Campanha.objects.create(
        discador=discador,
        nome=nome.strip(),
        is_active=is_active,
    )


@transaction.atomic
def atualizar_campanha(*, campanha: Campanha, nome: str, is_active: bool) -> Campanha:
    campanha.nome = nome.strip()
    campanha.is_active = is_active
    campanha.save()
    return campanha


@transaction.atomic
def excluir_campanha(*, campanha: Campanha) -> None:
    if campanha.acessos.exists():
        raise ValidationError(
            'Não é possível excluir: há acessos vinculados. Desative a campanha em vez disso.'
        )
    campanha.delete()


@transaction.atomic
def criar_acesso(
    *,
    discador: Discador,
    titular_nome: str,
    titular_user,
    login_discador: str,
    ramal: Ramal,
    campanha: Campanha,
    tipo: str,
    actor,
) -> AcessoDiscador:
    if ramal.discador_id != discador.id:
        raise ValidationError('O ramal não pertence a este discador.')
    if campanha.discador_id != discador.id:
        raise ValidationError('A campanha não pertence a este discador.')
    if _ramal_tem_acesso(ramal):
        raise ValidationError('Este ramal já possui um acesso ativo.')

    status = derivar_status_acesso(titular_nome, login_discador)
    validar_teto_licencas(discador, status, ramal=ramal)

    acesso = AcessoDiscador.objects.create(
        discador=discador,
        titular_nome=titular_nome or '',
        titular_user=titular_user,
        login_discador=login_discador.strip(),
        ramal=ramal,
        campanha=campanha,
        tipo=tipo,
        status=status,
    )
    ramal.status = status
    ramal.save(update_fields=['status', 'updated_at'])

    _registrar_atribuicao(
        ramal=ramal,
        action=RamalAtribuicaoHistorico.ActionChoices.ASSIGNED,
        actor=actor,
        titular_nome=acesso.titular_nome,
        login_discador=acesso.login_discador,
        campanha_nome=campanha.nome,
        tipo=tipo,
        status=status,
    )
    return acesso


@transaction.atomic
def atualizar_acesso(
    *,
    acesso: AcessoDiscador,
    titular_nome: str,
    titular_user,
    login_discador: str,
    ramal: Ramal,
    campanha: Campanha,
    tipo: str,
    actor,
) -> AcessoDiscador:
    discador = acesso.discador
    if ramal.discador_id != discador.id:
        raise ValidationError('O ramal não pertence a este discador.')
    if campanha.discador_id != discador.id:
        raise ValidationError('A campanha não pertence a este discador.')

    # Troca de ramal: destino não pode ter outro acesso
    if ramal.pk != acesso.ramal_id and _ramal_tem_acesso(ramal):
        raise ValidationError('O ramal de destino já possui um acesso ativo.')

    titular_antes = acesso.titular_nome
    login_antes = acesso.login_discador
    ramal_antes = acesso.ramal

    status = derivar_status_acesso(titular_nome, login_discador)
    validar_teto_licencas(discador, status, ramal=ramal)

    acesso.titular_nome = titular_nome or ''
    acesso.titular_user = titular_user
    acesso.login_discador = login_discador.strip()
    acesso.ramal = ramal
    acesso.campanha = campanha
    acesso.tipo = tipo
    acesso.status = status
    acesso.save()

    # Libera ramal anterior se trocou
    if ramal_antes.pk != ramal.pk:
        ramal_antes.status = Ramal.StatusChoices.FREE
        ramal_antes.save(update_fields=['status', 'updated_at'])
        _registrar_atribuicao(
            ramal=ramal_antes,
            action=RamalAtribuicaoHistorico.ActionChoices.FREED,
            actor=actor,
            status=Ramal.StatusChoices.FREE,
            observacao=f'Titular movido para ramal {ramal.numero}.',
        )

    ramal.status = status
    ramal.save(update_fields=['status', 'updated_at'])

    if titular_antes != acesso.titular_nome or login_antes != acesso.login_discador:
        action = RamalAtribuicaoHistorico.ActionChoices.TRANSFERRED
    else:
        action = RamalAtribuicaoHistorico.ActionChoices.ASSIGNED

    _registrar_atribuicao(
        ramal=ramal,
        action=action,
        actor=actor,
        titular_nome=acesso.titular_nome,
        login_discador=acesso.login_discador,
        campanha_nome=campanha.nome,
        tipo=tipo,
        status=status,
    )
    return acesso


@transaction.atomic
def excluir_acesso(*, acesso: AcessoDiscador, actor) -> None:
    ramal = acesso.ramal
    _registrar_atribuicao(
        ramal=ramal,
        action=RamalAtribuicaoHistorico.ActionChoices.DELETED,
        actor=actor,
        titular_nome=acesso.titular_nome,
        login_discador=acesso.login_discador,
        campanha_nome=acesso.campanha.nome,
        tipo=acesso.tipo,
        status=Ramal.StatusChoices.FREE,
        observacao='Acesso excluído; ramal liberado.',
    )
    acesso.delete()
    # Mantém licença ativa (Livre) após exclusão do acesso
    ramal.status = Ramal.StatusChoices.FREE
    ramal.save(update_fields=['status', 'updated_at'])


@transaction.atomic
def atualizar_contrato(
    *,
    discador: Discador,
    valor_por_licenca,
    licencas_contratadas: int,
    observacao: str,
    actor,
) -> Discador:
    consumidas = contar_licencas_consumidas(discador)
    if licencas_contratadas < consumidas:
        raise ValidationError(
            f'Não é possível reduzir para {licencas_contratadas}: '
            f'há {consumidas} ramais consumindo licença (Em uso ou Livre).'
        )

    mudou = (
        discador.valor_por_licenca != valor_por_licenca
        or discador.licencas_contratadas != licencas_contratadas
    )
    discador.valor_por_licenca = valor_por_licenca
    discador.licencas_contratadas = licencas_contratadas
    discador.save()

    if mudou:
        DiscadorContratoHistorico.objects.create(
            discador=discador,
            valor_por_licenca=discador.valor_por_licenca,
            licencas_contratadas=discador.licencas_contratadas,
            observacao=(observacao or '').strip(),
            registered_by=actor if getattr(actor, 'is_authenticated', False) else None,
        )
    return discador
