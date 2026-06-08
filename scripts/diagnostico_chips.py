#!/usr/bin/env python
"""
Diagnóstico da página /chips/ — rode na VPS:
  python scripts/diagnostico_chips.py
"""
import os
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

import django  # noqa: E402

django.setup()

from django.template.loader import render_to_string  # noqa: E402
from django.test import RequestFactory  # noqa: E402

from core.models import CustomUser  # noqa: E402
from chips.views.dashboard import ChipsView  # noqa: E402


def main():
    user = CustomUser.objects.filter(is_active=True).first()
    if not user:
        print('ERRO: nenhum usuário ativo no banco')
        sys.exit(1)

    print(f'Usuário: {user.username} | role={user.role} | superuser={user.is_superuser}')

    factory = RequestFactory()
    request = factory.get('/chips/', HTTP_HOST='ti.moneypromotora.com.br')
    request.user = user

    view = ChipsView()
    view.setup(request)

    try:
        context = view.get_context_data()
        print('OK — contexto carregado')
    except Exception:
        print('ERRO — ao montar contexto:')
        traceback.print_exc()
        sys.exit(2)

    try:
        html = render_to_string('chips/index.html', context, request=request)
        print(f'OK — template renderizado ({len(html)} bytes)')
    except Exception:
        print('ERRO — ao renderizar template:')
        traceback.print_exc()
        sys.exit(3)


if __name__ == '__main__':
    main()
