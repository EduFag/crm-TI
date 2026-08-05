# Tags, Central Informativa estruturada e presença online

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('helpdesk', '0026_informativemessage'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Nome curto da tag (sem espaços longos).', max_length=30, unique=True)),
                ('slug', models.SlugField(help_text='Identificador normalizado.', max_length=40, unique=True)),
                ('criada_por_ia', models.BooleanField(default=False, help_text='True se criada pelo Assistente.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'tag de chamado',
                'verbose_name_plural': 'tags de chamado',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='UserPresence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_seen', models.DateTimeField(db_index=True, help_text='Último heartbeat recebido.')),
                (
                    'user',
                    models.OneToOneField(
                        help_text='Usuário monitorado.',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='presence',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'presença de usuário',
                'verbose_name_plural': 'presenças de usuários',
            },
        ),
        migrations.AddField(
            model_name='ticket',
            name='assistente_ajuda_ti_em',
            field=models.DateTimeField(
                blank=True,
                help_text='Última solicitação de ajuda do Assistente aos técnicos online (anti-spam).',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='tag',
            field=models.ForeignKey(
                blank=True,
                help_text='Tag curta de funil/follow-up (uma por chamado).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tickets',
                to='helpdesk.tickettag',
            ),
        ),
        migrations.AddField(
            model_name='informativemessage',
            name='ativo',
            field=models.BooleanField(default=True, help_text='Se falso, o Assistente ignora o comunicado.'),
        ),
        migrations.AddField(
            model_name='informativemessage',
            name='palavras_chave',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Palavras-chave separadas por vírgula para o Assistente consultar.',
                max_length=400,
            ),
        ),
        migrations.AddField(
            model_name='informativemessage',
            name='valido_ate',
            field=models.DateField(
                blank=True,
                help_text='Opcional: data de validade do comunicado (inclusive).',
                null=True,
            ),
        ),
    ]
