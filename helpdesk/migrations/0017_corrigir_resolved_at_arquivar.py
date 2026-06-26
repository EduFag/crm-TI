# Corrige resolved_at preenchido com updated_at recente e arquiva chamados elegíveis

from datetime import timedelta

from django.db import migrations
from django.db.models import Q
from django.utils import timezone


def corrigir_resolved_at_e_arquivar(apps, schema_editor):
    Ticket = apps.get_model('helpdesk', 'Ticket')
    Comment = apps.get_model('helpdesk', 'Comment')
    RegistroAcao = apps.get_model('core', 'RegistroAcao')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    ticket_ct = ContentType.objects.filter(app_label='helpdesk', model='ticket').first()
    cutoff = timezone.now() - timedelta(hours=24)

    for ticket in Ticket.objects.filter(status='RESOLVED', is_archived=False).iterator():
        comentario = (
            Comment.objects.filter(ticket_id=ticket.pk, is_active=True)
            .filter(
                Q(text__startswith='Chamado finalizado') | Q(text__startswith='Chamado recusado')
            )
            .order_by('-created_at')
            .first()
        )

        data_resolucao = None
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
            if log:
                data_resolucao = log.timestamp

        if not data_resolucao:
            data_resolucao = ticket.resolved_at or ticket.updated_at or ticket.created_at

        if ticket.resolved_at is None or ticket.resolved_at > data_resolucao:
            Ticket.objects.filter(pk=ticket.pk).update(resolved_at=data_resolucao)

        if data_resolucao < cutoff:
            Ticket.objects.filter(pk=ticket.pk).update(is_archived=True)


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0016_ticket_resolved_at'),
    ]

    operations = [
        migrations.RunPython(corrigir_resolved_at_e_arquivar, migrations.RunPython.noop),
    ]
