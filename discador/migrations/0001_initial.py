# Generated manually for discador app

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


def seed_joytec(apps, schema_editor):
    Discador = apps.get_model('discador', 'Discador')
    DiscadorContratoHistorico = apps.get_model('discador', 'DiscadorContratoHistorico')
    discador, criado = Discador.objects.get_or_create(
        slug='joytec',
        defaults={
            'nome': 'JoyTec',
            'valor_por_licenca': Decimal('0.00'),
            'licencas_contratadas': 37,
            'is_active': True,
        },
    )
    if criado:
        DiscadorContratoHistorico.objects.create(
            discador=discador,
            valor_por_licenca=discador.valor_por_licenca,
            licencas_contratadas=discador.licencas_contratadas,
            observacao='Cadastro inicial do contrato JoyTec.',
            registered_by=None,
        )


def unseed_joytec(apps, schema_editor):
    Discador = apps.get_model('discador', 'Discador')
    Discador.objects.filter(slug='joytec').delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Discador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Nome do provedor de discador.', max_length=100)),
                ('slug', models.SlugField(help_text='Identificador único na URL.', unique=True)),
                ('valor_por_licenca', models.DecimalField(decimal_places=2, default=0, help_text='Valor cobrado por licença ativa.', max_digits=10)),
                ('licencas_contratadas', models.PositiveIntegerField(default=0, help_text='Quantidade de licenças contratadas no momento.')),
                ('is_active', models.BooleanField(default=True, help_text='Discador ativo no sistema.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Discador',
                'verbose_name_plural': 'Discadores',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Campanha',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('is_active', models.BooleanField(default=True, help_text='Campanha disponível para novos acessos.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('discador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='campanhas', to='discador.discador')),
            ],
            options={
                'verbose_name': 'Campanha',
                'verbose_name_plural': 'Campanhas',
                'ordering': ['nome'],
                'unique_together': {('discador', 'nome')},
            },
        ),
        migrations.CreateModel(
            name='Ramal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(help_text='Número do ramal no discador.', max_length=50)),
                ('status', models.CharField(choices=[('IN_USE', 'Ramal em uso'), ('FREE', 'Livre'), ('NOT_CONFIGURED', 'Não configurado')], default='NOT_CONFIGURED', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('discador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ramais', to='discador.discador')),
            ],
            options={
                'verbose_name': 'Ramal',
                'verbose_name_plural': 'Ramais',
                'ordering': ['numero'],
                'unique_together': {('discador', 'numero')},
            },
        ),
        migrations.CreateModel(
            name='AcessoDiscador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titular_nome', models.CharField(blank=True, default='', help_text='Nome do titular (snapshot).', max_length=150)),
                ('login_discador', models.CharField(help_text='Login no discador.', max_length=100)),
                ('tipo', models.CharField(choices=[('CONSULTOR', 'Consultor(a)'), ('VENDEDOR', 'Vendedor(a)'), ('NEGOCIADOR', 'Negociador(a)')], max_length=20)),
                ('status', models.CharField(choices=[('IN_USE', 'Ramal em uso'), ('FREE', 'Livre'), ('NOT_CONFIGURED', 'Não configurado')], default='IN_USE', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('campanha', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='acessos', to='discador.campanha')),
                ('discador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='acessos', to='discador.discador')),
                ('ramal', models.OneToOneField(help_text='Ramal associado a este acesso.', on_delete=django.db.models.deletion.PROTECT, related_name='acesso', to='discador.ramal')),
                ('titular_user', models.ForeignKey(blank=True, help_text='Usuário do sistema, se houver.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='acessos_discador', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Acesso do discador',
                'verbose_name_plural': 'Acessos do discador',
                'ordering': ['titular_nome', 'login_discador'],
            },
        ),
        migrations.CreateModel(
            name='DiscadorContratoHistorico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_por_licenca', models.DecimalField(decimal_places=2, max_digits=10)),
                ('licencas_contratadas', models.PositiveIntegerField()),
                ('observacao', models.CharField(blank=True, default='', max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('discador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico_contrato', to='discador.discador')),
                ('registered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='discador_contrato_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Histórico de contrato',
                'verbose_name_plural': 'Históricos de contrato',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='RamalAtribuicaoHistorico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ramal_numero', models.CharField(blank=True, default='', help_text='Snapshot do número do ramal (preserva histórico se o ramal for excluído).', max_length=50)),
                ('action', models.CharField(choices=[('ASSIGNED', 'Atribuição'), ('TRANSFERRED', 'Transferência'), ('FREED', 'Liberado'), ('DELETED', 'Exclusão do acesso'), ('STATUS_CHANGED', 'Mudança de status'), ('CREATED', 'Cadastro do ramal')], max_length=20)),
                ('titular_nome', models.CharField(blank=True, default='', max_length=150)),
                ('login_discador', models.CharField(blank=True, default='', max_length=100)),
                ('campanha_nome', models.CharField(blank=True, default='', max_length=150)),
                ('tipo', models.CharField(blank=True, default='', max_length=20)),
                ('status', models.CharField(blank=True, default='', max_length=20)),
                ('observacao', models.CharField(blank=True, default='', max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('discador', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='historico_atribuicoes', to='discador.discador')),
                ('ramal', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historico_atribuicoes', to='discador.ramal')),
                ('registered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='discador_atribuicao_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Histórico de atribuição de ramal',
                'verbose_name_plural': 'Históricos de atribuição de ramal',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.RunPython(seed_joytec, unseed_joytec),
    ]
