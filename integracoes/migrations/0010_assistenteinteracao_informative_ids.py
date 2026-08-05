# AssistenteInteracao: IDs de comunicados da Central usados na rodada

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integracoes', '0009_integracaoapi'),
    ]

    operations = [
        migrations.AddField(
            model_name='assistenteinteracao',
            name='informative_ids',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='IDs de InformativeMessage usados nesta rodada.',
            ),
        ),
    ]
