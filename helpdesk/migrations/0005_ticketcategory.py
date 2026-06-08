# Generated manually — categorias dinâmicas de chamado

import django.db.models.deletion
from django.db import migrations, models


CATEGORIAS_PADRAO = ('Hardware', 'Software', 'Rede', 'Outros')

MAPEAMENTO_LEGADO = {
    'HARDWARE': 'Hardware',
    'SOFTWARE': 'Software',
    'NETWORK': 'Rede',
    'OTHER': 'Outros',
}


def criar_categorias_padrao(apps, schema_editor):
    TicketCategory = apps.get_model('helpdesk', 'TicketCategory')
    for nome in CATEGORIAS_PADRAO:
        TicketCategory.objects.get_or_create(name=nome, defaults={'is_active': True})


def vincular_categorias_aos_chamados(apps, schema_editor):
    Ticket = apps.get_model('helpdesk', 'Ticket')
    TicketCategory = apps.get_model('helpdesk', 'TicketCategory')
    por_nome = {c.name: c for c in TicketCategory.objects.all()}
    padrao = por_nome.get('Outros')
    for ticket in Ticket.objects.all():
        codigo_legado = ticket.category
        nome = MAPEAMENTO_LEGADO.get(codigo_legado, 'Outros')
        ticket.category_fk = por_nome.get(nome, padrao)
        ticket.save(update_fields=['category_fk'])


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0004_ticket_requester_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nome exibido da categoria.', max_length=80, unique=True)),
                ('is_active', models.BooleanField(default=True, help_text='Categorias inativas não aparecem no formulário.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'categoria de chamado',
                'verbose_name_plural': 'categorias de chamado',
                'ordering': ['name'],
            },
        ),
        migrations.RunPython(criar_categorias_padrao, migrations.RunPython.noop),
        migrations.AddField(
            model_name='ticket',
            name='category_fk',
            field=models.ForeignKey(
                blank=True,
                help_text='Categoria do problema.',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tickets_migracao',
                to='helpdesk.ticketcategory',
            ),
        ),
        migrations.RunPython(vincular_categorias_aos_chamados, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='ticket',
            name='category',
        ),
        migrations.RenameField(
            model_name='ticket',
            old_name='category_fk',
            new_name='category',
        ),
        migrations.AlterField(
            model_name='ticket',
            name='category',
            field=models.ForeignKey(
                help_text='Categoria do problema.',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tickets',
                to='helpdesk.ticketcategory',
            ),
        ),
    ]
