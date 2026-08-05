# Sessão de autorização de chips concedida pela TI ao Assistente

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('helpdesk', '0027_assistente_contextual'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='assistente_chip_auth_em',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text=(
                    'Início/renovação da autorização de chips dada por TI via @assistente interno. '
                    'Vale por ASSISTENTE_CHIP_AUTH_MINUTOS e é renovada a cada nota interna da TI.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='assistente_chip_auth_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='chip_auth_tickets',
                to=settings.AUTH_USER_MODEL,
                help_text='Membro da TI que autorizou operações de chip neste chamado.',
            ),
        ),
    ]
