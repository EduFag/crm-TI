import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from chips.models import Operator

op = Operator.objects.first()
if op:
    print(f"op: {op}, status: {op.status}, display: {op.get_status_display()}")
else:
    print("No operators")
