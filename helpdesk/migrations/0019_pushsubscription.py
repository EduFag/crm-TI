import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('helpdesk', '0018_ticket_resolved_by_ticketcontestation'),
    ]

    operations = [
        migrations.CreateModel(
            name='PushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.TextField(help_text='URL do endpoint do browser.', unique=True)),
                ('p256dh', models.CharField(help_text='Chave pública do cliente (p256dh).', max_length=255)),
                ('auth', models.CharField(help_text='Segredo de autenticação do cliente.', max_length=255)),
                ('user_agent', models.CharField(blank=True, help_text='User-Agent no momento da inscrição.', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True, help_text='False quando o endpoint expirou ou foi cancelado.')),
                ('user', models.ForeignKey(help_text='Usuário inscrito para receber push.', on_delete=django.db.models.deletion.CASCADE, related_name='push_subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'inscrição push',
                'verbose_name_plural': 'inscrições push',
                'ordering': ['-created_at'],
            },
        ),
    ]
