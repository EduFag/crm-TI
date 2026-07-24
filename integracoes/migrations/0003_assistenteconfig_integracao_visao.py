# Generated manually — integração multimodal para prints do Assistente

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integracoes', '0002_assistente'),
    ]

    operations = [
        migrations.AddField(
            model_name='assistenteconfig',
            name='integracao_visao',
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    'Integração multimodal para ler prints (ChatGPT/Gemini). '
                    'DeepSeek não lê imagem — use outro provedor aqui.'
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='configs_assistente_visao',
                to='integracoes.integracaoia',
            ),
        ),
    ]
