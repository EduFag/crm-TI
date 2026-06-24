# Generated manually — novos papéis TEAM_LEADER e MULTIPLIER

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_customuser_id_alter_equipe_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('ADMIN', 'Administrador'),
                    ('IT_USER', 'Membro da Equipe (TI)'),
                    ('SUPERVISOR', 'Supervisor'),
                    ('TEAM_LEADER', 'Líder de Equipe'),
                    ('MULTIPLIER', 'Multiplicador'),
                    ('STANDARD', 'Usuário Padrão'),
                ],
                default='STANDARD',
                help_text='Papel do usuário no sistema (define permissões de acesso).',
                max_length=20,
            ),
        ),
    ]
