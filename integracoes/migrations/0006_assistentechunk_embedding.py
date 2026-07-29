# Campos de embedding em AssistenteChunk (RAG híbrido sem pgvector)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integracoes', '0005_seed_chunks_regras'),
    ]

    operations = [
        migrations.AddField(
            model_name='assistentechunk',
            name='embedding',
            field=models.JSONField(
                blank=True,
                help_text='Lista de floats do embedding; null se ainda não calculado.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='assistentechunk',
            name='embedding_modelo',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Modelo usado no último embedding (ex.: text-embedding-3-small).',
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name='assistentechunk',
            name='embedding_em',
            field=models.DateTimeField(
                blank=True,
                help_text='Quando o embedding foi gerado.',
                null=True,
            ),
        ),
    ]
