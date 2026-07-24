# Generated manually — mensagens internas TI/Assistente

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0023_assistente_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='is_interno',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Mensagem interna: visível só para TI/staff/superuser e para o Assistente. '
                    'Solicitante/criador comum não vê.'
                ),
            ),
        ),
    ]
