# Modelo AssistenteInteracao para eval do Assistente

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('integracoes', '0006_assistentechunk_embedding'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssistenteInteracao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_id', models.PositiveIntegerField(db_index=True)),
                ('chunk_ids', models.JSONField(blank=True, default=list)),
                ('hybrid', models.BooleanField(
                    default=False,
                    help_text='True se a query usou embedding semântico nesta rodada.',
                )),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('nota', models.SmallIntegerField(
                    blank=True,
                    choices=[(1, 'Útil'), (-1, 'Ruim')],
                    help_text='null = sem avaliação; 1 = útil; -1 = ruim.',
                    null=True,
                )),
                ('nota_em', models.DateTimeField(blank=True, null=True)),
                ('comentario', models.CharField(blank=True, default='', max_length=400)),
                ('nota_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='avaliacoes_assistente',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'interação do assistente',
                'verbose_name_plural': 'interações do assistente',
                'ordering': ['-criado_em'],
            },
        ),
    ]
