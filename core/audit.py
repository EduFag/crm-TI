"""Serviço central de auditoria (append-only)."""

from django.contrib.contenttypes.models import ContentType

from core.models import RegistroAcao
from core.permissions import (
    MODULO_CHIPS,
    MODULO_EMAILS,
    MODULO_EQUIPMENT,
    MODULO_HELPDESK,
    MODULO_GESTAO_USUARIOS,
)

# Módulo lógico "core" para gestão de usuários/equipes
MODULO_CORE = 'core'

MODULOS_AUDITORIA = frozenset({
    MODULO_HELPDESK,
    MODULO_CHIPS,
    MODULO_EMAILS,
    MODULO_EQUIPMENT,
    MODULO_CORE,
})

# Campos que nunca entram em metadata de alterações
CAMPOS_SENSIVEIS = frozenset({
    'password',
    'last_login',
    'date_joined',
    'created_at',
    'updated_at',
    'last_password_reset',
})


def _serializar_valor(valor):
    if valor is None:
        return None
    if hasattr(valor, 'pk'):
        return str(valor)
    if hasattr(valor, 'isoformat'):
        return valor.isoformat()
    return str(valor)


def registrar_acao(*, modulo, acao, descricao, actor=None, obj=None, metadata=None):
    """Persiste um registro de auditoria. Nunca atualiza registros existentes."""
    if modulo not in MODULOS_AUDITORIA:
        raise ValueError(f'Módulo de auditoria inválido: {modulo}')

    content_type = None
    object_id = None
    object_repr = ''

    if obj is not None:
        content_type = ContentType.objects.get_for_model(obj)
        object_id = obj.pk
        object_repr = str(obj)[:255]

    return RegistroAcao.objects.create(
        modulo=modulo,
        acao=acao,
        descricao=descricao,
        actor=actor,
        content_type=content_type,
        object_id=object_id,
        object_repr=object_repr,
        metadata=metadata or {},
    )


def registrar_alteracoes(
    *,
    modulo,
    actor,
    obj_antes,
    obj_depois,
    campos,
    acao=RegistroAcao.AcaoChoices.UPDATED,
    descricao_prefixo='',
):
    """
    Compara campos entre duas instâncias e grava um único RegistroAcao com metadata.
    Retorna None se nenhum campo relevante mudou.
    """
    metadata = {}
    for campo in campos:
        if campo in CAMPOS_SENSIVEIS:
            continue
        antes = getattr(obj_antes, campo, None)
        depois = getattr(obj_depois, campo, None)
        if antes != depois:
            metadata[campo] = {
                'antes': _serializar_valor(antes),
                'depois': _serializar_valor(depois),
            }

    if not metadata:
        return None

    nomes = ', '.join(sorted(metadata.keys()))
    descricao = descricao_prefixo or f'Campos alterados: {nomes}.'
    return registrar_acao(
        modulo=modulo,
        acao=acao,
        descricao=descricao,
        actor=actor,
        obj=obj_depois,
        metadata=metadata,
    )


def logs_do_modulo(modulo, limite=50):
    """Retorna os últimos registros de um módulo para painéis locais."""
    return (
        RegistroAcao.objects.filter(modulo=modulo)
        .select_related('actor')
        .order_by('-timestamp')[:limite]
    )
