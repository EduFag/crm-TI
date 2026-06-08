# Generated manually — vínculo do solicitante a usuário do sistema

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0003_ticket_created_by'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='requester_user',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário do sistema selecionado como solicitante.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='requested_tickets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
