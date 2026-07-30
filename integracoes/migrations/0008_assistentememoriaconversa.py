# Conversas persistentes do chat de memória

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('integracoes', '0007_assistenteinteracao'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssistenteMemoriaConversa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(blank=True, default='Nova conversa', max_length=160)),
                ('mensagens', models.JSONField(
                    blank=True,
                    default=list,
                    help_text='Lista de {role, content} (user/assistant).',
                )),
                ('ativo', models.BooleanField(
                    default=True,
                    help_text='False = arquivada (some do histórico ativo).',
                )),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='conversas_memoria_assistente',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'conversa de memória',
                'verbose_name_plural': 'conversas de memória',
                'ordering': ['-atualizado_em'],
            },
        ),
    ]
