# Preenche resolved_at em chamados já finalizados para o arquivamento automático funcionar

from django.db import migrations, models


def preencher_resolved_at(apps, schema_editor):
    Ticket = apps.get_model('helpdesk', 'Ticket')
    Comment = apps.get_model('helpdesk', 'Comment')
    RegistroAcao = apps.get_model('core', 'RegistroAcao')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    ticket_ct = ContentType.objects.filter(app_label='helpdesk', model='ticket').first()

    for ticket in Ticket.objects.filter(status='RESOLVED', resolved_at__isnull=True).iterator():
        comentario = (
            Comment.objects.filter(ticket_id=ticket.pk)
            .filter(text__startswith='Chamado finalizado')
            .order_by('-created_at')
            .first()
        )
        if not comentario:
            comentario = (
                Comment.objects.filter(ticket_id=ticket.pk)
                .filter(text__startswith='Chamado recusado')
                .order_by('-created_at')
                .first()
            )

        if comentario:
            data_resolucao = comentario.created_at
        elif ticket_ct:
            log = (
                RegistroAcao.objects.filter(
                    content_type_id=ticket_ct.pk,
                    object_id=ticket.pk,
                    acao='STATUS_CHANGED',
                    descricao__contains='para Resolvido',
                )
                .order_by('-timestamp')
                .first()
            )
            data_resolucao = log.timestamp if log else (ticket.updated_at or ticket.created_at)
        else:
            data_resolucao = ticket.updated_at or ticket.created_at

        Ticket.objects.filter(pk=ticket.pk).update(resolved_at=data_resolucao)


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0015_ticket_co_authors'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='resolved_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Momento em que o chamado foi finalizado/resolvido (base do arquivamento automático).',
                null=True,
            ),
        ),
        migrations.RunPython(preencher_resolved_at, migrations.RunPython.noop),
    ]
