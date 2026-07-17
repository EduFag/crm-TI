import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from django.test import Client
from core.models import CustomUser

# Get the first admin or IT user
user = CustomUser.objects.filter(is_superuser=True).first()
if not user:
    user = CustomUser.objects.first()

client = Client()
client.force_login(user)

response = client.get('/helpdesk/', SERVER_NAME='127.0.0.1', follow=True)
print('Kanban Status:', response.status_code)
if response.status_code == 500:
    print(response.content.decode('utf-8'))

response2 = client.get('/helpdesk/dashboard/', SERVER_NAME='127.0.0.1', follow=True)
print('Dashboard Status:', response2.status_code)
if response2.status_code == 500:
    print(response2.content.decode('utf-8'))
