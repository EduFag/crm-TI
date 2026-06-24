import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Equipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nome da equipe.', max_length=80, unique=True)),
                ('is_active', models.BooleanField(default=True, help_text='Equipes inativas não aparecem na atribuição.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'equipe',
                'verbose_name_plural': 'equipes',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='customuser',
            name='equipe',
            field=models.ForeignKey(
                blank=True,
                help_text='Equipe do usuário (opcional; atribuída pelo administrador).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='membros',
                to='core.equipe',
            ),
        ),
    ]
