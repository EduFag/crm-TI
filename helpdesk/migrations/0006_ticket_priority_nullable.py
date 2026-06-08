import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0005_ticketcategory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='priority',
            field=models.CharField(
                blank=True,
                choices=[('LOW', 'Baixa'), ('MEDIUM', 'Média'), ('HIGH', 'Alta'), ('URGENT', 'Urgente')],
                help_text='Definida pela TI; null até triagem.',
                max_length=20,
                null=True,
            ),
        ),
    ]
