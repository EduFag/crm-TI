# Generated manually for AssistenteConfig / AssistenteChunk

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integracoes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssistenteConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ativo', models.BooleanField(default=False, help_text='Quando ativo, o Assistente responde chamados de não-TI.')),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('ultima_geracao_em', models.DateTimeField(blank=True, help_text='Última geração de chunks de aprendizado.', null=True)),
                ('integracao', models.ForeignKey(blank=True, help_text='Integração IA preferencial (senão usa a primeira ativa).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='configs_assistente', to='integracoes.integracaoia')),
            ],
            options={
                'verbose_name': 'configuração do assistente',
                'verbose_name_plural': 'configuração do assistente',
            },
        ),
        migrations.CreateModel(
            name='AssistenteChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('conteudo', models.TextField()),
                ('categoria_hint', models.CharField(blank=True, default='', max_length=120)),
                ('fonte_ticket_ids', models.JSONField(blank=True, default=list)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'chunk de aprendizado',
                'verbose_name_plural': 'chunks de aprendizado',
                'ordering': ['-criado_em'],
            },
        ),
    ]
