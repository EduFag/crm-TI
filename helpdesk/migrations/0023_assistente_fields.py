# Generated manually for assistente fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0022_ticketmention'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='is_assistente',
            field=models.BooleanField(default=False, help_text='Comentário gerado pelo Assistente de IA.'),
        ),
        migrations.AddField(
            model_name='ticket',
            name='assistente_escalado',
            field=models.BooleanField(default=False, help_text='Assistente IA encerrou o atendimento e pediu intervenção da TI.'),
        ),
    ]
