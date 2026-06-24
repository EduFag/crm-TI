from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0006_ticket_priority_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='description',
            field=models.TextField(help_text='Descrição detalhada do chamado.'),
        ),
    ]
