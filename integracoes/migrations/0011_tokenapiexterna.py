# Token de API externa por usuário (integração CRM-TI)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('integracoes', '0010_assistenteinteracao_informative_ids'),
    ]

    operations = [
        migrations.CreateModel(
            name='TokenApiExterna',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Rótulo amigável (ex.: sistema do cliente).', max_length=120)),
                ('prefixo', models.CharField(help_text='Primeiros caracteres do token para identificação na UI.', max_length=12)),
                ('token_hash', models.CharField(db_index=True, help_text='SHA-256 do token em texto claro.', max_length=64, unique=True)),
                ('ativo', models.BooleanField(default=True, help_text='False = revogado.')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('ultimo_uso', models.DateTimeField(blank=True, help_text='Última autenticação ou chamada autenticada.', null=True)),
                ('user', models.ForeignKey(
                    help_text='Usuário dono do token.',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tokens_api_externa',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'token API externa',
                'verbose_name_plural': 'tokens API externa',
                'ordering': ['-criado_em'],
            },
        ),
    ]
