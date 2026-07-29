# Seed dos chunks de regras do Assistente (tag regra)

from django.db import migrations


def seed_regras(apps, schema_editor):
    AssistenteChunk = apps.get_model('integracoes', 'AssistenteChunk')
    # Import local: lista de seeds versionada no código
    from integracoes.regras_seed import REGRAS_SEED

    titulos = {s['titulo'] for s in REGRAS_SEED}
    existentes = set(
        AssistenteChunk.objects.filter(titulo__in=titulos).values_list('titulo', flat=True)
    )
    for seed in REGRAS_SEED:
        if seed['titulo'] in existentes:
            continue
        AssistenteChunk.objects.create(
            titulo=seed['titulo'][:200],
            conteudo=seed['conteudo'],
            categoria_hint=(seed.get('categoria_hint') or 'regras')[:120],
            fonte_ticket_ids=[],
            origem='manual',
            ativo=True,
            tags=list(seed.get('tags') or ['regra']),
        )


def noop_reverse(apps, schema_editor):
    # Não remove regras: podem ter sido editadas pela TI
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('integracoes', '0004_assistentechunk_origem_ativo_tags'),
    ]

    operations = [
        migrations.RunPython(seed_regras, noop_reverse),
    ]
