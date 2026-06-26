# Generated manually — resolved_by no Ticket e histórico de contestação

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('helpdesk', '0017_corrigir_resolved_at_arquivar'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='resolved_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário que finalizou ou recusou o chamado.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='resolved_tickets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name='TicketContestation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(help_text='Motivo informado na contestação.')),
                ('finalized_at', models.DateTimeField(blank=True, help_text='Momento em que o chamado havia sido finalizado.', null=True)),
                ('was_rejected', models.BooleanField(default=False, help_text='Indica se a finalização contestada era uma recusa.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contested_by', models.ForeignKey(help_text='Usuário que contestou a finalização.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ticket_contestations', to=settings.AUTH_USER_MODEL)),
                ('finalized_by', models.ForeignKey(blank=True, help_text='Usuário que havia finalizado ou recusado o chamado.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contested_finalizations', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(help_text='Chamado contestado.', on_delete=django.db.models.deletion.CASCADE, related_name='contestations', to='helpdesk.ticket')),
            ],
            options={
                'verbose_name': 'contestação de chamado',
                'verbose_name_plural': 'contestações de chamado',
                'ordering': ['-created_at'],
            },
        ),
    ]
