import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0002_equipe'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistroAcao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modulo', models.CharField(
                    choices=[
                        ('helpdesk', 'Helpdesk'),
                        ('chips', 'Chips'),
                        ('emails', 'E-mails'),
                        ('equipment', 'Equipamentos'),
                        ('core', 'Core'),
                    ],
                    db_index=True,
                    max_length=20,
                )),
                ('acao', models.CharField(
                    choices=[
                        ('CREATED', 'Criação'),
                        ('UPDATED', 'Atualização'),
                        ('STATUS_CHANGED', 'Mudança de status'),
                        ('ASSIGNED', 'Atribuição'),
                        ('TRANSFERRED', 'Transferência'),
                        ('RETURNED', 'Devolução'),
                        ('DELIVERY', 'Entrega'),
                        ('COMMENT', 'Comentário'),
                        ('ACTIVATED', 'Ativação'),
                        ('DEACTIVATED', 'Desativação'),
                        ('PASSWORD_RESET', 'Reset de senha'),
                        ('RECHARGE', 'Recarga'),
                        ('BLOCKED', 'Bloqueio'),
                        ('UNBLOCKED', 'Desbloqueio'),
                    ],
                    db_index=True,
                    max_length=30,
                )),
                ('descricao', models.TextField(help_text='Descrição legível da ação.')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('object_repr', models.CharField(blank=True, help_text='Snapshot do objeto afetado.', max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Detalhes estruturados (antes/depois).')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('actor', models.ForeignKey(
                    blank=True,
                    help_text='Usuário que executou a ação.',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='acoes_registradas',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('content_type', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='contenttypes.contenttype',
                )),
            ],
            options={
                'verbose_name': 'registro de ação',
                'verbose_name_plural': 'registros de ação',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='registroacao',
            index=models.Index(fields=['modulo', '-timestamp'], name='core_regist_modulo__idx'),
        ),
        migrations.AddIndex(
            model_name='registroacao',
            index=models.Index(fields=['actor', '-timestamp'], name='core_regist_actor_i_idx'),
        ),
    ]
