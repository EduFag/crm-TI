# Generated manually for IntegracaoIA

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IntegracaoIA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nome amigável da integração.', max_length=120)),
                ('provider', models.CharField(choices=[('deepseek', 'DeepSeek'), ('chatgpt', 'ChatGPT'), ('gemini', 'Gemini'), ('grok', 'Grok'), ('claude', 'Claude'), ('nano_banana', 'Nano Banana')], help_text='Provedor de IA.', max_length=32)),
                ('credentials_encrypted', models.TextField(help_text='Credenciais JSON criptografadas (Fernet).')),
                ('token_hint', models.CharField(blank=True, default='', help_text='Últimos caracteres da API key para exibição mascarada.', max_length=8)),
                ('is_active', models.BooleanField(default=True, help_text='Integração ativa.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='integracoes_ia_criadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'integração IA',
                'verbose_name_plural': 'integrações IA',
                'ordering': ['-created_at'],
            },
        ),
    ]
