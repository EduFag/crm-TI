# Generated manually — co-autores em chamados

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('helpdesk', '0014_ticket_unread_count_tech_ticket_unread_count_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='co_authors',
            field=models.ManyToManyField(
                blank=True,
                help_text='Co-autores com acesso e permissão de comentário no chamado.',
                related_name='coauthored_tickets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
