# Gerada manualmente — sincroniza models.py com 0003 (sem alteração no banco)

from django.db import migrations


class Migration(migrations.Migration):
    """
    Os índices core_regist_modulo__idx e core_regist_actor_i_idx já existem desde 0003.
    O models.py foi alinhado com os mesmos nomes explícitos.
    Nenhuma operação no banco é necessária.
    """

    dependencies = [
        ('core', '0003_registroacao'),
    ]

    operations = []
