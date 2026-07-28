# Campos de curadoria/metadados em AssistenteChunk

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('integracoes', '0003_assistenteconfig_integracao_visao'),
    ]

    operations = [
        migrations.AddField(
            model_name='assistentechunk',
            name='origem',
            field=models.CharField(
                choices=[
                    ('ia', 'Gerado pela IA'),
                    ('manual', 'Manual'),
                    ('chat', 'Chat de memória'),
                ],
                default='manual',
                help_text='Como o chunk foi criado (ia/manual/chat).',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='assistentechunk',
            name='ativo',
            field=models.BooleanField(
                default=True,
                help_text='Se falso, o chunk não entra no contexto do Assistente.',
            ),
        ),
        migrations.AddField(
            model_name='assistentechunk',
            name='tags',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='assistentechunk',
            name='atualizado_em',
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='assistentechunk',
            options={
                'ordering': ['-atualizado_em', '-criado_em'],
                'verbose_name': 'chunk de aprendizado',
                'verbose_name_plural': 'chunks de aprendizado',
            },
        ),
    ]
