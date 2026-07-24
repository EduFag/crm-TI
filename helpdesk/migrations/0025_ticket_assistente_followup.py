# Generated manually — follow-up automático do Assistente (5min @ / 20min recusa)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0024_comment_is_interno'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='assistente_aguardando_desde',
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    'Início da espera por resposta do solicitante/criador após '
                    'mensagem pública do Assistente.'
                ),
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='assistente_followup_mencao_em',
            field=models.DateTimeField(
                blank=True,
                help_text='Quando o Assistente cobrou resposta com @menção (follow-up de 5 min).',
                null=True,
            ),
        ),
    ]
