# Model IntegracaoApi (MoneyConsig e outras APIs externas)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('integracoes', '0008_assistentememoriaconversa'),
    ]

    operations = [
        migrations.CreateModel(
            name='IntegracaoApi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nome amigável da integração.', max_length=120)),
                (
                    'provider',
                    models.CharField(
                        choices=[('moneyconsig', 'MoneyConsig')],
                        help_text='Provedor da API externa.',
                        max_length=32,
                    ),
                ),
                (
                    'credentials_encrypted',
                    models.TextField(help_text='Credenciais JSON criptografadas (Fernet).'),
                ),
                (
                    'token_hint',
                    models.CharField(
                        blank=True,
                        default='',
                        help_text='Últimos caracteres do token para exibição mascarada.',
                        max_length=8,
                    ),
                ),
                ('is_active', models.BooleanField(default=True, help_text='Integração ativa.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='integracoes_api_criadas',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'integração API',
                'verbose_name_plural': 'integrações API',
                'ordering': ['-created_at'],
            },
        ),
    ]
