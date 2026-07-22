# Migration de reparo: o 0001 antigo (3C Plus) ficou marcado como aplicado
# após a remoção do app, então o JoyTec nunca criou as tabelas novas.

from decimal import Decimal

from django.db import connection, migrations


TABELAS_JOYTEC = (
    'discador_discador',
    'discador_campanha',
    'discador_ramal',
    'discador_acessodiscador',
    'discador_discadorcontratohistorico',
    'discador_ramalatribuicaohistorico',
)


def ensure_joytec_schema(apps, schema_editor):
    """Cria tabelas do JoyTec se ainda não existirem (caso 0001 fantasma)."""
    # Models concretos: create_model precisa da definição completa (FKs etc.)
    from discador.models import (
        AcessoDiscador,
        Campanha,
        Discador,
        DiscadorContratoHistorico,
        Ramal,
        RamalAtribuicaoHistorico,
    )

    existentes = set(connection.introspection.table_names())

    for model in (
        Discador,
        Campanha,
        Ramal,
        AcessoDiscador,
        DiscadorContratoHistorico,
        RamalAtribuicaoHistorico,
    ):
        if model._meta.db_table not in existentes:
            schema_editor.create_model(model)
            existentes.add(model._meta.db_table)

    _seed_joytec(apps)


def _seed_joytec(apps):
    Discador = apps.get_model('discador', 'Discador')
    DiscadorContratoHistorico = apps.get_model('discador', 'DiscadorContratoHistorico')
    discador, criado = Discador.objects.get_or_create(
        slug='joytec',
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


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    """
    SeparateDatabaseAndState: o estado Django já tem os models via 0001 novo;
    no banco, as tabelas podem não existir por causa do 0001 antigo fantasma.
    """

    dependencies = [
        ('discador', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(ensure_joytec_schema, noop_reverse),
            ],
        ),
    ]
