# Gerada manualmente — custódia, envelopes e transferências

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chips', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='nome',
            field=models.CharField(blank=True, help_text='Nome escrito no envelope.', max_length=150),
        ),
        migrations.AddField(
            model_name='batch',
            name='setor',
            field=models.CharField(blank=True, help_text='Setor escrito no envelope.', max_length=100),
        ),
        migrations.AddField(
            model_name='batch',
            name='tipo',
            field=models.CharField(
                choices=[('LOTE', 'Lote'), ('ENVELOPE', 'Envelope')],
                default='ENVELOPE',
                help_text='Lote de recebimento ou envelope físico na TI.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='chip',
            name='activated_at',
            field=models.DateField(
                blank=True,
                help_text='Data de ativação no callcenter (primeira entrega).',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='chip',
            name='custody',
            field=models.CharField(
                choices=[('WITH_TI', 'Na TI'), ('WITH_PERSON', 'Com pessoa')],
                default='WITH_TI',
                help_text='Onde o chip está fisicamente agora.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='chip',
            name='last_blocked_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Data do último bloqueio da linha.',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='chipmovement',
            name='action',
            field=models.CharField(
                choices=[
                    ('DELIVERY', 'Entrega'),
                    ('RETURN', 'Devolução'),
                    ('TRANSFER', 'Transferência'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='chipmovement',
            name='employee_user',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário do sistema vinculado ao titular.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='chip_movements',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='chipmovement',
            name='registered_by',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='chip_movements_registered',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Dados legados: lotes existentes eram lotes de recebimento
        migrations.RunSQL(
            sql="UPDATE chips_batch SET tipo = 'LOTE' WHERE tipo = 'ENVELOPE';",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Chips em uso legados
        migrations.RunSQL(
            sql="UPDATE chips_chip SET custody = 'WITH_PERSON' WHERE status = 'IN_USE';",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="UPDATE chips_chip SET custody = 'WITH_TI' WHERE status != 'IN_USE';",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
