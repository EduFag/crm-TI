# Generated manually for TicketMention

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('helpdesk', '0021_alter_comment_attachment'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketMention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('seen_at', models.DateTimeField(blank=True, help_text='Momento em que o mencionado abriu o chamado (null = não visto).', null=True)),
                ('comment', models.ForeignKey(help_text='Comentário que contém a menção.', on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to='helpdesk.comment')),
                ('mentioned_by', models.ForeignKey(blank=True, help_text='Operador que fez a menção.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mentions_made', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(help_text='Chamado em que a menção ocorreu.', on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to='helpdesk.ticket')),
                ('user', models.ForeignKey(help_text='Usuário mencionado.', on_delete=django.db.models.deletion.CASCADE, related_name='ticket_mentions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'menção em chamado',
                'verbose_name_plural': 'menções em chamados',
                'ordering': ['-created_at'],
                'unique_together': {('ticket', 'user', 'comment')},
            },
        ),
    ]
