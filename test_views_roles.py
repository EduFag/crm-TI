import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from django.test import Client
from core.models import CustomUser

for role in ['ADMIN', 'IT_USER', 'SUPERVISOR', 'STANDARD', 'MULTIPLIER']:
    try:
        user, created = CustomUser.objects.get_or_create(username=f'test_{role}', defaults={'role': role, 'is_staff': True})
        client = Client()
        client.force_login(user)
        response = client.get('/helpdesk/', SERVER_NAME='127.0.0.1', follow=True)
        print(f'{role} Kanban Status:', response.status_code)
        if response.status_code == 500:
            print(response.content.decode('utf-8'))
    except Exception as e:
        print(f'{role} Error:', e)
