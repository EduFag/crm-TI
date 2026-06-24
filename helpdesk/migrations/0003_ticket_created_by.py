# Generated manually — vínculo do chamado ao usuário que o abriu

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0002_ticket_is_archived'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário que abriu o chamado no sistema.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_tickets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
